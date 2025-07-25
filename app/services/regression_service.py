import pandas as pd
import statsmodels.api as sm
from typing import Annotated, Dict, Optional, List
from fastapi import Depends
from schemas.regression_schema import (
    RegressionInputSearchPosition,
    RegressionInputPrice,
    RegressionOutput,
    RegressionCoefficients,
    Coefficient,
    RegressionCoefficientTable,
    RegressionCoefficientTableRow,
)
from services.csv_service import CSVServiceDependency, ScrapedCarQuery
from services.logger_service import logger
from crud.regression_model_repository import RegressionModelRepositoryDependency
from datetime import datetime, timezone
import matplotlib.pyplot as plt
import seaborn as sns
import json
import hashlib


class RegressionService:
    def __init__(
        self,
        csv_service: CSVServiceDependency,
        regression_model_repo: RegressionModelRepositoryDependency,
    ):
        self.csv_service = csv_service
        self.regression_model_repo = regression_model_repo
        self.df_cache: Optional[pd.DataFrame] = None
        self.search_position_model = None
        self.price_model = None
        self.search_position_coefficients = None
        self.price_coefficients = None
        self.last_query_hash: Optional[str] = None

    def _get_query_hash(self, query: ScrapedCarQuery) -> str:
        query_dict = query.model_dump()
        query_str = str(sorted(query_dict.items()))
        return hashlib.md5(query_str.encode()).hexdigest()

    async def _load_and_prepare_data(
        self, cars_scraping_query: ScrapedCarQuery
    ) -> pd.DataFrame:
        query_hash = self._get_query_hash(cars_scraping_query)

        if self.df_cache is not None and self.last_query_hash == query_hash:
            logger.debug("Using cached DataFrame")
            return self.df_cache

        logger.info("Loading data from CSVService")
        try:
            csv_data = await self.csv_service.generate_scraped_cars_csv(
                cars_scraping_query
            )
            csv_data.seek(0)
            df = pd.read_csv(csv_data)
        except Exception as e:
            logger.error(f"Failed to load CSV data: {str(e)}")
            raise ValueError(f"Failed to load CSV data: {str(e)}")

        df = df.rename(
            columns={
                "scraped_year": "year_of_car",
                "scraped_price": "price",
                "scraped_mileage": "mileage",
                "scraped_number_of_views": "number_of_views",
                "search_position": "search_position",
            }
        )

        required_columns = [
            "year_of_car",
            "price",
            "mileage",
            "number_of_views",
            "search_position",
        ]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            raise ValueError(f"Missing required columns: {missing_columns}")

        df = df[required_columns].dropna()
        df = df[
            (df["year_of_car"].between(1900, 2025))
            & (df["price"] >= 0)
            & (df["mileage"] >= 0)
            & (df["number_of_views"] >= 0)
            & (df["search_position"] >= 0)
        ]

        if df.empty:
            logger.warning("No valid data after filtering, using fallback data")
            df = pd.DataFrame(
                {
                    "year_of_car": [2018],
                    "price": [25000.0],
                    "mileage": [150000.0],
                    "number_of_views": [100],
                    "search_position": [5.0],
                }
            )

        logger.info(f"Prepared {len(df)} rows of data")
        self.df_cache = df
        self.last_query_hash = query_hash
        return df

    def _create_input_df(self, input_data: Dict, columns: list) -> pd.DataFrame:
        input_df = pd.DataFrame([input_data], columns=columns)
        input_df = sm.add_constant(input_df, has_constant="add")
        logger.debug(f"Input DataFrame columns: {input_df.columns}")
        return input_df

    async def save_regression_model_to_db(
        self,
        *,
        name,
        target_variable,
        feature_variables,
        coefficients_json,
        intercept,
        r_squared,
        adj_r_squared,
        f_statistic,
        f_p_value,
        n_observations,
        filters,
        formula,
    ):
        model_data = {
            "name": name,
            "target_variable": target_variable,
            "feature_variables": feature_variables,
            "coefficients_json": coefficients_json,
            "intercept": intercept,
            "r_squared": r_squared,
            "adj_r_squared": adj_r_squared,
            "f_statistic": f_statistic,
            "f_p_value": f_p_value,
            "n_observations": n_observations,
            "filters": filters,
            "formula": formula,
            "last_trained_at": datetime.now(timezone.utc),
        }
        await self.regression_model_repo.add_regression_model(model_data)

    async def _train_search_position_model(
        self, df: pd.DataFrame, filters, save_to_db=False
    ):
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
        if save_to_db:
            await self.save_regression_model_to_db(
                name="Прогноз позиції на платформі",
                target_variable="search_position",
                feature_variables=json.dumps(
                    ["year_of_car", "price", "mileage", "number_of_views"]
                ),
                coefficients_json=json.dumps(model.params.to_dict()),
                intercept=float(model.params["const"]),
                r_squared=float(model.rsquared),
                adj_r_squared=float(model.rsquared_adj),
                f_statistic=float(model.fvalue),
                f_p_value=float(model.f_pvalue),
                n_observations=int(model.nobs),
                filters=json.dumps(filters),
                formula="search_position ~ year_of_car + price + mileage + number_of_views",
            )

        logger.info("Search position model trained")
        return model

    async def _train_price_model(self, df: pd.DataFrame, filters, save_to_db=False):
        logger.info("Training price model")
        X = df[["search_position", "mileage", "year_of_car", "number_of_views"]]
        y = df["price"]
        X = sm.add_constant(X)
        model = sm.OLS(y, X).fit()

        self.price_coefficients = [
            Coefficient(feature=feat, coefficient=coef, p_value=pval)
            for feat, coef, pval in zip(
                [
                    "const",
                    "search_position",
                    "mileage",
                    "year_of_car",
                    "number_of_views",
                ],
                model.params,
                model.pvalues,
            )
        ]
        if save_to_db:
            model_summary = {
                "coefficients": model.params.to_dict(),
                "std_errors": model.bse.to_dict(),
                "t_statistics": model.tvalues.to_dict(),
                "p_values": model.pvalues.to_dict(),
                "confidence_intervals": model.conf_int().T.to_dict(),
            }
            formula = (
                "price ~ search_position + mileage + year_of_car + number_of_views"
            )
            await self.save_regression_model_to_db(
                name="Прогноз ціни на платформі",
                target_variable="price",
                feature_variables=json.dumps(
                    ["search_position", "mileage", "year_of_car", "number_of_views"]
                ),
                coefficients_json=json.dumps(model_summary),
                intercept=float(model.params["const"]),
                r_squared=float(model.rsquared),
                adj_r_squared=float(model.rsquared_adj),
                f_statistic=float(model.fvalue),
                f_p_value=float(model.f_pvalue),
                n_observations=int(model.nobs),
                filters=json.dumps(filters),
                formula=formula,
            )

        logger.info("Price model trained")
        return model

    async def _initialize_models(
        self,
        cars_scraping_query: ScrapedCarQuery,
        model_type: str = "both",
        save_to_db=False,
    ):
        df = await self._load_and_prepare_data(cars_scraping_query)
        query_hash = self._get_query_hash(cars_scraping_query)

        if self.last_query_hash != query_hash:
            self.search_position_model = None
            self.price_model = None
            self.search_position_coefficients = None
            self.price_coefficients = None

        filters = cars_scraping_query.model_dump()

        if (
            model_type in ["both", "search_position"]
            and self.search_position_model is None
        ):
            self.search_position_model = await self._train_search_position_model(
                df, filters, save_to_db=save_to_db
            )

        if model_type in ["both", "price"] and self.price_model is None:
            self.price_model = await self._train_price_model(
                df, filters, save_to_db=save_to_db
            )

    async def predict_search_position(
        self,
        input_data: RegressionInputSearchPosition,
        cars_scraping_query: ScrapedCarQuery,
    ) -> RegressionOutput:
        await self._initialize_models(
            cars_scraping_query, model_type="search_position", save_to_db=True
        )
        logger.info("Predicting search position")
        input_dict = {
            "year_of_car": input_data.year_of_car,
            "price": input_data.price,
            "mileage": input_data.mileage,
            "number_of_views": input_data.number_of_views,
        }
        input_df = self._create_input_df(
            input_dict, ["year_of_car", "price", "mileage", "number_of_views"]
        )

        expected_features = self.search_position_model.params.index.tolist()
        if set(input_df.columns) != set(expected_features):
            logger.error(
                f"Feature mismatch: expected {expected_features}, got {input_df.columns}"
            )
            raise ValueError(
                f"Feature mismatch: expected {expected_features}, got {input_df.columns}"
            )

        prediction = self.search_position_model.predict(input_df)[0]
        logger.info(f"Predicted search position: {prediction}")
        return RegressionOutput(predicted_value=round(float(prediction), 2))

    async def predict_price(
        self,
        input_data: RegressionInputPrice,
        cars_scraping_query: ScrapedCarQuery,
    ) -> RegressionOutput:
        await self._initialize_models(
            cars_scraping_query, model_type="price", save_to_db=True
        )
        logger.info("Predicting price")
        input_dict = {
            "search_position": input_data.search_position,
            "mileage": input_data.mileage,
            "year_of_car": input_data.year_of_car,
            "number_of_views": input_data.number_of_views,
        }
        input_df = self._create_input_df(
            input_dict, ["search_position", "mileage", "year_of_car", "number_of_views"]
        )

        expected_features = self.price_model.params.index.tolist()
        if set(input_df.columns) != set(expected_features):
            logger.error(
                f"Feature mismatch: expected {expected_features}, got {input_df.columns}"
            )
            raise ValueError(
                f"Feature mismatch: expected {expected_features}, got {input_df.columns}"
            )

        prediction = self.price_model.predict(input_df)[0]
        logger.info(f"Predicted price: {prediction}")
        return RegressionOutput(predicted_value=round(float(prediction), 2))

    async def get_search_position_coefficients(
        self, cars_scraping_query: ScrapedCarQuery
    ) -> RegressionCoefficients:
        await self._initialize_models(
            cars_scraping_query, model_type="search_position", save_to_db=True
        )
        logger.info("Retrieving search position coefficients")
        return RegressionCoefficients(coefficients=self.search_position_coefficients)

    async def get_price_coefficients(
        self, cars_scraping_query: ScrapedCarQuery
    ) -> RegressionCoefficients:
        await self._initialize_models(
            cars_scraping_query, model_type="price", save_to_db=True
        )
        logger.info("Retrieving price coefficients")
        return RegressionCoefficients(coefficients=self.price_coefficients)

    def create_coefficients_plot(
        self, coefficients: List[Coefficient], model_name: str
    ) -> str:
        coef_df = pd.DataFrame([c.model_dump() for c in coefficients])

        const_value = coef_df[coef_df["feature"] == "const"]["coefficient"].iloc[0]
        const_p_value = coef_df[coef_df["feature"] == "const"]["p_value"].iloc[0]
        other_coefs = coef_df[coef_df["feature"] != "const"].copy()

        max_abs_coef = (
            abs(other_coefs["coefficient"]).max() if not other_coefs.empty else 1.0
        )
        other_coefs["coefficient_normalized"] = (
            other_coefs["coefficient"] / max_abs_coef
        )

        plt.figure(figsize=(10, 6))

        if not other_coefs.empty:
            sns.barplot(
                x="coefficient_normalized",
                y="feature",
                hue="feature",
                data=other_coefs,
                palette="Blues_d",
            )
            plt.xlabel("Coefficient Value (Normalized to Max)")
        else:
            plt.xlabel("Coefficient Value (No Data)")

        for i, row in other_coefs.iterrows():
            if row["p_value"] < 0.05:
                plt.text(
                    row["coefficient_normalized"], i, "*", fontsize=12, va="center"
                )

        plt.title(f"{model_name} Regression Coefficients")
        plt.ylabel("Feature")
        const_significance = "*" if const_p_value < 0.05 else ""
        plt.text(
            0.5,
            1.1,
            f"const: {const_value:.2f} {const_significance}",
            transform=plt.gca().transAxes,
            fontsize=10,
            ha="center",
            color="red",
        )

        plt.xlim(-1.5, 1.5)

        plot_path = f"{model_name.lower().replace(' ', '_')}_coefficients_plot.png"
        plt.savefig(plot_path)
        plt.close()
        logger.info(f"Created plot at {plot_path}")
        return plot_path

    async def get_price_coefficients_plot(
        self, cars_scraping_query: ScrapedCarQuery
    ) -> str:
        await self._initialize_models(
            cars_scraping_query, model_type="price", save_to_db=True
        )
        return self.create_coefficients_plot(self.price_coefficients, "Price")

    async def get_search_position_coefficient_table(
        self, cars_scraping_query: ScrapedCarQuery
    ) -> RegressionCoefficientTable:
        await self._initialize_models(
            cars_scraping_query, model_type="search_position", save_to_db=True
        )
        logger.info("Retrieving search position coefficient table")
        return self._get_coefficient_table(
            self.search_position_coefficients, "search_position"
        )

    def _get_coefficient_table(
        self, coefficients: List[Coefficient], model_type: str
    ) -> RegressionCoefficientTable:
        rows = []
        for coef in coefficients:
            significance = "Significant" if coef.p_value < 0.05 else "Not significant"
            if coef.feature == "const":
                interpretation = "Baseline value (intercept) of the model"
            else:
                impact = "increases" if coef.coefficient > 0 else "decreases"
                interpretation = (
                    f"An increase of {coef.feature} by 1 unit {impact} "
                    f"{model_type} by {abs(coef.coefficient):.4f} "
                    f"({'significant' if coef.p_value < 0.05 else 'not significant'} effect)"
                )
            rows.append(
                RegressionCoefficientTableRow(
                    feature=coef.feature,
                    coefficient=round(coef.coefficient, 4),
                    p_value=round(coef.p_value, 4),
                    significance=significance,
                    interpretation=interpretation,
                )
            )
        return RegressionCoefficientTable(rows=rows)

    async def get_price_coefficient_table(
        self, cars_scraping_query: ScrapedCarQuery
    ) -> RegressionCoefficientTable:
        await self._initialize_models(
            cars_scraping_query, model_type="price", save_to_db=True
        )
        logger.info("Retrieving price coefficient table")
        return self._get_coefficient_table(self.price_coefficients, "price")


def get_regression_service(
    csv_service: CSVServiceDependency,
    regression_model_repo: RegressionModelRepositoryDependency,
) -> RegressionService:
    return RegressionService(
        csv_service=csv_service, regression_model_repo=regression_model_repo
    )


RegressionServiceDependency = Annotated[
    RegressionService, Depends(get_regression_service)
]
