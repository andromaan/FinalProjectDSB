from models.base import Base
from models.car import Car
from models.car_platform import CarPlatform
from models.scraped_car import ScrapedCar
from models.scrape_request import ScrapeRequest
from .regression_model import RegressionModel

__all__ = [
    "Base",
    "Car",
    "CarPlatform",
    "ScrapedCar",
    "ScrapeRequest",
    "RegressionModel",
]
