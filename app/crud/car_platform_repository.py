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
    
    async def get_car_platform_by_id(self, car_platform_id: int) -> CarPlatform:
        query = select(CarPlatform).where(CarPlatform.id == car_platform_id)
        response = await self.session.execute(query)
        car_platform = response.scalar_one_or_none()

        if not car_platform:
            raise HTTPException(status_code=404, detail="Car platform not found")

        return car_platform
    
    async def update_car_platform(
        self, car_platform_id: int, car_platform: CarPlatformCreateUpdate
    ) -> CarPlatform:
        try:
            query = select(CarPlatform).where(CarPlatform.id == car_platform_id)
            response = await self.session.execute(query)
            existing_car_platform = response.scalar_one_or_none()

            if not existing_car_platform:
                raise HTTPException(status_code=404, detail="Car platform not found")

            for key, value in car_platform.model_dump().items():
                setattr(existing_car_platform, key, value)

            await self.session.commit()
            await self.session.refresh(existing_car_platform)
            return existing_car_platform
        
        except IntegrityError as e:
            await self.session.rollback()
            original_error = e.orig
            raise HTTPException(status_code=400, detail=str(original_error))
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=500, detail=str(e))
    
    async def delete_car_platform(self, car_platform_id: int) -> None:
        try:
            query = select(CarPlatform).where(CarPlatform.id == car_platform_id)
            response = await self.session.execute(query)
            existing_car_platform = response.scalar_one_or_none()

            if not existing_car_platform:
                raise HTTPException(status_code=404, detail="Car platform not found")

            await self.session.delete(existing_car_platform)
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=500, detail=str(e))


CarPlatformRepositoryDependency = Annotated[
    CarPlatformRepository, Depends(CarPlatformRepository)
]
