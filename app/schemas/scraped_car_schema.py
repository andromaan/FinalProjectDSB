from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum


class ScrapingStatus(str, Enum):
    SUCCESS = "success"
    NOT_FOUND = "not_found"
    INVALID_SELECTOR = "invalid_selector"
    SITE_UNAVAILABLE = "site_unavailable"
    ERROR_SCRAPING = "error_scraping"


class ScrapedCarCreate(BaseModel):
    request_id: int
    car_platform_id: int
    car_id: Optional[int] = None
    scraped_url: Optional[str] = None
    search_position: Optional[int] = None
    scraped_year: Optional[int] = None
    scraped_price: Optional[int] = None
    scraped_currency: Optional[str] = None
    scraped_mileage: Optional[int] = None
    scraped_mileage_unit: Optional[str] = None
    scraped_number_of_views: Optional[int] = None
    scraped_at: Optional[datetime] = None
    status: ScrapingStatus
    error_message: Optional[str]


class ScrapingConfigByQuery(BaseModel):
    brand: str
    model: str
    year_from: str
    year_to: str
    car_platform_ids: List[int]


class ScrapingConfigByCarModel(BaseModel):
    car_id: int
    car_platform_ids: List[int]


class ScrapingConfigByCarsModel(BaseModel):
    car_ids: List[int]
    car_platform_ids: List[int]


class ScrapingResultSuccess(BaseModel):
    marketplace_name: str
    status: str = "success"
    cars_scraped: int
    time_to_scrape_platform: str
    car_id: Optional[int] = None
    scraped_at: datetime


class ScrapingResultError(BaseModel):
    marketplace_name: str
    status: str
    error_message: str
    car_id: Optional[int] = None
    scraped_at: datetime


class Summary(BaseModel):
    total_marketplaces_processed: int
    successful_scrapes: int
    failed_scrapes: int


class ScrapingResults(BaseModel):
    scrape_request_id: int
    brand_searched: str
    model_searched: str
    year_from_searched: str
    year_to_searched: str
    results: List[ScrapingResultSuccess | ScrapingResultError]
    summary: Summary

class ScrapingResultsByCarModels(BaseModel):
    car_ids: List[int]
    results: List[ScrapingResultSuccess | ScrapingResultError]
    summary: Summary


class ScrapedRequestCreate(BaseModel):
    car_id: Optional[int] = None
    search_query: Optional[str] = None


class ScrapedRequestResponse(BaseModel):
    id: int
    car_platform_id: int
    car_id: Optional[int] = None
    request_id: int
    scraped_url: Optional[str] = None
    search_position: Optional[int] = None
    scraped_year: Optional[int] = None
    scraped_price: Optional[int] = None
    scraped_currency: Optional[str] = None
    scraped_mileage: Optional[int] = None
    scraped_mileage_unit: Optional[str] = None
    scraped_number_of_views: Optional[int] = None
    status: str
    error_message: Optional[str] = None
    scraped_at: datetime


class ScrapeRequestResponse(BaseModel):
    id: int
    car_id: Optional[int] = None
    search_query: Optional[str] = None
    requested_at: datetime

    class Config:
        from_attributes = True


class ScrapedCarItem(BaseModel):
    url: str
    year: Optional[int] = None
    price: Optional[int] = None
    currency: Optional[str] = None
    mileage: Optional[int] = None
    mileage_unit: Optional[str] = None
    views: Optional[int] = None
    scraped_at: Optional[datetime] = None
