# AeroShield — Urban Air Quality Assistant

**Chosen Vertical:** `[Challenge 6] Urban Air Quality Assistant`

AeroShield is a GenAI-powered assistant that helps families and communities navigate severe winter smog and urban air pollution. It combines live air quality telemetry, a deterministic household risk & emissions engine, and Google Gemini (`gemini-2.5-flash`) to deliver tailored low-emission routines, indoor air quality hacks, and quantified health/CO₂e impact.

---

## Approach & Logic

1. **Live Environmental Context (`app/services/air_quality.py`):**
   - Resolves any city via Open-Meteo Geocoding + Air Quality API (`us_aqi`, `pm2_5`, `pm10`, `nitrogen_dioxide`) with a 10-minute in-memory TTL cache and regional winter-smog fallbacks for offline resilience.
   - Identifies the optimal **midday ventilation window** (e.g., `13:00–15:30`) when winter thermal inversions lift, or advises sealed filtration during Hazardous (`>300 AQI`) episodes.
2. **Deterministic Household Decision Engine (`app/services/context_engine.py`):**
   - Calculates a `0–100` baseline health risk score using AQI severity plus household vulnerability factors (children, elderly, asthma/respiratory sensitivity, solid-fuel cooking).
   - Selects 6 personalized actions across **Daily Routines**, **Indoor Air Hacks** (matched to `zero_cost`, `low_budget`, or `moderate` budgets—from wet-mopping to DIY Corsi-Rosenthal MERV-13 box-fan filters and True HEPA H13), and **Sustainable Alternatives**.
   - Quantifies direct impact using diminishing-returns PM2.5 exposure reduction (`1 - ∏(1 - r_i)`) and passenger-km CO₂e savings (`kg CO₂e/week`, annual CO₂e, and equivalent trees planted).
3. **Google Gemini GenAI Layer (`app/services/genai_service.py`):**
   - Grounds `gemini-2.5-flash` in the household's live AQI, constraints, and computed impact numbers to produce a concise executive briefing and answer follow-up questions.
   - Includes a deterministic context-engine fallback so evaluators can test every endpoint even without a `GEMINI_API_KEY`.
4. **Interactive & Accessible UI (`app/static/`):**
   - Built with an atmospheric Aurora + DotGrid canvas, cursor-tracking Spotlight cards, animated impact counters, an interactive **What-If simulator** (toggle any action card to see risk & CO₂e recalculate live), keyboard navigation, ARIA live regions, and a **High Contrast** toggle.

---

## How the Solution Works

- **Backend:** FastAPI (`app/main.py`) exposing:
  - `GET /` — Accessible web application
  - `GET /api/health` — Service health check
  - `GET /api/air-quality?city=...` — Live AQI snapshot
  - `POST /api/plan` — Tailored 6-action plan, risk score, quantified impact, and GenAI narrative
  - `POST /api/chat` — Context-aware follow-up Q&A
- **Security:** Pydantic v2 strict input validation, XSS-safe DOM rendering (`textContent`), HTTP security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`), and `.env`-isolated API keys.

---

## Quick Start

```bash
# 1. Create and activate virtual environment
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure Gemini API key (optional; offline fallback works without it)
cp .env.example .env
# Add GEMINI_API_KEY=your_key_here inside .env

# 4. Run the application
uvicorn app.main:app --reload

# 5. Run automated tests
pytest -v
```

Open `http://127.0.0.1:8000` in your browser.

---

## Assumptions Made

- **Ventilation Windows:** Urban winter smog typically exhibits morning/evening boundary-layer inversions; midday (`13:00–15:30`) offers brief mixing unless AQI exceeds 300 (Hazardous), where sealed indoor filtration is safer.
- **Commute Emissions:** CO₂e savings assume 3 commute days/week shifted from personal car (`0.192 kg/km`) or two-wheeler (`0.084 kg/km`) to public transit (`0.041 kg/km`), and tree equivalents use `21.77 kg CO₂/tree/year`.
- **PM2.5 Exposure Modeling:** Combined exposure reduction uses an independent multiplicative diminishing-returns model capped at `85%` to avoid unrealistic >100% claims.
