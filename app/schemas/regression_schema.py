from pydantic import BaseModel
from typing import List

class RegressionInputSearchPosition(BaseModel):
    year_of_car: int
    price: float
    mileage: float
    number_of_views: int

class RegressionInputPrice(BaseModel):
    search_position: float
    mileage: float
    year_of_car: int
    number_of_views: int

class RegressionOutput(BaseModel):
    predicted_value: float

class Coefficient(BaseModel):
    feature: str
    coefficient: float
    p_value: float

class RegressionCoefficients(BaseModel):
    coefficients: List[Coefficient]