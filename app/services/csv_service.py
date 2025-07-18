import csv
import io
from typing import Annotated
from fastapi import Depends
from crud.scraping_repository import ScrapingRepositoryDependency
from schemas.scraped_car_schema import ScrapedCarQuery
import httpx


async def fetch_exchange_rates() -> int | None:
    url = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        usd_rate = next(
            (item["rate"] for item in response.json() if item["cc"] == "USD"), None
        )
        return int(usd_rate) if usd_rate is not None else None


class CSVService:
    def __init__(self, scraping_repo: ScrapingRepositoryDependency):
        self.scraping_repo = scraping_repo

    async def generate_scraped_cars_csv(
        self, cars_scraping_query: ScrapedCarQuery
    ) -> io.BytesIO:
        cars = await self.scraping_repo.fetch_scraped_cars(cars_scraping_query)

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")

        headers = [
            "No",
            "scraped_url",
            "search_position",
            "scraped_year",
            "scraped_price",
            "scraped_mileage",
            "scraped_number_of_views",
            "scraped_at",
        ]
        writer.writerow(headers)

        index = 1
        exchange_rate = await fetch_exchange_rates()
        for car in cars:
            if any(
                getattr(car, field) is None
                for field in [
                    "scraped_url",
                    "search_position",
                    "scraped_year",
                    "scraped_price",
                    "scraped_mileage",
                    "scraped_number_of_views",
                    "scraped_at",
                ]
            ):
                continue

            price = car.scraped_price
            if car.scraped_currency in ["грн", "₴"]:
                price = (
                    round(car.scraped_price / exchange_rate) if exchange_rate else price
                )

            row = [
                index,
                car.scraped_url,
                car.search_position,
                car.scraped_year,
                price,
                car.scraped_mileage,
                car.scraped_number_of_views,
                car.scraped_at.isoformat(),
            ]
            writer.writerow(row)
            index += 1

        output.seek(0)
        bytes_output = io.BytesIO(output.getvalue().encode("utf-8"))
        output.close()
        return bytes_output


def get_csv_service(scraping_repo: ScrapingRepositoryDependency):
    return CSVService(scraping_repo=scraping_repo)


CSVServiceDependency = Annotated[CSVService, Depends(get_csv_service)]
