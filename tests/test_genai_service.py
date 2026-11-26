"""Unit tests for GenAI service offline fallback and topic routing."""

import asyncio

from app.models.schemas import AirQualitySnapshot, HouseholdProfile
from app.services import genai_service
from app.services.context_engine import (
    compute_baseline_risk,
    compute_impact_summary,
    generate_tailored_actions,
)


def _sample_aq() -> AirQualitySnapshot:
    return AirQualitySnapshot(
        city="Delhi",
        country="India",
        aqi_us=260,
        pm25_ug_m3=143.0,
        pm10_ug_m3=205.0,
        no2_ug_m3=60.0,
        severity_tier="Very Unhealthy",
        best_ventilation_window="Keep sealed; use filtered recirculation",
        source="Test",
    )


def test_generate_plan_narrative_offline_fallback(monkeypatch):
    async def _no_llm(_prompt: str):
        return None

    monkeypatch.setattr(genai_service, "_call_gemini", _no_llm)
    profile = HouseholdProfile(city="Delhi", has_children=True, has_elderly=True)
    aq = _sample_aq()
    base, _, _ = compute_baseline_risk(profile, aq)
    actions = generate_tailored_actions(profile, aq)
    impact = compute_impact_summary(base, actions)

    text, provider = asyncio.run(
        genai_service.generate_plan_narrative(profile, aq, actions, impact)
    )
    assert "Fallback" in provider
    assert "Delhi" in text
    assert str(impact.total_pm25_exposure_drop_pct) in text


def test_answer_followup_offline_topics(monkeypatch):
    async def _no_llm(_prompt: str):
        return None

    monkeypatch.setattr(genai_service, "_call_gemini", _no_llm)
    profile = HouseholdProfile(city="Delhi")
    aq = _sample_aq()

    for question, expected_word in [
        ("When should I open windows?", "ventilation"),
        ("Can kids walk to school?", "N95"),
        ("Should I run an air purifier?", "HEPA"),
        ("What general steps help today?", "Delhi"),
    ]:
        ans, provider = asyncio.run(genai_service.answer_followup(profile, aq, question))
        assert "Fallback" in provider
        assert expected_word.lower() in ans.lower()
