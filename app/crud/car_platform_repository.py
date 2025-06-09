from fastapi import Depends, HTTPException
from sqlalchemy import select
from typing import Annotated, List
from db import SessionContext
from models.car_platform import CarPlatform
from schemas.car_platform_schema import CarPlatformCreateUpdate
from sqlalchemy.exc import IntegrityError

class CarPlatformRepository:
    def __init__(self, session: SessionContext):
        self.session = session

    async def create_car_platform(
        self, car_platform: CarPlatformCreateUpdate
    ) -> CarPlatform:
        try:
            new_car_platform = CarPlatform(**car_platform.model_dump())
            self.session.add(new_car_platform)
            await self.session.commit()
            await self.session.refresh(new_car_platform)
            return new_car_platform

        except IntegrityError as e:
            await self.session.rollback()
            original_error = e.orig
            raise HTTPException(status_code=400, detail=str(original_error))
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        
    async def get_all_car_platforms(self) -> List[CarPlatform]:
        query = select(CarPlatform)
        response = await self.session.execute(query)
        return [car_platform for car_platform in response.scalars()]

CarPlatformRepositoryDependency = Annotated[
    CarPlatformRepository, Depends(CarPlatformRepository)
]
