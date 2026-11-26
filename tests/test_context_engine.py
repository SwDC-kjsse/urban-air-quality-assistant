"""Unit tests for the deterministic context engine and impact quantification."""
from app.models.schemas import AirQualitySnapshot, HouseholdProfile
from app.services.air_quality import classify_aqi
from app.services.context_engine import (
    compute_baseline_risk,
    compute_impact_summary,
    generate_tailored_actions,
)


def _sample_aq(aqi: int = 280) -> AirQualitySnapshot:
    sev, win = classify_aqi(aqi)
    return AirQualitySnapshot(
        city="Delhi",
        country="India",
        aqi_us=aqi,
        pm25_ug_m3=154.0,
        pm10_ug_m3=220.0,
        no2_ug_m3=65.0,
        severity_tier=sev,
        best_ventilation_window=win,
        source="Test",
    )


def test_classify_aqi_tiers():
    assert classify_aqi(40)[0] == "Good"
    assert classify_aqi(85)[0] == "Moderate"
    assert classify_aqi(130)[0] == "Unhealthy for Sensitive Groups"
    assert classify_aqi(180)[0] == "Unhealthy"
    assert classify_aqi(260)[0] == "Very Unhealthy"
    assert classify_aqi(350)[0].startswith("Hazardous")


def test_vulnerability_increases_risk_score():
    aq = _sample_aq(240)
    low_vuln = HouseholdProfile(
        city="Delhi",
        has_children=False,
        has_elderly=False,
        has_respiratory_condition=False,
    )
    high_vuln = HouseholdProfile(
        city="Delhi",
        has_children=True,
        has_elderly=True,
        has_respiratory_condition=True,
    )

    s_low, _, _ = compute_baseline_risk(low_vuln, aq)
    s_high, level_high, _ = compute_baseline_risk(high_vuln, aq)
    assert s_high > s_low
    assert level_high in ("High", "Critical")


def test_budget_tier_tailors_indoor_hack():
    aq = _sample_aq(260)
    zero_p = HouseholdProfile(city="Delhi", budget_tier="zero_cost")
    low_p = HouseholdProfile(city="Delhi", budget_tier="low_budget")
    mod_p = HouseholdProfile(city="Delhi", budget_tier="moderate")

    zero_titles = [a.title for a in generate_tailored_actions(zero_p, aq)]
    low_titles = [a.title for a in generate_tailored_actions(low_p, aq)]
    mod_titles = [a.title for a in generate_tailored_actions(mod_p, aq)]

    assert any("Wet-Mop" in t for t in zero_titles)
    assert any("Corsi-Rosenthal" in t for t in low_titles)
    assert any("True HEPA H13" in t for t in mod_titles)


def test_impact_summary_reduces_risk_and_computes_co2():
    aq = _sample_aq(300)
    profile = HouseholdProfile(city="Delhi", commute_mode="car", commute_km_per_day=20.0)
    base_score, _, _ = compute_baseline_risk(profile, aq)
    actions = generate_tailored_actions(profile, aq)
    impact = compute_impact_summary(base_score, actions)

    assert impact.projected_risk_score < impact.baseline_risk_score
    assert 10 <= impact.total_pm25_exposure_drop_pct <= 85
    assert impact.weekly_co2_saved_kg > 0
    assert impact.annual_co2_saved_kg == round(impact.weekly_co2_saved_kg * 52.0, 1)
