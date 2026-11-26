"""FastAPI entry point for the Urban Air Quality Assistant."""
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, Query, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.models.schemas import (
    AirQualitySnapshot,
    ChatRequest,
    ChatResponse,
    HouseholdProfile,
    PlanResponse,
)
from app.services.air_quality import fetch_air_quality
from app.services.context_engine import (
    compute_baseline_risk,
    compute_impact_summary,
    generate_tailored_actions,
)
from app.services.genai_service import answer_followup, generate_plan_narrative

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="Urban Air Quality Assistant",
    description=(
        "GenAI-powered winter smog and urban air pollution navigator "
        "for families and communities."
    ),
    version="1.0.0",
)


@app.middleware("http")
async def add_security_headers(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Attach standard security headers to all HTTP responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'none'"
    )
    return response


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    """Serve the accessible web interface."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "urban-air-quality-assistant"}


@app.get("/api/air-quality", response_model=AirQualitySnapshot)
async def get_air_quality(
    city: str = Query(default="Delhi", min_length=2, max_length=80),
    manual_aqi: int | None = Query(default=None, ge=10, le=500),
) -> AirQualitySnapshot:
    """Fetch current air quality snapshot for a given city."""
    return await fetch_air_quality(city=city, manual_aqi_override=manual_aqi)


@app.post("/api/plan", response_model=PlanResponse)
async def create_action_plan(profile: HouseholdProfile) -> PlanResponse:
    """Generate a tailored winter smog action plan with quantified impact."""
    aq = await fetch_air_quality(profile.city, profile.manual_aqi_override)
    baseline_risk, risk_level, risk_explanation = compute_baseline_risk(profile, aq)
    actions = generate_tailored_actions(profile, aq)
    impact = compute_impact_summary(baseline_risk, actions)
    narrative, provider = await generate_plan_narrative(profile, aq, actions, impact)

    return PlanResponse(
        air_quality=aq,
        risk_level=risk_level,
        risk_explanation=risk_explanation,
        ai_narrative=narrative,
        ai_provider=provider,
        actions=actions,
        impact=impact,
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_assistant(payload: ChatRequest) -> ChatResponse:
    """Answer a follow-up question grounded in the household's location and lifestyle."""
    aq = await fetch_air_quality(payload.profile.city, payload.profile.manual_aqi_override)
    answer, provider = await answer_followup(payload.profile, aq, payload.question)
    return ChatResponse(answer=answer, ai_provider=provider, air_quality=aq)
