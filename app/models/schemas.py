"""Pydantic schemas for requests, air quality snapshots, and AI action plans."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

CommuteMode = Literal["car", "two_wheeler", "public_transit", "walk_cycle", "remote"]
HomeType = Literal["apartment", "independent_house", "shared_housing"]
BudgetTier = Literal["zero_cost", "low_budget", "moderate"]
CookingFuel = Literal["lpg_gas", "electric_induction", "biomass_solid"]


class HouseholdProfile(BaseModel):
    """User context describing location, household vulnerabilities, and lifestyle."""

    city: str = Field(..., min_length=2, max_length=80, description="City or neighborhood name")
    household_size: int = Field(default=3, ge=1, le=15)
    has_children: bool = Field(default=False)
    has_elderly: bool = Field(default=False)
    has_respiratory_condition: bool = Field(default=False)
    commute_mode: CommuteMode = Field(default="car")
    commute_km_per_day: float = Field(default=14.0, ge=0.0, le=150.0)
    home_type: HomeType = Field(default="apartment")
    cooking_fuel: CookingFuel = Field(default="lpg_gas")
    budget_tier: BudgetTier = Field(default="low_budget")
    manual_aqi_override: int | None = Field(default=None, ge=10, le=500)

    @field_validator("city")
    @classmethod
    def clean_city(cls, value: str) -> str:
        cleaned = " ".join(value.strip().split())
        if not cleaned or not any(ch.isalpha() for ch in cleaned):
            raise ValueError("City name must contain alphabetic characters.")
        return cleaned


class AirQualitySnapshot(BaseModel):
    """Normalized air quality reading for a location."""

    city: str
    country: str
    aqi_us: int = Field(..., ge=0, le=500)
    pm25_ug_m3: float = Field(..., ge=0.0)
    pm10_ug_m3: float = Field(..., ge=0.0)
    no2_ug_m3: float = Field(..., ge=0.0)
    severity_tier: str
    best_ventilation_window: str
    source: str


class ActionItem(BaseModel):
    """Single tailored recommendation with quantified direct impact."""

    category: Literal["daily_routine", "indoor_hack", "sustainable_alt"]
    title: str
    steps: str
    direct_impact: str
    pm25_reduction_pct: int = Field(..., ge=0, le=90)
    weekly_co2_saved_kg: float = Field(..., ge=0.0)
    cost_level: str


class ImpactSummary(BaseModel):
    """Aggregate quantified impact of adopting the recommended actions."""

    baseline_risk_score: int = Field(..., ge=0, le=100)
    projected_risk_score: int = Field(..., ge=0, le=100)
    total_pm25_exposure_drop_pct: int = Field(..., ge=0, le=90)
    weekly_co2_saved_kg: float = Field(..., ge=0.0)
    annual_co2_saved_kg: float = Field(..., ge=0.0)
    equivalent_trees_planted: float = Field(..., ge=0.0)


class PlanResponse(BaseModel):
    """Complete tailored advisory response returned to the client."""

    air_quality: AirQualitySnapshot
    risk_level: str
    risk_explanation: str
    ai_narrative: str
    ai_provider: str
    actions: list[ActionItem]
    impact: ImpactSummary


class ChatRequest(BaseModel):
    """Follow-up conversational question grounded in the user's household context."""

    profile: HouseholdProfile
    question: str = Field(..., min_length=3, max_length=500)

    @field_validator("question")
    @classmethod
    def clean_question(cls, value: str) -> str:
        cleaned = " ".join(value.strip().split())
        if len(cleaned) < 3:
            raise ValueError("Question must be at least 3 characters.")
        return cleaned


class ChatResponse(BaseModel):
    """Conversational answer with provider attribution."""

    answer: str
    ai_provider: str
    air_quality: AirQualitySnapshot
