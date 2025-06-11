import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re

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
        await (
            page.locator(item_selector)
            .get_by_text(re.compile(f"^{re.escape(value)}$", re.IGNORECASE))
            .first.click()
        )
        

    if close_selector:
        await close_popup(page, close_selector)

class CarDataParser:
    @staticmethod
    def parse_text_for_price(content_element):
        text = content_element.get_text(strip=True) if content_element else None
        if text and "=" in text:
            text = text.split('=')[0].strip()
        
        if text is None:
            return None, None
        
        text = text.replace("'", "").replace(",", "").strip()
    
        currency = None
        if '$' in text:
            currency = '$'
            text = text.replace('$', '').strip()
        elif 'USD' in text:
            currency = 'USD'
            text = text.replace('USD', '').strip()
        
        try:
            price = ''.join(c for c in text if c.isdigit())
            price = int(price) if price else None
        except ValueError:
            price = None
        
        return price, currency

    @staticmethod
    def parse_text_for_year(content_element):
        year_text = content_element.get_text(strip=True) if content_element else None
        if year_text and ":" in year_text:
            return year_text.split(':')[1].strip()
        elif year_text and " " in year_text:
            return year_text.split(' ')[-1].strip()
        else:
            return year_text if year_text is not None else None

    @staticmethod
    def parse_text_for_views(content_element):
        text = content_element.get_text(strip=True) if content_element else None
        if content_element and len(content_element.contents) > 1:
            return int(content_element.contents[1])
        elif text and " " in text:
            parsed_text_with_spaces = text.split(' ')[1].strip() if " " in text else text
            return int(parsed_text_with_spaces) if parsed_text_with_spaces.isdigit() else None
        else:
            return int(text.strip()) if text else None

    @staticmethod
    def parse_text_for_mileage(content_element):
        mileage_text = content_element.get_text(strip=True) if content_element else None
        if mileage_text and ":" in mileage_text:
            mileage_text = mileage_text.split(':')[1].strip()
        
        if mileage_text is None:
            return None, None
    
        mileage_text = mileage_text.replace("'", "").replace(",", "").strip()
        
        unit = None
        multiply_by_1000 = False
        if 'км' in mileage_text.lower():
            unit = 'км'
            if 'тис' in mileage_text.lower():
                multiply_by_1000 = True
                mileage_text = mileage_text.lower().replace('км', '').replace('тис.', '').replace('тис', '').replace('пробіг', '').strip()
        
        try:
            mileage = ''.join(c for c in mileage_text if c.isdigit())
            if mileage:
                mileage = int(mileage) * 1000 if multiply_by_1000 else int(mileage)
            else:
                mileage = None
        except ValueError:
            mileage = None
        
        return mileage, unit

async def scrape_car_details(page, url, selectors, search_position):
    await page.goto(url)

    html_content = await page.content()
    soup = BeautifulSoup(html_content, 'html.parser')

    data = {}
    try:
        data['url'] = url

        data['search_position'] = search_position

        # Extract year
        year_element = soup.select_one(selectors['year'])
        data['year'] = CarDataParser.parse_text_for_year(year_element)


        # Extract price
        price_element = soup.select_one(selectors['price'])
        price, currency = CarDataParser.parse_text_for_price(price_element)
        data['price'] = price
        data['currency'] = currency

        # Extract mileage
        mileage_element = soup.select_one(selectors['mileage'])
        mileage, mileage_unit = CarDataParser.parse_text_for_mileage(mileage_element)
        data['mileage'] = mileage
        data['mileage_unit'] = mileage_unit

        # Extract views
        views_element = soup.select_one(selectors['views'])
        if views_element:
            data['views'] = CarDataParser.parse_text_for_views(views_element)
        else:
            for _ in range(50):
                await page.mouse.wheel(0, 300)
                await page.wait_for_timeout(100)
                html_content = await page.content()
                soup = BeautifulSoup(html_content, 'html.parser')
                views_element = soup.select_one(selectors['views'])
                if views_element:
                    data['views'] = CarDataParser.parse_text_for_views(views_element)
                    break
            else:
                data['views'] = None

    except Exception as e:
        data['error'] = str(e)

    return data

async def scrape_car_list(page, car_list_selector, url_to_details, base_url=None):
    car_urls = []
    await page.wait_for_selector(car_list_selector, state="visible")
    elements = await page.locator(f"{car_list_selector} {url_to_details}").all()
    for element in elements:
        url = await element.get_attribute("href")
        if url and base_url:
            domain_match = re.match(
                r"https?://([^/]+)", base_url
            )
            if domain_match:
                domain = domain_match.group(1)
                if domain not in url:
                    url = f"https://{domain}/{url.lstrip('/')}"
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
        await page.wait_for_timeout(100)
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
            base_url = "https://auto.ria.com/uk/legkovie/"
            await page.goto(base_url)

            brand_selector = 'label[for="brandTooltipBrandAutocompleteInput-1"]'
            brand_item_selector = 'div#brandTooltipBrandAutocomplete-1 li.list-item a.item'
            
            model_selector = 'label[for="brandTooltipModelAutocompleteInput-1"]'
            model_item_selector = 'div#brandTooltipModelAutocomplete-1 li.list-item a.item'
            
            year_from_selector = 'div.e-year div.middle select#year'
            year_from_item_selector = 'div.e-year div.middle select#year option'

            year_to_selector = 'div.e-year div.middle select#yearTo'
            year_to_item_selector = 'div.e-year div.middle select#yearTo option'
            
            button_selector = 'div.footbar-search__main button[type="submit"]'

            car_list_selector = 'div#searchResults'
            url_to_details = 'a.address'

            close_selector = ''

            selectors = {
                'year': 'div.heading > h1.head',
                'price': 'section.price > div.price_value strong',
                'mileage': 'div.base-information.bold',
                'views': 'aside li#viewsStatistic > span.bold.load'
            }

            await select_option_or_click(page, brand_selector, brand_item_selector, "Volkswagen", close_selector)
            await select_option_or_click(page, model_selector, model_item_selector, "golf", close_selector)
            await select_option_or_click(page, year_from_selector, year_from_item_selector, "2014", close_selector)
            await select_option_or_click(page, year_to_selector, year_to_item_selector, "2019", close_selector)

            if button_selector:
                await page.locator(button_selector).click()

            car_urls = await scrape_car_list(page, car_list_selector, url_to_details, base_url)
            car_list = []

            search_position = 1
            for url in car_urls:
                car_data = await scrape_car_details(page, url, selectors, search_position)
                await add_to_list(car_list, car_data)
                search_position += 1
            
            await print_car_list(car_list)
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())