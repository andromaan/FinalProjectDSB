from typing import List, Dict, Optional
from playwright.async_api import BrowserContext, Page
from bs4 import BeautifulSoup, Tag
import re
from models.car_platform import CarPlatform
from services.car_data_parser import CarDataParser
from datetime import datetime, timezone
from schemas.scraped_car_schema import ScrapedCarItem
from services.logger_service import logger


async def select_option_or_click(
    page: Page,
    selector: str,
    item_selector: Optional[str],
    value: str,
    close_selector: Optional[str],
):
    await page.wait_for_timeout(200)
    if close_selector:
        await close_popup(page, close_selector)

    try:
        await page.wait_for_selector(selector, state="visible")
        element = await page.locator(selector).first.element_handle()
        tag_name = await element.evaluate("el => el.tagName.toLowerCase()")

        if tag_name == "select":
            options = await page.locator(selector).evaluate(
                """el => el.options ? Array.from(el.options).map(opt => ({
                    value: opt.value,
                    text: opt.textContent.trim()
                })) : []"""
            )
            option_value = await page.locator(selector).evaluate(
                """(el, searchText) => {
                    const options = Array.from(el.options);
                    const matchingOption = options.find(opt => 
                        opt.textContent.trim().toLowerCase().includes(searchText.toLowerCase())
                    );
                    return matchingOption ? matchingOption.value : null;
                }""",
                value,
            )
            if option_value:
                await page.locator(selector).select_option(option_value)
            else:
                raise ValueError(
                    f"Option '{value}' not found in select options: {options}"
                )
        elif tag_name == "input":
            await page.locator(selector).first.click()
            await page.locator(selector).first.fill(value)
            await page.locator(selector).first.press("Enter")
        else:
            await page.locator(selector).first.click()
            if item_selector:
                max_scroll_attempts = 100

                list_items = page.locator(item_selector)

                parent_container = page.locator(
                    f"{item_selector} >> xpath=.. >> xpath=.."
                ).first
                await parent_container.wait_for(timeout=5000)

                for attempt in range(max_scroll_attempts):
                    try:
                        target = list_items.get_by_text(value, exact=False).first
                        await target.scroll_into_view_if_needed(timeout=200)
                        is_visible = await target.is_visible()
                        if is_visible:
                            await target.click()
                            logger.info(
                                f"Clicked value '{value}' on attempt {attempt + 1}"
                            )
                            break
                    except Exception:
                        if attempt == max_scroll_attempts - 1:
                            item_texts = await list_items.evaluate_all(
                                "elements => elements.map(el => el.textContent.trim())"
                            )
                            logger.error(
                                f"Value '{value}' not found in {item_selector} after {max_scroll_attempts} attempts. Available items: {item_texts}"
                            )
                            raise ValueError(
                                f"Value '{value}' not found in {item_selector} after {max_scroll_attempts} attempts"
                            )

                        await parent_container.evaluate(
                            "element => element.scrollBy(0, 5000)"
                        )
                        logger.debug(
                            f"Scroll attempt {attempt + 1} for value '{value}'"
                        )

        if close_selector:
            await close_popup(page, close_selector)

    except Exception as e:
        raise RuntimeError(f"Failed to interact with selector {selector}: {str(e)}")


async def close_popup(page: Page, close_selector: str):
    try:
        close_btn = page.locator(close_selector)
        await close_btn.wait_for(state="visible", timeout=3000)
        await close_btn.click()
        await page.wait_for_timeout(100)
    except Exception:
        pass


async def scrape_car_list(
    page: Page,
    car_list_selector: str,
    url_to_details: str,
    base_url: str,
    button_selector: Optional[str],
) -> List[str]:
    car_urls = []
    try:
        await page.wait_for_timeout(500) if button_selector is None else 0

        await page.wait_for_selector(car_list_selector, state="visible")
        elements = await page.locator(f"{car_list_selector} {url_to_details}").all()

        for element in elements:
            url = await element.get_attribute("href")
            if url and base_url:
                domain_match = re.match(r"https?://([^/]+)", base_url)
                if domain_match:
                    domain = domain_match.group(1)
                    if domain not in url:
                        url = f"https://{domain}/{url.lstrip('/')}"
            if url:
                car_urls.append(url)
        return car_urls
    except Exception as e:
        raise RuntimeError(f"Failed to scrape car list: {str(e)}")

