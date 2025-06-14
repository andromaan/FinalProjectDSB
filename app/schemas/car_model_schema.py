from pydantic import BaseModel, Field
from datetime import datetime, timezone

class CarModelCreateUpdate(BaseModel):
    brand: str
    model: str
    year_from: int = Field(..., ge=1985, le=datetime.now(timezone.utc).year)
    year_to: int = Field(..., ge=1985, le=datetime.now(timezone.utc).year)

class CarModelResponse(CarModelCreateUpdate):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True