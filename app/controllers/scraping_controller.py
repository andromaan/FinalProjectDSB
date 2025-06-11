from fastapi import APIRouter, Query
from services.scraping_service import ScrapingServiceDependency
from schemas.scraped_car_schema import (
    ScrapingConfigQuery,
    ScrapingResults,
    ScrapedRequestResponse,
    ScrapeRequestResponse
)
from crud.scraping_repository import ScrapingRepositoryDependency
from typing import Annotated

scraping_router = APIRouter(prefix="/scraping", tags=["scraping"])


@scraping_router.post("/scrape-cars", response_model=ScrapingResults)
async def scrape_car(
    service: ScrapingServiceDependency,
    config: ScrapingConfigQuery,
):
    return await service.scrape_car_with_query(config)


@scraping_router.get("/scraped-cars", response_model=list[ScrapedRequestResponse])
async def get_scraped_cars(
    repo: ScrapingRepositoryDependency,
    id: Annotated[int | None, Query()] = None,
    car_id: Annotated[int | None, Query()] = None,
    req_id: Annotated[int | None, Query()] = None,
    car_platform_id: Annotated[int | None, Query()] = None
):
    return await repo.fetch_scraped_cars(
        id=id,
        car_id=car_id,
        req_id=req_id,
        car_platform_id=car_platform_id
    )

@scraping_router.get("/scrape-requests", response_model=list[ScrapeRequestResponse])
async def list_scrape_requests(
    repo: ScrapingRepositoryDependency,
):
    return await repo.list_scrape_requests()

@scraping_router.get("/scrape-request/{request_id}", response_model=ScrapeRequestResponse)
async def get_scrape_request(
    request_id: int,
    repo: ScrapingRepositoryDependency,
):
    return await repo.fetch_scrape_request(request_id)