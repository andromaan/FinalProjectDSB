import pandas as pd
import statsmodels.api as sm
from typing import Annotated, Dict, Optional
from fastapi import Depends
from schemas.regression_schema import (
    RegressionInputSearchPosition,
    RegressionInputPrice,
    RegressionOutput,
    RegressionCoefficients,
    Coefficient,
)
from services.csv_service import CSVServiceDependency, ScrapedCarQuery
from services.logger_service import logger

class RegressionService:
    def __init__(self, csv_service: CSVServiceDependency):
        self.csv_service = csv_service
        self.df_cache: Optional[pd.DataFrame] = None
        self.search_position_model = None
        self.price_model = None
        self.search_position_coefficients = None
        self.price_coefficients = None
        self.last_query_hash: Optional[str] = None

    def _get_query_hash(self, query: ScrapedCarQuery) -> str:
        """Генерує унікальний хеш для ScrapedCarQuery."""
        import hashlib
        query_dict = query.dict()
        query_str = str(sorted(query_dict.items()))
        return hashlib.md5(query_str.encode()).hexdigest()

    async def _load_and_prepare_data(self, cars_scraping_query: ScrapedCarQuery) -> pd.DataFrame:
        """Завантажує і готує дані з CSVService."""
        query_hash = self._get_query_hash(cars_scraping_query)

        if self.df_cache is not None and self.last_query_hash == query_hash:
            logger.debug("Using cached DataFrame")
            return self.df_cache

        logger.info("Loading data from CSVService")
        try:
            csv_data = await self.csv_service.generate_scraped_cars_csv(cars_scraping_query)
            csv_data.seek(0)
            df = pd.read_csv(csv_data)
        except Exception as e:
            logger.error(f"Failed to load CSV data: {str(e)}")
            raise ValueError(f"Failed to load CSV data: {str(e)}")

        df = df.rename(columns={
            "scraped_year": "year_of_car",
            "scraped_price": "price",
            "scraped_mileage": "mileage",
            "scraped_number_of_views": "number_of_views",
            "search_position": "search_position"
        })

        required_columns = ["year_of_car", "price", "mileage", "number_of_views", "search_position"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            raise ValueError(f"Missing required columns: {missing_columns}")

        df = df[required_columns].dropna()
        df = df[
            (df["year_of_car"].between(1900, 2025)) &
            (df["price"] >= 0) &
            (df["mileage"] >= 0) &
            (df["number_of_views"] >= 0) &
            (df["search_position"] >= 0)
        ]

        if df.empty:
            logger.warning("No valid data after filtering, using fallback data")
            df = pd.DataFrame({
                "year_of_car": [2018],
                "price": [25000.0],
                "mileage": [150000.0],
                "number_of_views": [100],
                "search_position": [5.0]
            })

        logger.info(f"Prepared {len(df)} rows of data")
        self.df_cache = df
        self.last_query_hash = query_hash
        return df

    def _create_input_df(self, input_data: Dict, columns: list) -> pd.DataFrame:
        """Створює DataFrame для прогнозування з константою."""
        input_df = pd.DataFrame([input_data], columns=columns)
        input_df = sm.add_constant(input_df, has_constant="add")
        logger.debug(f"Input DataFrame columns: {input_df.columns}")
        return input_df

    def _train_search_position_model(self, df: pd.DataFrame) -> sm.OLS:
        """Тренує модель для search_position."""
        logger.info("Training search position model")
        X = df[["year_of_car", "price", "mileage", "number_of_views"]]
        y = df["search_position"]
        X = sm.add_constant(X)
        model = sm.OLS(y, X).fit()

        self.search_position_coefficients = [
            Coefficient(feature=feat, coefficient=coef, p_value=pval)
            for feat, coef, pval in zip(
                ["const", "year_of_car", "price", "mileage", "number_of_views"],
                model.params,
                model.pvalues,
            )
        ]
        logger.info("Search position model trained")
        return model

    def _train_price_model(self, df: pd.DataFrame) -> sm.OLS:
        """Тренує модель для price."""
        logger.info("Training price model")
        X = df[["search_position", "mileage", "year_of_car", "number_of_views"]]
        y = df["price"]
        X = sm.add_constant(X)
        model = sm.OLS(y, X).fit()

        self.price_coefficients = [
            Coefficient(feature=feat, coefficient=coef, p_value=pval)
            for feat, coef, pval in zip(
                ["const", "search_position", "mileage", "year_of_car", "number_of_views"],
                model.params,
                model.pvalues,
            )
        ]
        logger.info("Price model trained")
        return model

    async def _initialize_models(self, cars_scraping_query: ScrapedCarQuery, model_type: str = "both"):
        """Ініціалізує моделі для поточного запиту."""
        df = await self._load_and_prepare_data(cars_scraping_query)
        query_hash = self._get_query_hash(cars_scraping_query)

        if self.last_query_hash != query_hash:
            self.search_position_model = None
            self.price_model = None
            self.search_position_coefficients = None
            self.price_coefficients = None

        if model_type in ["both", "search_position"] and self.search_position_model is None:
            self.search_position_model = self._train_search_position_model(df)

        if model_type in ["both", "price"] and self.price_model is None:
            self.price_model = self._train_price_model(df)

    async def predict_search_position(
        self,
        input_data: RegressionInputSearchPosition,
        cars_scraping_query: ScrapedCarQuery,
    ) -> RegressionOutput:
        """Прогнозує search_position."""
        await self._initialize_models(cars_scraping_query, model_type="search_position")
        logger.info("Predicting search position")
        input_dict = {
            "year_of_car": input_data.year_of_car,
            "price": input_data.price,
            "mileage": input_data.mileage,
            "number_of_views": input_data.number_of_views
        }
        input_df = self._create_input_df(
            input_dict, ["year_of_car", "price", "mileage", "number_of_views"]
        )

        expected_features = self.search_position_model.params.index.tolist()
        if set(input_df.columns) != set(expected_features):
            logger.error(f"Feature mismatch: expected {expected_features}, got {input_df.columns}")
            raise ValueError(f"Feature mismatch: expected {expected_features}, got {input_df.columns}")

        prediction = self.search_position_model.predict(input_df)[0]
        logger.info(f"Predicted search position: {prediction}")
        return RegressionOutput(predicted_value=round(float(prediction), 2))

    async def predict_price(
        self,
        input_data: RegressionInputPrice,
        cars_scraping_query: ScrapedCarQuery,
    ) -> RegressionOutput:
        """Прогнозує price."""
        await self._initialize_models(cars_scraping_query, model_type="price")
        logger.info("Predicting price")
        input_dict = {
            "search_position": input_data.search_position,
            "mileage": input_data.mileage,
            "year_of_car": input_data.year_of_car,
            "number_of_views": input_data.number_of_views
        }
        input_df = self._create_input_df(
            input_dict, ["search_position", "mileage", "year_of_car", "number_of_views"]
        )

        expected_features = self.price_model.params.index.tolist()
        if set(input_df.columns) != set(expected_features):
            logger.error(f"Feature mismatch: expected {expected_features}, got {input_df.columns}")
            raise ValueError(f"Feature mismatch: expected {expected_features}, got {input_df.columns}")

        prediction = self.price_model.predict(input_df)[0]
        logger.info(f"Predicted price: {prediction}")
        return RegressionOutput(predicted_value=round(float(prediction), 2))

    async def get_search_position_coefficients(
        self, cars_scraping_query: ScrapedCarQuery
    ) -> RegressionCoefficients:
        """Повертає коефіцієнти для search_position."""
        await self._initialize_models(cars_scraping_query, model_type="search_position")
        logger.info("Retrieving search position coefficients")
        return RegressionCoefficients(coefficients=self.search_position_coefficients)

    async def get_price_coefficients(
        self, cars_scraping_query: ScrapedCarQuery
    ) -> RegressionCoefficients:
        """Повертає коефіцієнти для price."""
        await self._initialize_models(cars_scraping_query, model_type="price")
        logger.info("Retrieving price coefficients")
        return RegressionCoefficients(coefficients=self.price_coefficients)

def get_regression_service(csv_service: CSVServiceDependency):
    return RegressionService(csv_service=csv_service)

RegressionServiceDependency = Annotated[RegressionService, Depends(get_regression_service)]