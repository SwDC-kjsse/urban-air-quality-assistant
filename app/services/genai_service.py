"""Google Gemini GenAI integration with deterministic offline fallback."""
import httpx

from app.config import settings
from app.models.schemas import ActionItem, AirQualitySnapshot, HouseholdProfile, ImpactSummary


async def _call_gemini(prompt: str) -> str | None:
    """Invoke Gemini generateContent REST API if an API key is configured."""
    api_key = settings.gemini_api_key
    if not api_key:
        return None

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 450},
    }
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_s) as client:
            resp = await client.post(
                url,
                headers={"Content-Type": "application/json", "X-goog-api-key": api_key},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates") or []
            if candidates:
                parts = candidates[0].get("content", {}).get("parts") or []
                text = "".join(p.get("text", "") for p in parts).strip()
                if text:
                    return text
    except (httpx.HTTPError, ValueError, KeyError):
        return None
    return None


def _offline_narrative(
    profile: HouseholdProfile,
    aq: AirQualitySnapshot,
    actions: list[ActionItem],
    impact: ImpactSummary,
) -> str:
    """Generate a structured, empathetic advisory when Gemini key is absent."""
    vulnerabilities = []
    if profile.has_children:
        vulnerabilities.append("children")
    if profile.has_elderly:
        vulnerabilities.append("elderly members")
    if profile.has_respiratory_condition:
        vulnerabilities.append("respiratory sensitivity")
    vuln_phrase = ", ".join(vulnerabilities) if vulnerabilities else "your household"

    top_titles = "; ".join(a.title for a in actions[:3])
    return (
        f"In {aq.city}, current air quality is {aq.severity_tier} (US AQI {aq.aqi_us}, PM2.5 {aq.pm25_ug_m3} µg/m³). "
        f"For {vuln_phrase} in a {profile.home_type.replace('_', ' ')}, your highest-leverage moves today are: "
        f"{top_titles}. Together, these habits cut household PM2.5 exposure by {impact.total_pm25_exposure_drop_pct}%, "
        f"lower your risk score from {impact.baseline_risk_score} to {impact.projected_risk_score}/100, and prevent "
        f"{impact.weekly_co2_saved_kg} kg of CO₂e emissions every week ({impact.equivalent_trees_planted} trees/year equivalent)."
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
        "navigate winter smog. Summarize a practical 3-sentence action plan tailored to their context "
        "and clearly explain the direct health + emissions impact of their choices. Keep under 130 words.\n\n"
        f"Location: {aq.city}, {aq.country} | AQI: {aq.aqi_us} ({aq.severity_tier}) | PM2.5: {aq.pm25_ug_m3} µg/m³\n"
        f"Household: size {profile.household_size}, children={profile.has_children}, elderly={profile.has_elderly}, "
        f"respiratory={profile.has_respiratory_condition}, commute={profile.commute_mode} ({profile.commute_km_per_day} km/day), "
        f"cooking={profile.cooking_fuel}, budget={profile.budget_tier}\n"
        f"Quantified Impact: PM2.5 drop {impact.total_pm25_exposure_drop_pct}%, "
        f"risk {impact.baseline_risk_score}->{impact.projected_risk_score}/100, "
        f"CO2 saved {impact.weekly_co2_saved_kg} kg/week.\n"
        f"Actions:\n{action_lines}"
    )
    ai_text = await _call_gemini(prompt)
    if ai_text:
        return ai_text, f"Google Gemini ({settings.gemini_model})"
    return _offline_narrative(profile, aq, actions, impact), "Context-Engine Fallback (Add GEMINI_API_KEY for live LLM)"


async def answer_followup(
    profile: HouseholdProfile,
    aq: AirQualitySnapshot,
    question: str,
) -> tuple[str, str]:
    """Answer a follow-up question grounded in live AQI and household context."""
    prompt = (
        "You are an Urban Air Quality Assistant. Answer the user's question concisely (max 120 words) "
        "with practical, low-emission steps and explain the direct impact on PM2.5 exposure or emissions.\n\n"
        f"Context: {aq.city} AQI {aq.aqi_us} ({aq.severity_tier}), PM2.5 {aq.pm25_ug_m3} µg/m³, "
        f"best ventilation window: {aq.best_ventilation_window}. "
        f"Household size {profile.household_size}, children={profile.has_children}, "
        f"elderly={profile.has_elderly}, respiratory={profile.has_respiratory_condition}, "
        f"commute={profile.commute_mode}, budget={profile.budget_tier}.\n"
        f"User question: {question}"
    )
    ai_text = await _call_gemini(prompt)
    if ai_text:
        return ai_text, f"Google Gemini ({settings.gemini_model})"

    q_low = question.lower()
    if any(w in q_low for w in ("window", "open", "ventilat", "air out")):
        ans = (
            f"At {aq.city}'s AQI {aq.aqi_us} ({aq.severity_tier}), your safest ventilation window is: "
            f"{aq.best_ventilation_window}. Outside that window, keep windows latched and wet-mop floors "
            "so fine PM2.5 stays outside—reducing indoor particulate buildup by ~24%."
        )
    elif any(w in q_low for w in ("school", "kid", "child", "walk", "run", "exercise", "outdoor")):
        ans = (
            f"With AQI at {aq.aqi_us} (PM2.5 {aq.pm25_ug_m3} µg/m³), avoid vigorous outdoor exercise in the "
            "early morning or evening inversion. Move outdoor play/errands to 13:00–15:30, use tree-lined "
            "side streets, and wear an N95/FFP2 mask if AQI > 150 to cut inhaled PM2.5 by >80%."
        )
    elif any(w in q_low for w in ("purifier", "filter", "fan", "indoors", "cook")):
        ans = (
            "For indoor air quality: run a True HEPA or DIY MERV-13 Corsi-Rosenthal box-fan filter in the "
            "main bedroom (cuts indoor PM2.5 by 48–60%), keep pot lids on while cooking, and run the kitchen "
            "exhaust for 15 minutes afterward to prevent indoor ultrafine particle spikes."
        )
    else:
        ans = (
            f"Based on {aq.city}'s AQI {aq.aqi_us} ({aq.severity_tier}), prioritize: (1) keeping windows closed "
            f"outside {aq.best_ventilation_window}, (2) running indoor filtration or wet-mopping, and (3) swapping "
            "car/two-wheeler trips for transit or carpools—cutting personal PM2.5 exposure and local tailpipe emissions."
        )
    return ans, "Context-Engine Fallback (Add GEMINI_API_KEY for live LLM)"
