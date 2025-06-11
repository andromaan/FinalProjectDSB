from typing import List, Annotated
from fastapi import HTTPException, Depends
from datetime import datetime, timezone
import asyncio
from playwright.async_api import async_playwright
from schemas.scraped_car_schema import (
    ScrapingConfigQuery,
    ScrapingResultSuccess,
    ScrapingResultError,
    ScrapingResults,
    Summary,
    ScrapedCarCreate,
    ScrapingStatus,
    ScrapedRequestCreate,
    ScrapingConfig
)
from crud.scraping_repository import ScrapingRepositoryDependency
from crud.car_platform_repository import CarPlatformRepositoryDependency
from services.scraping_utils import scrape_car_data
import time
from services.logger_service import logger


class ScrapingService:
    def __init__(
        self,
        repo_car_platform: CarPlatformRepositoryDependency,
        repo_scraping: ScrapingRepositoryDependency,
    ):
        self.repo_car_platform = repo_car_platform
        self.repo_scraping = repo_scraping

    async def scrape_single_marketplace(
        self,
        context,
        car_platform,
        config: ScrapingConfigQuery,
        scrape_request_id: int,
        semaphore: asyncio.Semaphore,
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
                    scraped_at=datetime.now(timezone.utc),
                )

    async def scrape_car_with_query(
        self, config: ScrapingConfigQuery, headless: bool = True
    ) -> ScrapingResults:
        all_marketplaces = await self.repo_car_platform.get_all_car_platforms()

        if config.car_platform_ids:
            marketplace_map = {mp.id: mp for mp in all_marketplaces}
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
            chosen_car_platforms = all_marketplaces

        results: List[ScrapingResultSuccess | ScrapingResultError] = []
        scraping_request = await self.repo_scraping.add_scrape_request(
            ScrapedRequestCreate(
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
                self.scrape_single_marketplace(
                    context=context,
                    car_platform=car_platform,
                    config=config,
                    scrape_request_id=scraping_request.id,
                    semaphore=semaphore,
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

    # async def scrape_car_with_models(
    #     self, config: ScrapingConfig, headless: bool = True
    # ) -> ScrapingResults:
    #     all_car_platforms = await self.repo_car_platform.get_all_car_platforms()

    #     if config.car_platform_ids:
    #         car_platform_map = {mp.id: mp for mp in all_car_platforms}
    #         chosen_car_platforms = [
    #             mp
    #             for mp_id, mp in car_platform_map.items()
    #             if mp_id in config.car_platform_ids
    #         ]
    #         if len(chosen_car_platforms) != len(config.car_platform_ids):
    #             invalid_ids = set(config.car_platform_ids) - set(car_platform_map.keys())
    #             raise HTTPException(
    #                 status_code=404,
    #                 detail=f"Marketplace(s) with ID(s) {invalid_ids} not found",
    #             )
    #     else:
    #         chosen_car_platforms = all_car_platforms

        


    #     results: List[ScrapingResultSuccess | ScrapingResultError] = []
    #     scraping_request = await self.repo_scraping.add_scrape_request(
    #         ScrapedRequestCreate(
    #             search_query=f"{config.brand} {config.model} {config.year_from}-{config.year_to}",
    #         )
    #     )

    #     max_concurrent_requests = 4
    #     semaphore = asyncio.Semaphore(max_concurrent_requests)

    #     async with async_playwright() as p:
    #         browser = await p.chromium.launch(headless=headless)
    #         context = await browser.new_context(
    #             user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0"
    #         )

    #         tasks = [
    #             self.scrape_single_marketplace(
    #                 context=context,
    #                 car_platform=car_platform,
    #                 config=config,
    #                 scrape_request_id=scraping_request.id,
    #                 semaphore=semaphore,
    #             )
    #             for car_platform in chosen_car_platforms
    #         ]
    #         results = await asyncio.gather(*tasks, return_exceptions=False)

    #         await context.close()
    #         await browser.close()

    #     summary = Summary(
    #         total_marketplaces_processed=len(results),
    #         successful_scrapes=sum(
    #             1 for r in results if isinstance(r, ScrapingResultSuccess)
    #         ),
    #         failed_scrapes=sum(
    #             1 for r in results if isinstance(r, ScrapingResultError)
    #         ),
    #     )

    #     return ScrapingResults(
    #         scrape_request_id=scraping_request.id,
    #         brand_searched=config.brand,
    #         model_searched=config.model,
    #         results=results,
    #         summary=summary,
    #     )


def get_scraping_service(
    repo_car_platform: CarPlatformRepositoryDependency,
    repo_scraping: ScrapingRepositoryDependency,
):
    return ScrapingService(
        repo_car_platform=repo_car_platform, repo_scraping=repo_scraping
    )


ScrapingServiceDependency = Annotated[ScrapingService, Depends(get_scraping_service)]
