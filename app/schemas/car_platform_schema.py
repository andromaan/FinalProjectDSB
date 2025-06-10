from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CarPlatformCreateUpdate(BaseModel):
    name: str
    base_search_url: str
    brand_selector: str
    brand_item_selector: Optional[str] = None
    model_selector: str
    model_item_selector: Optional[str] = None
    year_from_selector: str
    year_from_item_selector: Optional[str] = None
    year_to_selector: str
    year_to_item_selector: Optional[str] = None
    button_selector: Optional[str] = None
    car_list_selector: str
    url_to_details: str
    close_selector: Optional[str] = None
    year_bs4_selector: str
    price_bs4_selector: str
    mileage_bs4_selector: str
    views_bs4_selector: str


class CarPlatformResponse(CarPlatformCreateUpdate):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True