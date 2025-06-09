import asyncio
from playwright.async_api import async_playwright
import re
from bs4 import BeautifulSoup

async def select_option_or_click(page, selector, item_selector, value, close_selector):
    if close_selector:
        await close_popup(page, close_selector)
    element = await page.locator(selector).first.element_handle()
    tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
    
    if tag_name == "select":
        await page.wait_for_selector(selector, state="visible")
        await page.wait_for_selector(f"{selector} option", state="attached", timeout=10000)
        
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
            value
        )
        
        if option_value:
            await page.locator(selector).select_option(option_value)
        else:
            raise ValueError(f"Option containing text '{value}' not found in select options: {options}")
    elif tag_name == "input":
        await page.wait_for_selector(selector, state="visible")
        await page.locator(selector).first.click()
        await page.locator(selector).first.fill(value)
        await page.locator(selector).first.press("Enter")
    else:
        await page.wait_for_selector(selector, state="visible")
        await page.locator(selector).first.click()
        await page.locator(item_selector).get_by_text(re.compile(value, re.IGNORECASE), exact=True).first.click()
    
    if close_selector:
        await close_popup(page, close_selector)

async def scrape_car_details(page, url, selectors):
    await page.goto(url)

    data = {}
    try:
        data['url'] = url
        data['year'] = await page.locator(selectors['year']).inner_text() or "N/A"

        text = await page.locator(selectors['price']).inner_text() or "N/A"
        if text and "=" in text:
            data['price'] = text.split('=')[0].strip()
        else:
            data['price'] = text if text != "N/A" else "N/A"


        data['mileage'] = await page.locator(selectors['mileage']).inner_text() or "N/A"
        if await page.locator(selectors['views']).count() > 0:
            views_text = await page.locator(selectors['views']).inner_text() or "N/A"
            if " " in views_text:
                data['views'] = views_text.split(' ')[0].strip()
            else:
                data['views'] = views_text
        else:
            for _ in range(50):
                await page.mouse.wheel(0, 300)
                await page.wait_for_timeout(100)
                if await page.locator(selectors['views']).count() > 0:
                    data['views'] = await page.locator(selectors['views']).inner_text() or "N/A"
                    break
                else:
                    data['views'] = "N/A"
    except Exception as e:
        data['error'] = str(e)
    return data

async def scrape_car_list(page, car_list_selector, url_to_details):
    car_urls = []
    await page.wait_for_selector(car_list_selector, state="visible")
    elements = await page.locator(url_to_details).all()
    for element in elements:
        url = await element.get_attribute("href")
        if url:
            car_urls.append(url)
    return car_urls

async def add_to_list(car_list, car_data):
    car_list.append(car_data)

async def print_car_list(car_list):
    for car in car_list:
        print(car)

async def close_popup(page, close_selector):
    try:
        close_btn = page.locator(close_selector)
        await close_btn.wait_for(state="visible", timeout=3000)
        await close_btn.click()
        await page.wait_for_timeout(500)
    except Exception:
        pass

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0'
        )
        page = await context.new_page()

        try:
            base_url = "https://www.olx.ua/uk/transport/legkovye-avtomobili/"
            await page.goto(base_url)

            brand_selector = 'div:has(> p:has-text("Підкатегорія")) div.css-1kh9n61'
            brand_item_selector = 'div.css-192xv8v div.css-1msmb8o'

            model_selector = 'div:has(> div > span:has-text("Модель")) div.css-t0lbh8'
            model_item_selector = 'div.css-k4teaq div.css-1d91jbp div.n-checkbox-label-text-wrapper p'

            year_from_selector = 'div.css-1y0lxug:has(> div:has-text("Рік випуску")) input[data-testid="range-from-input"]'
            year_from_item_selector = ''

            year_to_selector = 'div.css-1y0lxug:has(> div:has-text("Рік випуску")) input[data-testid="range-to-input"]'
            year_to_item_selector = ''

            button_selector = ''

            car_list_selector = 'div[data-testid="listing-grid"].css-j0t2x2'
            url_to_details = 'div[data-cy="ad-card-title"].css-u2ayx9 a.css-1tqlkj0'

            close_selector = 'button[aria-label="Close"]'

            selectors = {
                'year': 'p.css-1los5bp:has-text("Рік випуску")',
                'price': 'div[data-testid="ad-price-container"].css-e2ir3r h3',
                'mileage': 'p.css-1los5bp:has-text("Пробіг:")',
                'views': 'span[data-testid="page-view-counter"].css-16r9cup'
            }

            await select_option_or_click(page, brand_selector, brand_item_selector, "Toyota", close_selector)
            await select_option_or_click(page, model_selector, model_item_selector, "Camry", close_selector)
            await select_option_or_click(page, year_from_selector, year_from_item_selector, "2018", close_selector)
            await select_option_or_click(page, year_to_selector, year_to_item_selector, "2020", close_selector)

            
            if button_selector:
                await page.locator(button_selector).click()
            
            car_urls = await scrape_car_list(page, car_list_selector, url_to_details)
            
            car_list = []
            for url in car_urls:
                if url and base_url:
                    domain_match = re.match(
                        r"https?://([^/]+)", base_url
                    )
                    if domain_match:
                        domain = domain_match.group(1)
                        if domain not in url:
                            url = f"https://{domain}/{url.lstrip('/')}"
                car_data = await scrape_car_details(page, url, selectors)
                await add_to_list(car_list, car_data)
            
            await print_car_list(car_list)
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())