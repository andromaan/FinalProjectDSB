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


@car_platform_router.get("", response_model=list[CarPlatformResponse])
async def get_all_car_platforms(repo: CarPlatformRepositoryDependency):
    car_platforms = await repo.get_all_car_platforms()
    return [CarPlatformResponse.model_validate(m) for m in car_platforms]