from pydantic import BaseModel

class CarPlatformCreateUpdate(BaseModel):
    name: str
    base_search_url: str
    brand_selector: str
    model_selector: str
    year_from_selector: str
    year_to_selector: str

class CarPlatformResponse(CarPlatformCreateUpdate):
    id: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True