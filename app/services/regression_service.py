import pandas as pd
import statsmodels.api as sm
from fastapi import Depends
from typing import List, Annotated
import io
from schemas.regression_schema import (
    RegressionInputSearchPosition,
    RegressionInputPrice,
    RegressionOutput,
    RegressionCoefficients,
    Coefficient,
)
from services.csv_service import CSVServiceDependency, ScrapedCarQuery

class RegressionService:
    def __init__(self, csv_service: CSVServiceDependency):
        self.csv_service = csv_service
        self.search_position_model = None
        self.price_model = None
        self.search_position_coefficients = None
        self.price_coefficients = None

    async def _load_and_prepare_data(self, cars_scraping_query: ScrapedCarQuery) -> pd.DataFrame:
        # Fetch CSV data
        csv_data = await self.csv_service.generate_scraped_cars_csv(cars_scraping_query)
        csv_data.seek(0)
        df = pd.read_csv(csv_data)
        
        # Clean and prepare data
        df = df.dropna(subset=['search_position', 'scraped_year', 'scraped_price', 
                             'scraped_mileage', 'scraped_number_of_views'])
        return df

    async def _train_search_position_model(self, cars_scraping_query: ScrapedCarQuery):
        df = await self._load_and_prepare_data(cars_scraping_query)

        # Prepare features and target for search position prediction
        X = df[['scraped_year', 'scraped_price', 'scraped_mileage', 'scraped_number_of_views']]
        y = df['search_position']
        
        # Add constant for intercept
        X = sm.add_constant(X)
        
        # Train model
        self.search_position_model = sm.OLS(y, X).fit()
        
        # Store coefficients
        self.search_position_coefficients = [
            Coefficient(feature=feat, coefficient=coef, p_value=pval)
            for feat, coef, pval in zip(
                ['const', 'year', 'price', 'mileage', 'number_of_views'],
                self.search_position_model.params,
                self.search_position_model.pvalues
            )
        ]

    async def _train_price_model(self, cars_scraping_query: ScrapedCarQuery):
        df = await self._load_and_prepare_data(cars_scraping_query)

        # Prepare features and target for price prediction
        X = df[['search_position', 'scraped_mileage', 'scraped_year', 'scraped_number_of_views']]
        y = df['scraped_price']
        
        # Add constant for intercept
        X = sm.add_constant(X)
        
        # Train model
        self.price_model = sm.OLS(y, X).fit()
        
        # Store coefficients
        self.price_coefficients = [
            Coefficient(feature=feat, coefficient=coef, p_value=pval)
            for feat, coef, pval in zip(
                ['const', 'search_position', 'mileage', 'year', 'number_of_views'],
                self.price_model.params,
                self.price_model.pvalues
            )
        ]

    async def predict_search_position(self, input_data: RegressionInputSearchPosition, cars_scraping_query: ScrapedCarQuery) -> RegressionOutput:
        if self.search_position_model is None:
            await self._train_search_position_model(cars_scraping_query)

        # Prepare input data
        X = pd.DataFrame({
            'const': [1.0],
            'scraped_year': [input_data.year_of_car],
            'scraped_price': [input_data.price],
            'scraped_mileage': [input_data.mileage],
            'scraped_number_of_views': [input_data.number_of_views]
        })
        
        # Make prediction
        prediction = self.search_position_model.predict(X)[0]
        return RegressionOutput(predicted_value=float(prediction))

    async def predict_price(self, input_data: RegressionInputPrice, cars_scraping_query: ScrapedCarQuery) -> RegressionOutput:
        if self.price_model is None:
            await self._train_price_model(cars_scraping_query)

        # Prepare input data
        X = pd.DataFrame({
            'const': [1.0],
            'search_position': [input_data.search_position],
            'scraped_mileage': [input_data.mileage],
            'scraped_year': [input_data.year_of_car],
            'scraped_number_of_views': [input_data.number_of_views]
        })
        
        # Make prediction
        prediction = self.price_model.predict(X)[0]
        return RegressionOutput(predicted_value=float(prediction))

    async def get_search_position_coefficients(self, cars_scraping_query: ScrapedCarQuery) -> RegressionCoefficients:
        if self.search_position_coefficients is None:
            await self._train_search_position_model(cars_scraping_query)
        return RegressionCoefficients(coefficients=self.search_position_coefficients)

    async def get_price_coefficients(self, cars_scraping_query: ScrapedCarQuery) -> RegressionCoefficients:
        if self.price_coefficients is None:
            await self._train_price_model(cars_scraping_query)
        return RegressionCoefficients(coefficients=self.price_coefficients)

def get_regression_service(csv_service: CSVServiceDependency):
    return RegressionService(csv_service=csv_service)

RegressionServiceDependency = Annotated[RegressionService, Depends(get_regression_service)]