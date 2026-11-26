# Efficiency & Resource Optimization

AeroShield is engineered for low latency, minimal memory footprint, and zero dependency bloat:

- **Repository Footprint:** Entire repository is under **100 KB** (zero `node_modules`, zero bundled binaries).
- **TTL Response Caching (`app/services/air_quality.py`):** Open-Meteo geocoding and AQI responses are cached in-memory per city for `600` seconds (`settings.cache_ttl_s`), eliminating redundant upstream API calls.
- **IPv4 Transport & Model Fallback (`app/services/genai_service.py`):** Uses `httpx.AsyncHTTPTransport(local_address="0.0.0.0")` to avoid Windows IPv6 stall timeouts and gracefully falls back across `gemini-flash-latest` → `gemini-flash-lite-latest` → `gemini-3.1-flash-lite` → `gemini-3-flash-preview`.
- **Non-Blocking Async I/O:** FastAPI async route handlers paired with `httpx.AsyncClient` handle concurrent requests efficiently.
- **Client-Side What-If Simulation (`app/static/app.js`):** Toggling action cards recalculates risk scores, PM2.5 reduction %, and CO₂e savings instantaneously in the browser with zero extra API round-trips.
