from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
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
    year_from: int = Field(..., ge=1985, le=datetime.now(timezone.utc).year)
    year_to: int = Field(..., ge=1985, le=datetime.now(timezone.utc).year)
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


class ScrapeResultSummary(BaseModel):
    total_marketplaces_processed: int
    successful_scrapes: int
    failed_scrapes: int
    total_cars_scraped: int


class ScrapingResults(BaseModel):
    scrape_request_id: int
    brand_searched: str
    model_searched: str
    year_from_searched: int
    year_to_searched: int
    results: List[ScrapingResultSuccess | ScrapingResultError]
    summary: ScrapeResultSummary


class ScrapingResultsByCarModels(BaseModel):
    car_ids: List[int]
    results: List[ScrapingResultSuccess | ScrapingResultError]
    summary: ScrapeResultSummary


class ScrapedCarQuery(BaseModel):
    id: int | None = None
    car_id: int | None = None
    request_id: int | None = None
    car_platform_id: int | None = None
    date_of_scrape_from: datetime | None = Field(default=None, description="Date must be before date_of_scrape_to")
    date_of_scrape_to: datetime | None = Field(default=None, description="Date must be after date_of_scrape_from")
    name_of_scrape_query: str | None = Field(default=None, max_length=100, min_length=3)


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
