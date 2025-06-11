from fastapi import APIRouter
from crud.car_platform_repository import CarPlatformRepositoryDependency
from schemas.car_platform_schema import CarPlatformCreateUpdate, CarPlatformResponse

car_platform_router = APIRouter(prefix="/car-platforms", tags=["car-platforms"])


@car_platform_router.post("", response_model=CarPlatformResponse)
async def create_car_platform(
    repo: CarPlatformRepositoryDependency, car_platform: CarPlatformCreateUpdate
):
    created_car_platform = await repo.create_car_platform(car_platform)
    return CarPlatformResponse.model_validate(created_car_platform)

@car_platform_router.get("/{car_platform_id}", response_model=CarPlatformResponse)
async def get_car_platform_by_id(
    car_platform_id: int, repo: CarPlatformRepositoryDependency
):
    car_platform = await repo.get_car_platform_by_id(car_platform_id)
    return CarPlatformResponse.model_validate(car_platform)

@car_platform_router.get("", response_model=list[CarPlatformResponse])
async def get_all_car_platforms(repo: CarPlatformRepositoryDependency):
    car_platforms = await repo.get_all_car_platforms()
    return [CarPlatformResponse.model_validate(m) for m in car_platforms]

@car_platform_router.put("/{car_platform_id}", response_model=CarPlatformResponse)
async def update_car_platform(
    car_platform_id: int,
    car_platform: CarPlatformCreateUpdate,
    repo: CarPlatformRepositoryDependency
):
    updated_car_platform = await repo.update_car_platform(car_platform_id, car_platform)
    return CarPlatformResponse.model_validate(updated_car_platform)

@car_platform_router.delete("/{car_platform_id}", response_model=None)
async def delete_car_platform(
    car_platform_id: int, repo: CarPlatformRepositoryDependency
):
    await repo.delete_car_platform(car_platform_id)
    return {"detail": "Car platform deleted successfully"}