def find_by_muliple_selectors(soup: BeautifulSoup, selectors: str) -> Optional[Tag]:
    list_selectors = selectors.split(",")
    for selector in list_selectors:
        element = soup.select_one(selector)
        if element:
            return element
    return None

async def scrape_car_details(
    page: Page,
    url: str,
    selectors: Dict[str, str],
) -> ScrapedCarItem | Dict[str, str]:
    try:
        await page.goto(url)
        html_content = await page.content()
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract year
        # year_element = soup.select_one(selectors["year"])
        year_element = find_by_muliple_selectors(soup, selectors["year"])
        year = CarDataParser.parse_text_for_year(year_element)

        # Extract price
        price_element = find_by_muliple_selectors(soup, selectors["price"])
        price, currency = CarDataParser.parse_text_for_price(price_element)

        # Extract mileage
        mileage_element = find_by_muliple_selectors(soup, selectors["mileage"])
        mileage, mileage_unit = CarDataParser.parse_text_for_mileage(mileage_element)

        # Extract views with scrolling if needed
        views_element = find_by_muliple_selectors(soup, selectors["views"])
        if views_element:
            views = CarDataParser.parse_text_for_views(views_element)
        else:
            for _ in range(20):
                await page.mouse.wheel(0, 300)
                await page.wait_for_timeout(100)
                html_content = await page.content()
                soup = BeautifulSoup(html_content, "html.parser")
                views_element = find_by_muliple_selectors(soup, selectors["views"])
                if views_element:
                    views = CarDataParser.parse_text_for_views(views_element)
                    break
            else:
                views = None

        scrape_car_data = ScrapedCarItem(
            url=url,
            year=year,
            price=price,
            currency=currency,
            mileage=mileage,
            mileage_unit=mileage_unit,
            views=views,
            scraped_at=datetime.now(timezone.utc),
        )

        logger.info(f"Scraped data for {url}: {scrape_car_data}")
        return scrape_car_data
    except Exception as e:
        return {"url": url, "error": str(e)}


async def scrape_car_data(
    context: BrowserContext,
    car_platform: CarPlatform,
    brand: str,
    model: str,
    year_from: str,
    year_to: str,
) -> list[ScrapedCarItem]:
    page: Optional[Page] = None
    try:
        logger.info(f"Scraping {brand} {model} on {car_platform.name}")
        page = await context.new_page()

        await page.goto(car_platform.base_search_url)

        # Interact with form elements
        await select_option_or_click(
            page,
            car_platform.brand_selector,
            car_platform.brand_item_selector,
            brand,
            car_platform.close_selector,
        )
        await select_option_or_click(
            page,
            car_platform.model_selector,
            car_platform.model_item_selector,
            model,
            car_platform.close_selector,
        )
        await select_option_or_click(
            page,
            car_platform.year_from_selector,
            car_platform.year_from_item_selector,
            year_from,
            car_platform.close_selector,
        )
        await select_option_or_click(
            page,
            car_platform.year_to_selector,
            car_platform.year_to_item_selector,
            year_to,
            car_platform.close_selector,
        )

        if car_platform.button_selector:
            await page.locator(car_platform.button_selector).click()

        car_urls = await scrape_car_list(
            page,
            car_platform.car_list_selector,
            car_platform.url_to_details,
            car_platform.base_search_url,
            car_platform.button_selector,
        )

        if not car_urls:
            raise RuntimeError(
                f"No cars found for {brand} {model} on {car_platform.name}"
            )

        # Scrape details for each car
        selectors = {
            "year": car_platform.year_bs4_selector,
            "price": car_platform.price_bs4_selector,
            "mileage": car_platform.mileage_bs4_selector,
            "views": car_platform.views_bs4_selector,
        }

        car_results: list[ScrapedCarItem] = []
        for url in car_urls[:10]:
            car_data = await scrape_car_details(page, url, selectors)
            if isinstance(car_data, dict) and "error" in car_data:
                logger.warning(f"Failed to scrape car at {url}: {car_data['error']}")
            elif isinstance(car_data, ScrapedCarItem) and car_data.year is not None and car_data.price is not None:
                car_results.append(car_data)

        if not car_results:
            raise RuntimeError(f"No valid car data retrieved from {car_platform.name}")

        return car_results

    except RuntimeError as e:
        raise e
    except Exception as e:
        raise RuntimeError(f"Unknown scraping error on {car_platform.name}: {str(e)}")
    finally:
        if page:
            await page.close()
