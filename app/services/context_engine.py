"""Deterministic decision engine for household risk scoring, tailored actions, and impact math."""

from app.models.schemas import (
    ActionItem,
    AirQualitySnapshot,
    HouseholdProfile,
    ImpactSummary,
)

# Emission factors in kg CO2e per passenger-km
_COMMUTE_CO2_KG_PER_KM: dict[str, float] = {
    "car": 0.192,
    "two_wheeler": 0.084,
    "public_transit": 0.041,
    "walk_cycle": 0.0,
    "remote": 0.0,
}

_RISK_BANDS: tuple[tuple[int, str], ...] = (
    (75, "Critical"),
    (55, "High"),
    (35, "Elevated"),
)

_INDOOR_HACK_BY_BUDGET: dict[str, tuple[str, str, str, int, str]] = {
    "zero_cost": (
        "Wet-Mop & Inversion-Timed Draft Sealing",
        "Seal door/window gaps with rolled towels during peak smog; wet-mop floors instead of "
        "dry sweeping; ventilate only during: {window}.",
        "Prevents outdoor PM2.5 infiltration and stops settled dust resuspension (-24% PM2.5).",
        24,
        "Zero cost",
    ),
    "low_budget": (
        "DIY Corsi-Rosenthal Box Fan Filter",
        "Tape MERV-13 furnace filters to a standard box fan in the main living/bedroom area; "
        "run on medium during high-smog hours and air out only at {window}.",
        "Captures up to 48% of indoor PM2.5 & smoke particles at ~1/4 commercial purifier cost.",
        48,
        "Low budget (~$25–$35)",
    ),
    "moderate": (
        "True HEPA H13 Bedroom Clean-Air Zone",
        "Place a True HEPA H13 purifier (sized to 4+ ACH) in the primary sleeping room, "
        "pair with a PM2.5 sensor, and keep doors closed overnight.",
        "Delivers ~60% indoor PM2.5 reduction overnight for deeper respiratory recovery.",
        60,
        "Moderate budget",
    ),
}


def compute_baseline_risk(
    profile: HouseholdProfile,
    aq: AirQualitySnapshot,
) -> tuple[int, str, str]:
    """Compute 0-100 baseline health risk score, tier label, and human-readable explanation."""
    aqi_component = min(65.0, (aq.aqi_us / 350.0) * 65.0)
    checks: tuple[tuple[bool, float, str], ...] = (
        (profile.has_children, 10.0, "children in household"),
        (profile.has_elderly, 10.0, "elderly family members"),
        (profile.has_respiratory_condition, 12.0, "asthma/respiratory sensitivity"),
        (profile.cooking_fuel == "biomass_solid", 8.0, "solid-fuel indoor cooking"),
    )
    vuln_points = sum(pts for cond, pts, _ in checks if cond)
    factors = [label for cond, _, label in checks if cond]

    score = max(5, min(100, int(round(aqi_component + vuln_points))))
    level = next((lbl for thresh, lbl in _RISK_BANDS if score >= thresh), "Manageable")
    vuln_text = ", ".join(factors) if factors else "general urban exposure"
    explanation = (
        f"Risk score {score}/100 ({level}) driven by {aq.city} AQI {aq.aqi_us} "
        f"(PM2.5: {aq.pm25_ug_m3} µg/m³) combined with {vuln_text}."
    )
    return score, level, explanation


def _build_routine_actions(
    profile: HouseholdProfile,
    aq: AirQualitySnapshot,
) -> list[ActionItem]:
    """Build daily routine actions for inversion avoidance and low-emission commuting."""
    outdoor_msg = (
        "Shift outdoor exercise, school pickups, and errands to 13:00–15:30 when winter "
        "inversion lifts; wear a well-fitted N95/FFP2 mask when AQI exceeds 150."
        if aq.aqi_us > 150
        else "Schedule walks and errands between 11:00–16:00 away from arterial traffic corridors."
    )
    schedule_action = ActionItem(
        category="daily_routine",
        title="Inversion-Aware Daily Schedule",
        steps=outdoor_msg,
        direct_impact=(
            "Cuts peak morning/evening fine-particulate inhalation by ~28% during inversions."
        ),
        pm25_reduction_pct=28,
        weekly_co2_saved_kg=0.0,
        cost_level="Zero cost",
    )

    daily_km = profile.commute_km_per_day
    if profile.commute_mode in ("car", "two_wheeler") and daily_km > 0:
        cur_factor = _COMMUTE_CO2_KG_PER_KM[profile.commute_mode]
        saved_per_day = max(0.0, (cur_factor - _COMMUTE_CO2_KG_PER_KM["public_transit"]) * daily_km)
        weekly_saved = round(saved_per_day * 3.0, 1)
        mode_name = profile.commute_mode.replace("_", " ")
        commute_action = ActionItem(
            category="daily_routine",
            title="3-Day Low-Emission Commute Swap",
            steps=(
                f"Shift 3 days/week of your {daily_km:.0f} km {mode_name} commute to metro/bus "
                "or neighborhood carpool, and eliminate 5-minute cold-start idling."
            ),
            direct_impact=(
                f"Avoids {weekly_saved:.1f} kg CO₂e/week and reduces street-level NOx & PM2.5."
            ),
            pm25_reduction_pct=12,
            weekly_co2_saved_kg=weekly_saved,
            cost_level="Saves fuel money",
        )
    else:
        commute_action = ActionItem(
            category="daily_routine",
            title="Green-Corridor Micro-Mobility",
            steps=(
                "Keep using zero/low-emission transit, and select tree-lined side streets 1–2 "
                "blocks off main roads to halve roadside black-carbon exposure."
            ),
            direct_impact=(
                "Maintains ~1.8 kg CO₂e/week savings vs car trips while cutting roadside PM2.5."
            ),
            pm25_reduction_pct=18,
            weekly_co2_saved_kg=1.8,
            cost_level="Zero cost",
        )

    return [schedule_action, commute_action]


