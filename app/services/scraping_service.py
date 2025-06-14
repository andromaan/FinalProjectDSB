from typing import List, Annotated, Optional
from fastapi import HTTPException, Depends
from datetime import datetime, timezone
import asyncio
from playwright.async_api import async_playwright
from schemas.scraped_car_schema import (
    ScrapingConfigByQuery,
    ScrapingResultSuccess,
    ScrapingResultError,
    ScrapingResults,
    Summary,
    ScrapedCarCreate,
    ScrapingStatus,
    ScrapedRequestCreate,
    ScrapingConfigByCarsModel,
    ScrapingResultsByCarModels
)
from crud.scraping_repository import ScrapingRepositoryDependency
from crud.car_platform_repository import CarPlatformRepositoryDependency
from crud.car_model_repository import CarModelRepositoryDependency
from services.scraping_utils import scrape_car_data
import time
from services.logger_service import logger


class ScrapingService:
    def __init__(
        self,
        repo_car_platform: CarPlatformRepositoryDependency,
        repo_scraping: ScrapingRepositoryDependency,
        repo_car_model: CarModelRepositoryDependency,
    ):
        self.repo_car_platform = repo_car_platform
        self.repo_scraping = repo_scraping
        self.repo_car_model = repo_car_model

    async def scrape_single_car_platform(
        self,
        context,
        car_platform,
        config: ScrapingConfigByQuery,
        scrape_request_id: int,
        semaphore: asyncio.Semaphore,
        car_id: Optional[int] = None
    ) -> ScrapingResultSuccess | ScrapingResultError:
        async with semaphore:
            start_time = time.perf_counter()
            try:
                car_results = await scrape_car_data(
                    context=context,
                    car_platform=car_platform,
                    brand=config.brand,
                    model=config.model,
                    year_from=config.year_from,
                    year_to=config.year_to,
                )

                for search_position, car_data in enumerate(car_results, 1):
                    await self.repo_scraping.add_scraped_car(
                        car_data=ScrapedCarCreate(
                            request_id=scrape_request_id,
                            car_platform_id=car_platform.id,
                            car_id=car_id,
                            scraped_url=car_data.url,
                            search_position=search_position,
                            scraped_year=car_data.year,
                            scraped_price=car_data.price,
                            scraped_currency=car_data.currency,
                            scraped_mileage=car_data.mileage,
                            scraped_mileage_unit=car_data.mileage_unit,
                            scraped_number_of_views=car_data.views,
                            scraped_at=car_data.scraped_at,
                            status=ScrapingStatus.SUCCESS,
                            error_message=None,
                        )
                    )

                time_to_scrape_platform = time.perf_counter() - start_time
                logger.info(
                    f"Scraped {car_platform.name} in {time_to_scrape_platform:.2f} seconds"
                )

                # Return the first result for simplicity in results summary
                return ScrapingResultSuccess(
                    marketplace_name=car_platform.name,
                    status="success",
                    cars_scraped=len(car_results),
                    time_to_scrape_platform=f"{time_to_scrape_platform:.2f} seconds",
                    car_id=car_id,
                    scraped_at=datetime.now(timezone.utc),
                )

            except RuntimeError as e:
                error_message = str(e)
                status = ScrapingStatus.ERROR_SCRAPING
                if "not found" in error_message.lower():
                    status = ScrapingStatus.NOT_FOUND
                elif "selector" in error_message.lower():
                    status = ScrapingStatus.INVALID_SELECTOR
                elif "site unavailable" in error_message.lower():
                    status = ScrapingStatus.SITE_UNAVAILABLE

                await self.repo_scraping.add_scraped_car(
                    car_data=ScrapedCarCreate(
                        request_id=scrape_request_id,
                        car_platform_id=car_platform.id,
                        car_id=car_id,
                        scraped_url=None,
                        search_position=None,
                        scraped_year=None,
                        scraped_price=None,
                        scraped_currency=None,
                        scraped_mileage=None,
                        scraped_mileage_unit=None,
                        scraped_number_of_views=None,
                        scraped_at=datetime.now(timezone.utc),
                        status=status,
                        error_message=error_message,
                    )
                )
                return ScrapingResultError(
                    marketplace_name=car_platform.name,
                    status=status,
                    error_message=error_message,
                    car_id=car_id,
                    scraped_at=datetime.now(timezone.utc),
                )

    async def scrape_car(
        self, config: ScrapingConfigByQuery, headless: bool = True, car_id: Optional[int] = None
    ) -> ScrapingResults:
        all_car_platforms = await self.repo_car_platform.get_all_car_platforms()

        if config.car_platform_ids:
            marketplace_map = {mp.id: mp for mp in all_car_platforms}
            chosen_car_platforms = [
                mp
                for mp_id, mp in marketplace_map.items()
                if mp_id in config.car_platform_ids
            ]
            if len(chosen_car_platforms) != len(config.car_platform_ids):
                invalid_ids = set(config.car_platform_ids) - set(marketplace_map.keys())
                raise HTTPException(
                    status_code=404,
                    detail=f"Marketplace(s) with ID(s) {invalid_ids} not found",
                )
        else:
            chosen_car_platforms = all_car_platforms

        results: List[ScrapingResultSuccess | ScrapingResultError] = []
        scraping_request = await self.repo_scraping.add_scrape_request(
            ScrapedRequestCreate(
                car_id=car_id,
                search_query=f"{config.brand} {config.model} {config.year_from}-{config.year_to}",
            )
        )

        max_concurrent_requests = 4
        semaphore = asyncio.Semaphore(max_concurrent_requests)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0"
            )

            tasks = [
                self.scrape_single_car_platform(
                    context=context,
                    car_platform=car_platform,
                    config=config,
                    scrape_request_id=scraping_request.id,
                    semaphore=semaphore,
                    car_id=car_id
                )
                for car_platform in chosen_car_platforms
            ]
            results = await asyncio.gather(*tasks, return_exceptions=False)

            await context.close()
            await browser.close()

        summary = Summary(
            total_marketplaces_processed=len(results),
            successful_scrapes=sum(
                1 for r in results if isinstance(r, ScrapingResultSuccess)
            ),
            failed_scrapes=sum(
                1 for r in results if isinstance(r, ScrapingResultError)
            ),
        )

        return ScrapingResults(
            scrape_request_id=scraping_request.id,
            brand_searched=config.brand,
            model_searched=config.model,
            year_from_searched=config.year_from,
            year_to_searched=config.year_to,
            results=results,
            summary=summary,
        )
    
    async def scrape_cars(
        self, config: ScrapingConfigByCarsModel, headless: bool = True
    ) -> ScrapingResultsByCarModels:
        all_car_platforms = await self.repo_car_platform.get_all_car_platforms()

        if config.car_platform_ids:
            marketplace_map = {mp.id: mp for mp in all_car_platforms}
            chosen_car_platforms = [
                cp
                for mp_id, cp in marketplace_map.items()
                if mp_id in config.car_platform_ids
            ]
            if len(chosen_car_platforms) != len(config.car_platform_ids):
                invalid_ids = set(config.car_platform_ids) - set(marketplace_map.keys())
                raise HTTPException(
                    status_code=404,
                    detail=f"Marketplace(s) with ID(s) {invalid_ids} not found",
                )
        else:
            chosen_car_platforms = all_car_platforms

        all_car_models = await self.repo_car_model.get_all_car_models()
        
        if config.car_ids:
            car_model_map = {car.id: car for car in all_car_models}
            chosen_car_models = [
                car
                for car_id, car in car_model_map.items()
                if car_id in config.car_ids
            ]
            if len(chosen_car_models) != len(config.car_ids):
                invalid_ids = set(config.car_ids) - set(car_model_map.keys())
                raise HTTPException(
                    status_code=404,
                    detail=f"Car model(s) with ID(s) {invalid_ids} not found",
                )
        else:
            chosen_car_models = all_car_models

        results: List[ScrapingResultSuccess | ScrapingResultError] = []
        max_concurrent_requests = 4
        semaphore = asyncio.Semaphore(max_concurrent_requests)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            tasks = []
            contexts = {}  # Зберігаємо контексти для кожної машини

            # Створюємо всі таби одразу
            for car in chosen_car_models:
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0"
                )
                contexts[car.id] = context
                scraping_request = await self.repo_scraping.add_scrape_request(
                    ScrapedRequestCreate(
                        car_id=car.id,
                        search_query=f"{car.brand} {car.model} {car.year_from}-{car.year_to}",
                    )
                )

                car_tasks = [
                    self.scrape_single_car_platform(
                        context=context,
                        car_platform=car_platform,
                        config=ScrapingConfigByQuery(
                            brand=car.brand,
                            model=car.model,
                            year_from=str(car.year_from),
                            year_to=str(car.year_to),
                            car_platform_ids=config.car_platform_ids
                        ),
                        scrape_request_id=scraping_request.id,
                        semaphore=semaphore,
                        car_id=car.id
                    )
                    for car_platform in chosen_car_platforms
                ]
                tasks.extend(car_tasks)

            # Виконуємо всі завдання паралельно
            results_raw = await asyncio.gather(*tasks, return_exceptions=True)

            # Закриваємо всі контексти після завершення
            for context in contexts.values():
                await context.close()

            await browser.close()

        # Фільтруємо результати, залишаємо лише валідні
        results: List[ScrapingResultSuccess | ScrapingResultError] = [
            r for r in results_raw if isinstance(r, (ScrapingResultSuccess, ScrapingResultError))
        ]
        error_count = sum(1 for r in results_raw if isinstance(r, Exception))

        summary = Summary(
            total_marketplaces_processed=len(results) + error_count,
            successful_scrapes=len([r for r in results if isinstance(r, ScrapingResultSuccess)]),
            failed_scrapes=error_count + len([r for r in results if isinstance(r, ScrapingResultError)]),
        )

        return ScrapingResultsByCarModels(
            car_ids=[car.id for car in chosen_car_models],
            results=results,
            summary=summary,
        )


def get_scraping_service(
    repo_car_platform: CarPlatformRepositoryDependency,
    repo_scraping: ScrapingRepositoryDependency,
    repo_car_model: CarModelRepositoryDependency,
):
    return ScrapingService(
        repo_car_platform=repo_car_platform,
        repo_scraping=repo_scraping,
        repo_car_model=repo_car_model,
    )


ScrapingServiceDependency = Annotated[ScrapingService, Depends(get_scraping_service)]
