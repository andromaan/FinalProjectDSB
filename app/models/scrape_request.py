from datetime import datetime
from sqlalchemy import Integer, DateTime, ForeignKey, String
from sqlalchemy.orm import mapped_column, Mapped
from models.base import Base
from sqlalchemy.sql import func


class ScrapeRequest(Base):
    __tablename__ = "scrape_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    car_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cars.id", ondelete="CASCADE"), nullable=True
    )
    search_query: Mapped[str] = mapped_column(String, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
