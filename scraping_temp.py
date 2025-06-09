import asyncio
from playwright.async_api import async_playwright
import re

async def select_option_or_click(page, selector, item_selector, value):
    await page.wait_for_timeout(2000)
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

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0'
        )
        page = await context.new_page()

        try:
            await page.goto("https://www.olx.ua/uk/transport/legkovye-avtomobili/")

            brand_selector = 'div:has(> p:has-text("Підкатегорія")) div.css-1kh9n61'
            brand_item_selector = 'div.css-192xv8v div.css-1msmb8o'

            model_selector = 'div:has(> div > span:has-text("Модель")) div.css-t0lbh8'
            model_item_selector = 'div.css-k4teaq div.css-1d91jbp div.n-checkbox-label-text-wrapper p'

            year_from_selector = 'div.css-1y0lxug:has(> div:has-text("Рік випуску")) input[data-testid="range-from-input"]'
            year_from_item_selector = ''

            year_to_selector = 'div.css-1y0lxug:has(> div:has-text("Рік випуску")) input[data-testid="range-to-input"]'
            year_to_item_selector = ''

            button_selector = ''

            await page.wait_for_selector(brand_selector, state="visible")

            await select_option_or_click(page, brand_selector, brand_item_selector, "Toyota")

            await select_option_or_click(page, model_selector, model_item_selector, "Camry")

            await select_option_or_click(page, year_from_selector, year_from_item_selector, "2018")
            await select_option_or_click(page, year_to_selector, year_to_item_selector, "2020")

            if button_selector:
                await page.locator(button_selector).click()

            await page.wait_for_timeout(5000)

        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())