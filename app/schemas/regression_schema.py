from pydantic import BaseModel, Field
from typing import List
from datetime import datetime, timezone


class RegressionInputSearchPosition(BaseModel):
    year_of_car: int = Field(..., ge=1985, le=datetime.now(timezone.utc).year)
    price: float = Field(..., ge=0)
    mileage: float = Field(..., ge=0)
    number_of_views: int = Field(..., ge=0)


class RegressionInputPrice(BaseModel):
    search_position: float = Field(..., ge=0, le=10)
    mileage: float = Field(..., ge=0)
    year_of_car: int = Field(..., ge=1985, le=datetime.now(timezone.utc).year)
    number_of_views: int = Field(..., ge=0)


class RegressionOutput(BaseModel):
    predicted_value: float


class Coefficient(BaseModel):
    feature: str
    coefficient: float
    p_value: float


class RegressionCoefficients(BaseModel):
    coefficients: List[Coefficient]
