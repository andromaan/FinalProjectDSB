from typing import List, Annotated
from fastapi import HTTPException, Depends
from datetime import datetime, timezone
import re
import asyncio
from playwright.async_api import async_playwright
from schemas.scraping import (
    ScrapingConfig,
    ScrapingResultSuccess,
    ScrapingResultError,
    ScrapingResults,
    Summary,
    ScrapedProductCreate,
)
from crud.scraping_repository import ScrapingRepositoryDependency
from crud.marketplace_repository import MarketplaceRepositoryDependency
from services.scraping_utils import scrape_product_data
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScrapingService:
    def __init__(
        self,
        repo_marketplace: MarketplaceRepositoryDependency,
        repo_scraping: ScrapingRepositoryDependency,
    ):
        self.repo_marketplace = repo_marketplace
        self.repo_scraping = repo_scraping

    async def scrape_single_marketplace(
        self,
        context,
        marketplace,
        product_name: str,
        scrape_request_id: int,
        semaphore: asyncio.Semaphore,
    ) -> ScrapingResultSuccess | ScrapingResultError:
        async with semaphore:
            try:
                product_title, price, url = await scrape_product_data(
                    context=context, marketplace=marketplace, product_name=product_name
                )

                scraped_currency = None
                if price:
                    match = re.search(r"([^\d.,\s]+)", price)
                    scraped_currency = match.group(1) if match else None

                if url and marketplace.base_search_url:
                    domain_match = re.match(
                        r"https?://([^/]+)", marketplace.base_search_url
                    )
                    if domain_match:
                        domain = domain_match.group(1)
                        if domain not in url:
                            url = f"https://{domain}/{url.lstrip('/')}"

                scraping_result_success = ScrapingResultSuccess(
                    marketplace_name=marketplace.name,
                    status="success",
                    product_title=product_title,
                    price=price,
                    url=url,
                    scraped_at=datetime.now(timezone.utc),
                )

                await self.repo_scraping.create_scraped_product(
                    product_data=ScrapedProductCreate(
                        request_id=scrape_request_id,
                        marketplace_id=marketplace.id,
                        scraped_product_title=product_title,
                        scraped_price=price,
                        scraped_currency=scraped_currency,
                        product_url=url,
                        status="success",
                        error_message=None,
                    )
                )
                return scraping_result_success

            except RuntimeError as e:
                error_message = str(e)
                status = "error_scraping"
                if "Product not found" in error_message:
                    status = "not_found"
                elif "Invalid product selector" in error_message:
                    status = "invalid_selector"
                elif "Site unavailable" in error_message:
                    status = "site_unavailable"

                scraping_result_error = ScrapingResultError(
                    marketplace_name=marketplace.name,
                    status=status,
                    error_message=error_message,
                    scraped_at=datetime.now(timezone.utc),
                )

                await self.repo_scraping.create_scraped_product(
                    product_data=ScrapedProductCreate(
                        request_id=scrape_request_id,
                        marketplace_id=marketplace.id,
                        scraped_product_title=product_name,
                        scraped_price=None,
                        scraped_currency=None,
                        product_url=None,
                        status=status,
                        error_message=error_message,
                    )
                )
                return scraping_result_error

    async def scrape_product(self, config: ScrapingConfig) -> ScrapingResults:
        all_marketplaces = await self.repo_marketplace.get_all_active_marketplaces()

        if config.marketplace_ids:
            marketplace_map = {mp.id: mp for mp in all_marketplaces}
            selected_marketplaces = [
                mp
                for mp_id, mp in marketplace_map.items()
                if mp_id in config.marketplace_ids
            ]
            if len(selected_marketplaces) != len(config.marketplace_ids):
                invalid_ids = set(config.marketplace_ids) - set(marketplace_map.keys())
                raise HTTPException(
                    status_code=404,
                    detail=f"Marketplace(s) with ID(s) {invalid_ids} not found",
                )
        else:
            selected_marketplaces = all_marketplaces

        results: List[ScrapingResultSuccess | ScrapingResultError] = []
        scraping_request = await self.repo_scraping.create_scrape_request(
            product_name=config.product_name
        )

        max_concurrent_requests = 4
        semaphore = asyncio.Semaphore(max_concurrent_requests)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0"
            )

            tasks = [
                self.scrape_single_marketplace(
                    context=context,
                    marketplace=marketplace,
                    product_name=config.product_name,
                    scrape_request_id=scraping_request.id,
                    semaphore=semaphore,
                )
                for marketplace in selected_marketplaces
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
            product_name_searched=config.product_name,
            results=results,
            summary=summary,
        )


def get_scraping_service(
    repo_marketplace: MarketplaceRepositoryDependency,
    repo_scraping: ScrapingRepositoryDependency,
):
    return ScrapingService(
        repo_marketplace=repo_marketplace, repo_scraping=repo_scraping
    )


ScrapingServiceDependency = Annotated[ScrapingService, Depends(get_scraping_service)]
