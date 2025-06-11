from fastapi import APIRouter, Query
from services.scraping_service import ScrapingServiceDependency
from schemas.scraped_car_schema import (
    ScrapingConfigByQuery,
    ScrapingResults,
    ScrapedRequestResponse,
    ScrapeRequestResponse,
    ScrapingConfigByCarModel,
)
from crud.scraping_repository import ScrapingRepositoryDependency
from crud.car_model_repository import CarModelRepositoryDependency
from typing import Annotated

scraping_router = APIRouter(prefix="/scraping", tags=["scraping"])


@scraping_router.post("/scrape-cars-query/{headless}", response_model=ScrapingResults)
async def scrape_car(
    service: ScrapingServiceDependency,
    config: ScrapingConfigByQuery,
    headless: bool = True,
):
    return await service.scrape_car(config, headless=headless)


@scraping_router.post(
    "/scrape-cars-by-car-model/{headless}", response_model=ScrapingResults
)
async def scrape_cars_by_car_model(
    service: ScrapingServiceDependency,
    car_repo: CarModelRepositoryDependency,
    config: ScrapingConfigByCarModel,
    headless: bool = True,
):
    car_model = await car_repo.get_car_model_by_id(config.car_id)

    return await service.scrape_car(ScrapingConfigByQuery(
        brand=car_model.brand,
        model=car_model.model,
        year_from=str(car_model.year_from),
        year_to=str(car_model.year_to),
        car_platform_ids=config.car_platform_ids
    ), headless=headless, car_id=car_model.id)


@scraping_router.get("/scraped-cars", response_model=list[ScrapedRequestResponse])
async def get_scraped_cars(
    repo: ScrapingRepositoryDependency,
    id: Annotated[int | None, Query()] = None,
    car_id: Annotated[int | None, Query()] = None,
    req_id: Annotated[int | None, Query()] = None,
    car_platform_id: Annotated[int | None, Query()] = None,
):
    return await repo.fetch_scraped_cars(
        id=id, car_id=car_id, req_id=req_id, car_platform_id=car_platform_id
    )


@scraping_router.get("/scrape-requests", response_model=list[ScrapeRequestResponse])
async def list_scrape_requests(
    repo: ScrapingRepositoryDependency,
):
    scrape_requests = await repo.list_scrape_requests()
    return [ScrapeRequestResponse.model_validate(r) for r in scrape_requests]


@scraping_router.get(
    "/scrape-request/{request_id}", response_model=ScrapeRequestResponse
)
async def get_scrape_request(
    request_id: int,
    repo: ScrapingRepositoryDependency,
):
    scrape_request = await repo.fetch_scrape_request(request_id)
    return ScrapeRequestResponse.model_validate(scrape_request)
