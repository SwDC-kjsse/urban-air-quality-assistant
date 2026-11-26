# Testing & Validation

AeroShield includes an automated `pytest` suite covering domain logic, API endpoints, security headers, input validation, and offline GenAI fallbacks:

## Test Suites (`tests/`)
- `tests/test_context_engine.py`:
  - Verifies US AQI tier classification (`Good` through `Hazardous`).
  - Verifies household vulnerability multipliers (children, elderly, respiratory conditions) increase baseline risk scores.
  - Verifies budget-tier action tailoring (`zero_cost` Wet-Mop, `low_budget` Corsi-Rosenthal, `moderate` True HEPA H13).
  - Verifies diminishing-returns PM2.5 exposure reduction and CO₂e math.
- `tests/test_api.py`:
  - Verifies `GET /api/health` and presence of security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`, `Permissions-Policy`).
  - Verifies `GET /` serves accessible HTML (`Skip to main content`, `aria-live="polite"`, `text-size-toggle`).
  - Verifies `GET /api/air-quality`, `POST /api/plan` (standard + `biomass_solid`/`zero_cost`), `POST /api/chat`, and `422` rejection of invalid inputs.
- `tests/test_genai_service.py`:
  - Verifies deterministic offline narrative generation and topic-routed follow-up answers (`purifier`, `window`, `school/N95`, default) via monkeypatched `_call_gemini`.

## Running Tests
```bash
pytest -v
ruff check .
```
All **13/13** tests and `ruff check .` pass cleanly.
