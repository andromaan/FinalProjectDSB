from typing import Tuple, Optional
from playwright.async_api import (
    BrowserContext,
    Page,
    TimeoutError,
    Error as PlaywrightError,
)
from models.marketplace import Marketplace
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def scrape_product_data(
    context: BrowserContext, marketplace: Marketplace, product_name: str
) -> Tuple[str, str, str]:
    page: Optional[Page] = None
    try:
        logger.info(f"Scraping {product_name} on {marketplace.name}")
        page = await context.new_page()

        base_search_url = marketplace.base_search_url + product_name.replace(" ", "+")
        logger.debug(f"Navigating to {base_search_url}")

        try:
            await page.goto(base_search_url, timeout=10000)
        except PlaywrightError as e:
            raise RuntimeError(f"Site unavailable ({marketplace.name}): {str(e)}")

        try:
            await page.wait_for_selector(marketplace.product_selector, timeout=5000)
            product_exists = (
                await page.locator(marketplace.product_selector).count() > 0
            )
            if not product_exists:
                raise RuntimeError(f"Product not found on {marketplace.name}")
        except TimeoutError:
            raise RuntimeError(
                f"Invalid product selector ({marketplace.product_selector}) on {marketplace.name}"
            )

        try:
            await page.wait_for_selector(marketplace.title_selector, timeout=5000)
            product_title = await page.locator(
                marketplace.title_selector
            ).first.inner_text()
            if not product_title or product_title.strip() == "":
                raise RuntimeError(
                    f"Failed to retrieve product title on {marketplace.name}"
                )
        except (TimeoutError, PlaywrightError):
            raise RuntimeError(
                f"Invalid title selector ({marketplace.title_selector}) on {marketplace.name}"
            )

        try:
            await page.wait_for_selector(marketplace.price_selector, timeout=5000)
            price = await page.locator(marketplace.price_selector).first.inner_text()
            if not price or price.strip() == "":
                raise RuntimeError(
                    f"Failed to retrieve product price on {marketplace.name}"
                )
        except (TimeoutError, PlaywrightError):
            raise RuntimeError(
                f"Invalid price selector ({marketplace.price_selector}) on {marketplace.name}"
            )

        try:
            await page.wait_for_selector(marketplace.link_selector, timeout=5000)
            url = await page.locator(marketplace.link_selector).first.get_attribute(
                "href"
            )
            if url is None or url.strip() == "":
                raise RuntimeError(
                    f"Failed to retrieve product URL on {marketplace.name}"
                )
        except (TimeoutError, PlaywrightError):
            raise RuntimeError(
                f"Invalid URL selector ({marketplace.link_selector}) on {marketplace.name}"
            )

        return product_title, price, url

    except RuntimeError as e:
        raise e
    except Exception as e:
        raise RuntimeError(f"Unknown scraping error on {marketplace.name}: {str(e)}")
    finally:
        if page:
            await page.close()
