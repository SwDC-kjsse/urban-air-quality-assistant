# Security Implementation

AeroShield follows defense-in-depth practices across transport headers, input validation, secret management, and frontend rendering:

## 1. Secret Management
- `GEMINI_API_KEY` is loaded exclusively from `.env` via `app/config.py` and excluded from Git via `.gitignore`.
- API keys are passed via the `X-goog-api-key` HTTP header rather than query parameters, and exception logs never print credentials.

## 2. HTTP Security Headers (`app/main.py`)
Every HTTP response includes:
- `Content-Security-Policy`: Restricts `default-src 'self'`, `script-src 'self'`, `object-src 'none'`, and `frame-ancestors 'none'`.
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), microphone=(), camera=()`

## 3. Input Validation & XSS Prevention
- **Backend:** Pydantic v2 enforces strict numeric bounds (`household_size` 1–15, `commute_km_per_day` 0–150, `manual_aqi_override` 10–500), `Literal` enums, and alphabetic city validation (`clean_city`, `clean_question`).
- **Frontend:** All dynamic text is inserted with `.textContent`, and SVG icons are built with `document.createElementNS` (zero `innerHTML` usage).
