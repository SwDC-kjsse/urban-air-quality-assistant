# Code Quality & Architecture

AeroShield is structured around clean separation of concerns, strict static analysis, and deterministic business logic:

## Module Structure
- `app/main.py`: FastAPI entrypoint, security middleware, static UI serving, and typed route handlers.
- `app/config.py`: Immutable `Settings` dataclass loaded from environment variables via `python-dotenv`.
- `app/models/schemas.py`: Strict Pydantic v2 schemas (`HouseholdProfile`, `AirQualitySnapshot`, `ActionItem`, `ImpactSummary`, `PlanResponse`, `ChatRequest`, `ChatResponse`) with custom field validators.
- `app/services/air_quality.py`: Open-Meteo Geocoding & Air Quality API client with 10-minute TTL caching, table-driven `_AQI_BANDS` classification, and offline winter-smog baselines.
- `app/services/context_engine.py`: Modular, single-purpose helpers (`compute_baseline_risk`, `_build_routine_actions`, `_build_indoor_actions`, `_build_sustainable_actions`, `compute_impact_summary`) using data-driven mappings (`_INDOOR_HACK_BY_BUDGET`, `_RISK_BANDS`).
- `app/services/genai_service.py`: Google Gemini REST integration with IPv4 transport, model fallback chain, structured logging, and deterministic offline fallback.
- `app/static/`: Accessible, zero-dependency frontend (`index.html`, `styles.css`, `app.js`) with modular DOM builders (`createActionCard`, `createCategorySvg`).

## Static Analysis & Standards
- **Ruff (`pyproject.toml`):** Enforces `E`, `F`, `I`, `B`, `UP`, `SIM` rules at `line-length = 100` (`ruff check .` passes with 0 errors).
- **Formatting:** Standardized via `.editorconfig` and `.pre-commit-config.yaml`.
- **Type Safety:** Explicit Python 3.11+ type annotations across all route handlers, services, and Pydantic models.
