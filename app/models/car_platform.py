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
    brand_selector: Mapped[str] = mapped_column(String)
    model_selector: Mapped[str] = mapped_column(String)
    year_from_selector: Mapped[str] = mapped_column(String)
    year_to_selector: Mapped[str] = mapped_column(String)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
