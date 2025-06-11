from pydantic import BaseModel
from datetime import datetime

class CarModelCreateUpdate(BaseModel):
    brand: str
    model: str
    year_from: int
    year_to: int

class CarModelResponse(CarModelCreateUpdate):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True