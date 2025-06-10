from datetime import datetime
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import mapped_column, Mapped
from models.base import Base

class CarPlatform(Base):
    __tablename__ = "car_platforms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    base_search_url: Mapped[str] = mapped_column(String)

    # Selectors for the car platform for playwright scraping
    brand_selector: Mapped[str] = mapped_column(String)
    brand_item_selector: Mapped[str] = mapped_column(String, nullable=True)

    model_selector: Mapped[str] = mapped_column(String)
    model_item_selector: Mapped[str] = mapped_column(String, nullable=True)

    year_from_selector: Mapped[str] = mapped_column(String)
    year_from_item_selector: Mapped[str] = mapped_column(String, nullable=True)

    year_to_selector: Mapped[str] = mapped_column(String)
    year_to_item_selector: Mapped[str] = mapped_column(String, nullable=True)

    button_selector: Mapped[str] = mapped_column(String, nullable=True)

    car_list_selector: Mapped[str] = mapped_column(String)
    url_to_details: Mapped[str] = mapped_column(String)

    close_selector: Mapped[str] = mapped_column(String, nullable=True)

    # Selectors for the scraped car details for BeautifulSoup scraping
    year_bs4_selector: Mapped[str] = mapped_column(String)
    price_bs4_selector: Mapped[str] = mapped_column(String)
    mileage_bs4_selector: Mapped[str] = mapped_column(String)
    views_bs4_selector: Mapped[str] = mapped_column(String)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
