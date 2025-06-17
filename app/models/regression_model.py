from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Float, JSON
from sqlalchemy.orm import mapped_column, Mapped
from models.base import Base


class RegressionModel(Base):
    __tablename__ = "regression_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    target_variable: Mapped[str] = mapped_column(String, nullable=False)
    feature_variables: Mapped[dict] = mapped_column(
        JSON, nullable=False
    )  # список фіч у форматі JSON
    coefficients_json: Mapped[dict] = mapped_column(
        JSON, nullable=False
    )  # параметри моделі у форматі JSON
    intercept: Mapped[float] = mapped_column(Float, nullable=False)
    r_squared: Mapped[float] = mapped_column(Float, nullable=True)
    adj_r_squared: Mapped[float] = mapped_column(Float, nullable=True)
    f_statistic: Mapped[float] = mapped_column(Float, nullable=True)
    f_p_value: Mapped[float] = mapped_column(Float, nullable=True)
    n_observations: Mapped[int] = mapped_column(Integer, nullable=True)
    filters: Mapped[dict] = mapped_column(
        JSON, nullable=False
    )  # ScrapedCarQuery у форматі JSON
    formula: Mapped[str] = mapped_column(String, nullable=False)
    last_trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
