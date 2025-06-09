from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped
from models.base import Base
from sqlalchemy.sql import func

class ScrapedCar(Base):
    __tablename__ = "scraped_cars"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    car_platform_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('car_platforms.id'), ondelete="CASCADE"
    )
    car_id: Mapped[int] = mapped_column(
        ForeignKey("cars.id", ondelete="CASCADE", nullable=True)
    )

    scraped_year: Mapped[int] = mapped_column(Integer)
    scraped_currency: Mapped[str] = mapped_column(String(3), nullable=True)
    scraped_price: Mapped[str] = mapped_column(String, nullable=True)
    scraped_url: Mapped[str] = mapped_column(String, nullable=True)
    scraped_mileage: Mapped[str] = mapped_column(String, nullable=True)
    scraped_number_of_views: Mapped[int] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(String)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    scraped_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())