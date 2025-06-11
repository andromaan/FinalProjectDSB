from fastapi import Depends, HTTPException
from sqlalchemy import select
from typing import Annotated, List
from db import SessionContext
from sqlalchemy.exc import IntegrityError
from models.car import Car
from schemas.car_model_schema import CarModelCreateUpdate

class CarModelRepository:
    def __init__(self, session: SessionContext):
        self.session = session

    async def create_car_model(
        self, car_model: CarModelCreateUpdate
    ) -> Car:
        try:
            new_car_model = Car(**car_model.model_dump())
            self.session.add(new_car_model)
            await self.session.commit()
            await self.session.refresh(new_car_model)
            return new_car_model

        except IntegrityError as e:
            await self.session.rollback()
            original_error = e.orig
            raise HTTPException(status_code=400, detail=str(original_error))
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_all_car_models(self) -> List[Car]:
        query = select(Car)
        response = await self.session.execute(query)
        return [car for car in response.scalars()]
    
    async def get_car_model_by_id(self, car_model_id: int) -> Car:
        query = select(Car).where(Car.id == car_model_id)
        response = await self.session.execute(query)
        car_model = response.scalar_one_or_none()

        if not car_model:
            raise HTTPException(status_code=404, detail="Car model not found")

        return car_model
    
    async def update_car_model(
        self, car_model_id: int, car_model: CarModelCreateUpdate
    ) -> Car:
        try:
            query = select(Car).where(Car.id == car_model_id)
            response = await self.session.execute(query)
            existing_car_model = response.scalar_one_or_none()

            if not existing_car_model:
                raise HTTPException(status_code=404, detail="Car model not found")

            for key, value in car_model.model_dump().items():
                setattr(existing_car_model, key, value)

            await self.session.commit()
            await self.session.refresh(existing_car_model)
            return existing_car_model

        except IntegrityError as e:
            await self.session.rollback()
            original_error = e.orig
            raise HTTPException(status_code=400, detail=str(original_error))
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        
    async def delete_car_model(self, car_model_id: int) -> None:
        try:
            query = select(Car).where(Car.id == car_model_id)
            response = await self.session.execute(query)
            existing_car_model = response.scalar_one_or_none()

            if not existing_car_model:
                raise HTTPException(status_code=404, detail="Car model not found")

            await self.session.delete(existing_car_model)
            await self.session.commit()

        except Exception as e:
            await self.session.rollback()
            raise HTTPException(status_code=500, detail=str(e))

CarModelRepositoryDependency = Annotated[
    CarModelRepository,
    Depends(CarModelRepository)
]