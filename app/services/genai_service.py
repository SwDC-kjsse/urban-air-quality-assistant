"""Google Gemini GenAI integration with deterministic offline fallback."""

import logging

import httpx

from app.config import settings
from app.models.schemas import (
    ActionItem,
    AirQualitySnapshot,
    HouseholdProfile,
    ImpactSummary,
)

logger = logging.getLogger(__name__)

_FALLBACK_PROVIDER = "Context-Engine Fallback (Add GEMINI_API_KEY for live LLM)"

_FOLLOWUP_TOPICS: tuple[tuple[tuple[str, ...], str], ...] = (
    (
        ("purifier", "filter", "fan", "indoors", "cook"),
        "For indoor air quality: run a True HEPA or DIY MERV-13 Corsi-Rosenthal box-fan "
        "filter in the main bedroom (cuts indoor PM2.5 by 48–60%), keep pot lids on while "
        "cooking, and run the kitchen exhaust for 15 minutes afterward.",
    ),
    (
        ("window", "open", "ventilat", "air out"),
        "At {city}'s AQI {aqi} ({tier}), your safest ventilation window is: {window}. "
        "Outside that window, keep windows latched and wet-mop floors so fine PM2.5 "
        "stays outside—reducing indoor particulate buildup by ~24%.",
    ),
    (
        ("school", "kid", "child", "walk", "jog", "exercise", "outdoor"),
        "With AQI at {aqi} (PM2.5 {pm25} µg/m³), avoid vigorous outdoor exercise during "
        "morning/evening inversions. Move errands to 13:00–15:30, use tree-lined side "
        "streets, and wear an N95/FFP2 mask if AQI > 150 to cut inhaled PM2.5 by >80%.",
    ),
)


async def _call_gemini(prompt: str) -> tuple[str, str] | None:
    """Invoke Gemini generateContent REST API if an API key is configured."""
    api_key = settings.gemini_api_key
    if not api_key:
        return None

    models = list(
        dict.fromkeys(
            [
                settings.gemini_model,
                "gemini-flash-lite-latest",
                "gemini-3.1-flash-lite",
                "gemini-3-flash-preview",
            ]
        )
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 450},
    }
    transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0")
    try:
        async with httpx.AsyncClient(
            transport=transport,
            timeout=settings.request_timeout_s,
        ) as client:
            for model in models:
                url = (
                    "https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{model}:generateContent"
                )
                resp = await client.post(
                    url,
                    headers={"Content-Type": "application/json", "X-goog-api-key": api_key},
                    json=payload,
                )
                if resp.status_code in (404, 429, 503):
                    continue
                resp.raise_for_status()
                data = resp.json()
                candidates = data.get("candidates") or []
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts") or []
                    text = "".join(p.get("text", "") for p in parts).strip()
                    if text:
                        return text, model
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        logger.debug("Gemini API request failed, using fallback: %s", exc)
        return None
    return None


def _offline_narrative(
    profile: HouseholdProfile,
    aq: AirQualitySnapshot,
    actions: list[ActionItem],
    impact: ImpactSummary,
) -> str:
    """Generate a structured, empathetic advisory when Gemini key is absent."""
    vulnerabilities: list[str] = []
    if profile.has_children:
        vulnerabilities.append("children")
    if profile.has_elderly:
        vulnerabilities.append("elderly members")
    if profile.has_respiratory_condition:
        vulnerabilities.append("respiratory sensitivity")
    vuln_phrase = ", ".join(vulnerabilities) if vulnerabilities else "your household"

    top_titles = "; ".join(a.title for a in actions[:3])
    home_label = profile.home_type.replace("_", " ")
    return (
        f"In {aq.city}, current air quality is {aq.severity_tier} "
        f"(US AQI {aq.aqi_us}, PM2.5 {aq.pm25_ug_m3} µg/m³). "
        f"For {vuln_phrase} in a {home_label}, your highest-leverage moves today are: "
        f"{top_titles}. Together, these habits cut household PM2.5 exposure by "
        f"{impact.total_pm25_exposure_drop_pct}%, lower your risk score from "
        f"{impact.baseline_risk_score} to {impact.projected_risk_score}/100, and prevent "
        f"{impact.weekly_co2_saved_kg} kg of CO₂e emissions every week "
        f"({impact.equivalent_trees_planted} trees/year equivalent)."
    )


