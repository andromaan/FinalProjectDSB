from fastapi import APIRouter
from services.scraping_service import ScrapingServiceDependency
from schemas.scraped_car_schema import (
    ScrapingConfigQuery,
    ScrapingResults,
)


scraping_router = APIRouter(prefix="/scraping", tags=["scraping"])


@scraping_router.post("/scrape-car", response_model=ScrapingResults)
async def scrape_car(
    service: ScrapingServiceDependency,
    config: ScrapingConfigQuery,
):
    return await service.scrape_car_with_query(config)
