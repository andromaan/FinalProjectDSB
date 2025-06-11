from fastapi import APIRouter
from crud.car_model_repository import CarModelRepositoryDependency
from schemas.car_model_schema import CarModelCreateUpdate, CarModelResponse

car_model_router = APIRouter(prefix="/car-models", tags=["car-models"])

@car_model_router.post("", response_model=CarModelResponse)
async def create_car_model(
    repo: CarModelRepositoryDependency, car_model: CarModelCreateUpdate
):
    created_car_model = await repo.create_car_model(car_model)
    return CarModelResponse.model_validate(created_car_model)

@car_model_router.get("/{car_model_id}", response_model=CarModelResponse)
async def get_car_model_by_id(
    car_model_id: int, repo: CarModelRepositoryDependency
):
    car_model = await repo.get_car_model_by_id(car_model_id)
    return CarModelResponse.model_validate(car_model)

@car_model_router.get("", response_model=list[CarModelResponse])
async def get_all_car_models(repo: CarModelRepositoryDependency):
    car_models = await repo.get_all_car_models()
    return [CarModelResponse.model_validate(m) for m in car_models]

@car_model_router.put("/{car_model_id}", response_model=CarModelResponse)
async def update_car_model(
    car_model_id: int,
    car_model: CarModelCreateUpdate,
    repo: CarModelRepositoryDependency
):
    updated_car_model = await repo.update_car_model(car_model_id, car_model)
    return CarModelResponse.model_validate(updated_car_model)

@car_model_router.delete("/{car_model_id}", response_model=None)
async def delete_car_model(
    car_model_id: int, repo: CarModelRepositoryDependency
):
    await repo.delete_car_model(car_model_id)
    return {"detail": "Car model deleted successfully"}

