from fastapi import Depends, HTTPException
from db import SessionContext
from typing import Annotated, List
from sqlalchemy import select, insert, delete
from schemas.scraped_car_schema import (
    ScrapedCarCreate,
    ScrapedRequestCreate,
    ScrapedCarQuery,
)
from models.scraped_car import ScrapedCar
from models.scrape_request import ScrapeRequest


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
        stmt = insert(ScrapedCar).values(**car_data.model_dump()).returning(ScrapedCar)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one()

    async def fetch_scraped_cars(
        self,
        car_search_criteria: ScrapedCarQuery = ScrapedCarQuery(),
    ) -> List[ScrapedCar]:
        stmt = select(ScrapedCar)
        if car_search_criteria.id is not None:
            stmt = stmt.where(ScrapedCar.id == car_search_criteria.id)
        if car_search_criteria.car_id is not None:
            if car_search_criteria.car_id == 0:
                stmt = stmt.where(ScrapedCar.car_id.is_(None))
            else:
                stmt = stmt.where(ScrapedCar.car_id == car_search_criteria.car_id)
        if car_search_criteria.request_id is not None:
            stmt = stmt.where(ScrapedCar.request_id == car_search_criteria.request_id)
        if car_search_criteria.car_platform_id is not None:
            stmt = stmt.where(
                ScrapedCar.car_platform_id == car_search_criteria.car_platform_id
            )
        if car_search_criteria.date_of_scrape_from is not None:
            stmt = stmt.where(
                ScrapedCar.scraped_at >= car_search_criteria.date_of_scrape_from
            )
        if car_search_criteria.date_of_scrape_to is not None:
            stmt = stmt.where(
                ScrapedCar.scraped_at <= car_search_criteria.date_of_scrape_to
            )
        if car_search_criteria.name_of_scrape_query is not None:
            stmt = stmt.join(ScrapeRequest).where(
                ScrapeRequest.search_query.ilike(
                    f"%{car_search_criteria.name_of_scrape_query}%"
                )
            )
        result = await self.session.execute(stmt)
        cars = result.scalars().all()
        if car_search_criteria.id is not None and not cars:
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

    async def delete_scrape_request(self, req_id: int) -> None:
        try:
            stmt = delete(ScrapeRequest).where(ScrapeRequest.id == req_id)
            result = await self.session.execute(stmt)
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Scrape request not found")
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=500, detail=str(e))


ScrapingRepositoryDependency = Annotated[
    ScrapingRepository, Depends(ScrapingRepository)
]