def _build_indoor_actions(
    profile: HouseholdProfile,
    aq: AirQualitySnapshot,
) -> list[ActionItem]:
    """Build indoor air quality hacks matched to budget tier and cooking fuel."""
    title, steps_tpl, impact_txt, pm_cut, cost = _INDOOR_HACK_BY_BUDGET[profile.budget_tier]
    filtration_action = ActionItem(
        category="indoor_hack",
        title=title,
        steps=steps_tpl.format(window=aq.best_ventilation_window),
        direct_impact=impact_txt,
        pm25_reduction_pct=pm_cut,
        weekly_co2_saved_kg=0.0,
        cost_level=cost,
    )

    if profile.cooking_fuel == "biomass_solid":
        kitchen_action = ActionItem(
            category="indoor_hack",
            title="Clean-Cookstove & Cross-Draft Venting",
            steps=(
                "Transition from solid biomass to LPG or electric induction; while transitioning, "
                "always cook with lids on and direct exhaust outdoors."
            ),
            direct_impact="Eliminates up to 55% of indoor PM2.5 spikes and saves ~14.0 kg CO₂e/wk.",
            pm25_reduction_pct=55,
            weekly_co2_saved_kg=14.0,
            cost_level="Low–Moderate",
        )
    else:
        kitchen_action = ActionItem(
            category="indoor_hack",
            title="Kitchen Exhaust + Lid-On Cooking Protocol",
            steps=(
                "Run kitchen exhaust fan 5 minutes before and 15 minutes after frying; "
                "cover pots and avoid indoor incense/candles during winter smog episodes."
            ),
            direct_impact="Cuts cooking-generated ultrafine indoor PM2.5 spikes by ~26%.",
            pm25_reduction_pct=26,
            weekly_co2_saved_kg=0.4,
            cost_level="Zero cost",
        )

    return [filtration_action, kitchen_action]


def _build_sustainable_actions(profile: HouseholdProfile) -> list[ActionItem]:
    """Build community and household sustainability alternatives."""
    return [
        ActionItem(
            category="sustainable_alt",
            title="Zero-Waste Winter Heating & Laundry Routine",
            steps=(
                "Replace open waste/leaf burning with community composting; sun-dry laundry "
                "midday instead of electric dryers and trim heater runtime by 1–2 hours daily."
            ),
            direct_impact="Prevents toxic dioxin/PM10 smoke locally and cuts ~5.2 kg CO₂e/week.",
            pm25_reduction_pct=10,
            weekly_co2_saved_kg=5.2,
            cost_level="Saves utility cost",
        ),
        ActionItem(
            category="sustainable_alt",
            title="School & Neighborhood Carpool Pod",
            steps=(
                f"Coordinate a 3-family school/errand carpool or walking bus for your "
                f"{profile.household_size}-person household, and report illegal trash burning."
            ),
            direct_impact="Removes 2 extra cold-start vehicles per trip (~4.6 kg CO₂e/week saved).",
            pm25_reduction_pct=12,
            weekly_co2_saved_kg=4.6,
            cost_level="Zero cost",
        ),
    ]


def generate_tailored_actions(
    profile: HouseholdProfile,
    aq: AirQualitySnapshot,
) -> list[ActionItem]:
    """Select and parameterize routines, indoor hacks, and sustainable alternatives."""
    return [
        *_build_routine_actions(profile, aq),
        *_build_indoor_actions(profile, aq),
        *_build_sustainable_actions(profile),
    ]


def compute_impact_summary(baseline_risk: int, actions: list[ActionItem]) -> ImpactSummary:
    """Aggregate diminishing-returns PM2.5 exposure reduction and CO2e savings."""
    remaining_exposure = 1.0
    weekly_co2 = 0.0
    for act in actions:
        remaining_exposure *= 1.0 - (act.pm25_reduction_pct / 100.0)
        weekly_co2 += act.weekly_co2_saved_kg

    drop_pct = max(5, min(85, int(round((1.0 - remaining_exposure) * 100))))
    projected_risk = max(5, int(round(baseline_risk * (1.0 - (drop_pct / 120.0)))))
    annual_co2 = round(weekly_co2 * 52.0, 1)
    trees = round(annual_co2 / 21.77, 1)

    return ImpactSummary(
        baseline_risk_score=baseline_risk,
        projected_risk_score=projected_risk,
        total_pm25_exposure_drop_pct=drop_pct,
        weekly_co2_saved_kg=round(weekly_co2, 1),
        annual_co2_saved_kg=annual_co2,
        equivalent_trees_planted=trees,
    )
