from fastapi import APIRouter, Query
from typing import Annotated
from services.regression_service import RegressionServiceDependency
from schemas.regression_schema import (
    RegressionInputSearchPosition,
    RegressionInputPrice,
    RegressionOutput,
    RegressionCoefficients,
)
from schemas.scraped_car_schema import ScrapedCarQuery

regression_router = APIRouter(prefix="/regression", tags=["regression"])

@regression_router.post("/predict-search-position", response_model=RegressionOutput)
async def predict_search_position(
    service: RegressionServiceDependency,
    input_data: RegressionInputSearchPosition,
    query: Annotated[ScrapedCarQuery, Query()] = ScrapedCarQuery(),
):
    return await service.predict_search_position(input_data, query)

@regression_router.post("/predict-price", response_model=RegressionOutput)
async def predict_price(
    input_data: RegressionInputPrice,
    service: RegressionServiceDependency,
    query: Annotated[ScrapedCarQuery, Query()] = ScrapedCarQuery(),
):
    return await service.predict_price(input_data, query)

@regression_router.get("/search-position-coefficients", response_model=RegressionCoefficients)
async def get_search_position_coefficients(
    service: RegressionServiceDependency,
    query: Annotated[ScrapedCarQuery, Query()] = ScrapedCarQuery(),
):
    return await service.get_search_position_coefficients(query)

@regression_router.get("/price-coefficients", response_model=RegressionCoefficients)
async def get_price_coefficients(
    service: RegressionServiceDependency,
    query: Annotated[ScrapedCarQuery, Query()] = ScrapedCarQuery(),
):
    return await service.get_price_coefficients(query)