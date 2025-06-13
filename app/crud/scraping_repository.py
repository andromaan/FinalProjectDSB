from fastapi import Depends, HTTPException
from db import SessionContext
from typing import Annotated, List
from sqlalchemy import select, insert
from schemas.scraped_car_schema import (
    ScrapedCarCreate,
    ScrapedRequestCreate,
)
from models.scraped_car import ScrapedCar
from models.scrape_request import ScrapeRequest
from datetime import datetime

class ScrapingRepository:
    def __init__(self, session: SessionContext):
        self.session = session

    async def add_scrape_request(
        self, scrape_req: ScrapedRequestCreate
    ) -> ScrapeRequest:
        scrape_req = ScrapeRequest(
            **scrape_req.model_dump(),
        )
        self.session.add(scrape_req)
        await self.session.commit()
        await self.session.refresh(scrape_req)
        return scrape_req

    async def add_scraped_car(self, car_data: ScrapedCarCreate) -> ScrapedCar:
        stmt = (
            insert(ScrapedCar)
            .values(**car_data.model_dump())
            .returning(ScrapedCar)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one()

    async def fetch_scraped_cars(
        self,
        id: int | None = None,
        car_id: int | None = None,
        req_id: int | None = None,
        car_platform_id: int | None = None,
        date_of_scrape_from: datetime | None = None,
        date_of_scrape_to: datetime | None = None,
    ) -> List[ScrapedCar]:
        stmt = select(ScrapedCar)
        if id is not None:
            stmt = stmt.where(ScrapedCar.id == id)
        if car_id is not None:
            stmt = stmt.where(ScrapedCar.car_id == car_id)
        if req_id is not None:
            stmt = stmt.where(ScrapedCar.request_id == req_id)
        if car_platform_id is not None:
            stmt = stmt.where(ScrapedCar.car_platform_id == car_platform_id)
        if date_of_scrape_from is not None:
            stmt = stmt.where(ScrapedCar.scraped_at >= date_of_scrape_from)
        if date_of_scrape_to is not None:
            stmt = stmt.where(ScrapedCar.scraped_at <= date_of_scrape_to)
        result = await self.session.execute(stmt)
        cars = result.scalars().all()
        if id is not None and not cars:
            raise HTTPException(status_code=404, detail="Scraped car not found")
        return list(cars)

    async def list_scrape_requests(self) -> List[ScrapeRequest]:
        result = await self.session.execute(select(ScrapeRequest))
        return list(result.scalars().all())

    async def fetch_scrape_request(self, req_id: int) -> ScrapeRequest:
        result = await self.session.execute(
            select(ScrapeRequest).where(ScrapeRequest.id == req_id)
        )
        req = result.scalar_one_or_none()
        if req is None:
            raise HTTPException(status_code=404, detail="Scrape request not found")
        return req


ScrapingRepositoryDependency = Annotated[
    ScrapingRepository, Depends(ScrapingRepository)
]