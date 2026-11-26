"""Live air quality lookup via Open-Meteo with TTL caching and offline winter-smog fallback."""

import logging
import time

import httpx

from app.config import settings
from app.models.schemas import AirQualitySnapshot

logger = logging.getLogger(__name__)

_CACHE: dict[str, tuple[float, AirQualitySnapshot]] = {}

_AQI_BANDS: tuple[tuple[int, str, str], ...] = (
    (50, "Good", "07:00–19:00 (Natural cross-ventilation safe all day)"),
    (100, "Moderate", "11:00–16:00 (Midday mixing lowers ground-level particulates)"),
    (
        150,
        "Unhealthy for Sensitive Groups",
        "13:00–15:30 (Brief midday airing only; avoid rush-hour windows)",
    ),
    (
        200,
        "Unhealthy",
        "13:30–15:00 (Keep windows sealed during morning/evening inversions)",
    ),
    (
        300,
        "Very Unhealthy",
        "Keep sealed; use filtered recirculation (15 min midday flush only if stuffy)",
    ),
)
_HAZARDOUS_WINDOW = "Keep all windows sealed; run HEPA/DIY filtration continuously"

_CITY_FALLBACKS: dict[str, tuple[str, int, float, float, float]] = {
    "delhi": ("India", 312, 186.0, 265.0, 78.0),
    "new delhi": ("India", 312, 186.0, 265.0, 78.0),
    "mumbai": ("India", 158, 68.5, 118.0, 44.0),
    "kolkata": ("India", 215, 112.0, 174.0, 56.0),
    "bengaluru": ("India", 92, 31.4, 58.0, 29.0),
    "lahore": ("Pakistan", 348, 224.0, 310.0, 84.0),
    "beijing": ("China", 174, 88.0, 132.0, 52.0),
    "london": ("United Kingdom", 54, 13.5, 22.0, 24.0),
}


def classify_aqi(aqi: int) -> tuple[str, str]:
    """Return (severity_tier, best_ventilation_window) for a US AQI value."""
    for threshold, tier, window in _AQI_BANDS:
        if aqi <= threshold:
            return tier, window
    return "Hazardous (Severe Winter Smog)", _HAZARDOUS_WINDOW


def _build_snapshot(
    city: str,
    country: str,
    aqi: int,
    pm25: float,
    pm10: float,
    no2: float,
    source: str,
) -> AirQualitySnapshot:
    severity, window = classify_aqi(aqi)
    return AirQualitySnapshot(
        city=city,
        country=country,
        aqi_us=max(0, min(500, int(round(aqi)))),
        pm25_ug_m3=round(max(0.0, pm25), 1),
        pm10_ug_m3=round(max(0.0, pm10), 1),
        no2_ug_m3=round(max(0.0, no2), 1),
        severity_tier=severity,
        best_ventilation_window=window,
        source=source,
    )


def _simulate_aqi(city: str, aqi: int) -> AirQualitySnapshot:
    est_pm25 = round(aqi * 0.55, 1)
    return _build_snapshot(
        city=city.strip().title(),
        country="Simulated Scenario",
        aqi=aqi,
        pm25=est_pm25,
        pm10=round(est_pm25 * 1.45, 1),
        no2=round(min(120.0, aqi * 0.24), 1),
        source="User AQI Simulation",
    )


async def _fetch_open_meteo(city: str) -> AirQualitySnapshot | None:
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_s) as client:
            geo = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1, "language": "en", "format": "json"},
            )
            geo.raise_for_status()
            results = geo.json().get("results") or []
            if not results:
                return None

            loc = results[0]
            aq = await client.get(
                "https://air-quality-api.open-meteo.com/v1/air-quality",
                params={
                    "latitude": loc["latitude"],
                    "longitude": loc["longitude"],
                    "current": "us_aqi,pm2_5,pm10,nitrogen_dioxide",
                },
            )
            aq.raise_for_status()
            cur = aq.json().get("current") or {}
            aqi = int(cur.get("us_aqi") or 145)
            return _build_snapshot(
                city=loc.get("name", city.title()),
                country=loc.get("country", "Unknown"),
                aqi=aqi,
                pm25=float(cur.get("pm2_5") or aqi * 0.52),
                pm10=float(cur.get("pm10") or aqi * 0.85),
                no2=float(cur.get("nitrogen_dioxide") or 36.0),
                source="Open-Meteo Live Air Quality",
            )
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        logger.debug("Open-Meteo lookup failed for %s: %s", city, exc)
        return None


async def fetch_air_quality(
    city: str,
    manual_aqi_override: int | None = None,
) -> AirQualitySnapshot:
    """Fetch current air quality for a city, applying optional override or offline fallback."""
    if manual_aqi_override is not None:
        return _simulate_aqi(city, manual_aqi_override)

    key = city.strip().lower()
    now = time.monotonic()
    cached = _CACHE.get(key)
    if cached and (now - cached[0]) < settings.cache_ttl_s:
        return cached[1]

    live = await _fetch_open_meteo(city)
    if live is not None:
        _CACHE[key] = (now, live)
        return live

    fallback = _CITY_FALLBACKS.get(key, ("Urban Region", 185, 89.0, 142.0, 48.0))
    snap = _build_snapshot(
        city=city.strip().title(),
        country=fallback[0],
        aqi=fallback[1],
        pm25=fallback[2],
        pm10=fallback[3],
        no2=fallback[4],
        source="Regional Winter-Smog Baseline",
    )
    _CACHE[key] = (now, snap)
    return snap