def _offline_followup(aq: AirQualitySnapshot, question: str) -> str:
    """Return a deterministic context-grounded reply when Gemini is unavailable."""
    q_low = question.lower()
    ctx = {
        "city": aq.city,
        "aqi": aq.aqi_us,
        "tier": aq.severity_tier,
        "pm25": aq.pm25_ug_m3,
        "window": aq.best_ventilation_window,
    }
    for keywords, template in _FOLLOWUP_TOPICS:
        if any(word in q_low for word in keywords):
            return template.format(**ctx)
    return (
        f"Based on {aq.city}'s AQI {aq.aqi_us} ({aq.severity_tier}), prioritize: "
        f"(1) keeping windows closed outside {aq.best_ventilation_window}, "
        "(2) running indoor filtration or wet-mopping, and (3) swapping car/two-wheeler "
        "trips for transit or carpools—cutting personal PM2.5 and tailpipe emissions."
    )


async def generate_plan_narrative(
    profile: HouseholdProfile,
    aq: AirQualitySnapshot,
    actions: list[ActionItem],
    impact: ImpactSummary,
) -> tuple[str, str]:
    """Return (narrative_text, provider_name) using Gemini or offline fallback."""
    action_lines = "\n".join(f"- {a.title}: {a.direct_impact}" for a in actions)
    prompt = (
        "You are an empathetic, science-grounded Urban Air Quality Assistant helping a family "
        "navigate winter smog. Summarize a practical 3-sentence action plan tailored to their "
        "context and clearly explain the direct health + emissions impact. Under 130 words.\n\n"
        f"Location: {aq.city}, {aq.country} | AQI: {aq.aqi_us} ({aq.severity_tier}) "
        f"| PM2.5: {aq.pm25_ug_m3} µg/m³\n"
        f"Household: size {profile.household_size}, children={profile.has_children}, "
        f"elderly={profile.has_elderly}, respiratory={profile.has_respiratory_condition}, "
        f"commute={profile.commute_mode} ({profile.commute_km_per_day} km/day), "
        f"cooking={profile.cooking_fuel}, budget={profile.budget_tier}\n"
        f"Quantified Impact: PM2.5 drop {impact.total_pm25_exposure_drop_pct}%, "
        f"risk {impact.baseline_risk_score}->{impact.projected_risk_score}/100, "
        f"CO2 saved {impact.weekly_co2_saved_kg} kg/week.\n"
        f"Actions:\n{action_lines}"
    )
    result = await _call_gemini(prompt)
    if result:
        ai_text, used_model = result
        return ai_text, f"Google Gemini ({used_model})"
    return _offline_narrative(profile, aq, actions, impact), _FALLBACK_PROVIDER


async def answer_followup(
    profile: HouseholdProfile,
    aq: AirQualitySnapshot,
    question: str,
) -> tuple[str, str]:
    """Answer a follow-up question grounded in live AQI and household context."""
    prompt = (
        "You are an Urban Air Quality Assistant. Answer concisely (max 120 words) "
        "with practical, low-emission steps and explain the direct PM2.5 or CO2 impact.\n\n"
        f"Context: {aq.city} AQI {aq.aqi_us} ({aq.severity_tier}), PM2.5 {aq.pm25_ug_m3} µg/m³, "
        f"best ventilation window: {aq.best_ventilation_window}. "
        f"Household size {profile.household_size}, children={profile.has_children}, "
        f"elderly={profile.has_elderly}, respiratory={profile.has_respiratory_condition}, "
        f"commute={profile.commute_mode}, budget={profile.budget_tier}.\n"
        f"User question: {question}"
    )
    result = await _call_gemini(prompt)
    if result:
        ai_text, used_model = result
        return ai_text, f"Google Gemini ({used_model})"
    return _offline_followup(aq, question), _FALLBACK_PROVIDER
