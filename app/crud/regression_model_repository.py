from fastapi import Depends, HTTPException
from db import SessionContext
from typing import Annotated, List
from sqlalchemy import select, update, delete
from models.regression_model import RegressionModel


class RegressionModelRepository:
    def __init__(self, session: SessionContext):
        self.session = session

    async def add_regression_model(self, model_data: dict) -> RegressionModel:
        model = RegressionModel(**model_data)
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return model

    async def get_regression_model(self, model_id: int) -> RegressionModel:
        result = await self.session.execute(
            select(RegressionModel).where(RegressionModel.id == model_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise HTTPException(status_code=404, detail="Regression model not found")
        return model

    async def list_regression_models(self) -> List[RegressionModel]:
        result = await self.session.execute(select(RegressionModel))
        return list(result.scalars().all())

    async def update_regression_model(
        self, model_id: int, update_data: dict
    ) -> RegressionModel:
        await self.session.execute(
            update(RegressionModel)
            .where(RegressionModel.id == model_id)
            .values(**update_data)
        )
        await self.session.commit()
        return await self.get_regression_model(model_id)

    async def delete_regression_model(self, model_id: int) -> None:
        stmt = delete(RegressionModel).where(RegressionModel.id == model_id)
        result = await self.session.execute(stmt)
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Regression model not found")
        await self.session.commit()


RegressionModelRepositoryDependency = Annotated[
    RegressionModelRepository, Depends(RegressionModelRepository)
]
