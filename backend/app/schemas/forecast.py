from datetime import date

from pydantic import BaseModel, Field

from app.schemas.geo import PanchayatOut

Probability = Field(ge=0.0, le=1.0)


class RainfallQuantiles(BaseModel):
    """Weekly accumulated rainfall (mm) across ensemble members."""

    p10: float = Field(ge=0.0)
    p50: float = Field(ge=0.0)
    p90: float = Field(ge=0.0)


class WeeklyForecast(BaseModel):
    week: int = Field(ge=1, le=4)
    lead_days_start: int = Field(description="Days after issue date, inclusive")
    lead_days_end: int
    start_date: date
    end_date: date
    rainfall_mm: RainfallQuantiles
    dry_spell_probability: float = Probability
    heavy_rain_probability: float = Probability


class ForecastDefinitions(BaseModel):
    """Thresholds behind the probabilities, so the UI can explain them."""

    dry_day_threshold_mm: float = Field(description="A day below this is a dry day (IMD rainy-day threshold)")
    dry_spell_min_days: int = Field(description="Consecutive dry days within the week that count as a dry spell")
    heavy_rain_threshold_mm: float = Field(description="A day at or above this is heavy rain (IMD)")


class ForecastResponse(BaseModel):
    panchayat: PanchayatOut
    issued_on: date
    model: str
    ensemble_members: int
    synthetic: bool = Field(default=True, description="True while forecasts are mocked")
    definitions: ForecastDefinitions
    weeks: list[WeeklyForecast] = Field(min_length=4, max_length=4)
