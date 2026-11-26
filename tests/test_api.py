"""API integration, security headers, and input validation tests."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_and_security_headers():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"
    assert "content-security-policy" in res.headers
    assert "permissions-policy" in res.headers


def test_index_serves_accessible_html():
    res = client.get("/")
    assert res.status_code == 200
    assert "Skip to main content" in res.text
    assert 'aria-live="polite"' in res.text
    assert "text-size-toggle" in res.text


def test_air_quality_endpoint_with_manual_aqi():
    res = client.get("/api/air-quality", params={"city": "Kolkata", "manual_aqi": 220})
    assert res.status_code == 200
    data = res.json()
    assert data["city"] == "Kolkata"
    assert data["aqi_us"] == 220


def test_plan_endpoint_with_manual_aqi():
    res = client.post(
        "/api/plan",
        json={
            "city": "Delhi",
            "household_size": 4,
            "has_children": True,
            "has_elderly": False,
            "has_respiratory_condition": True,
            "commute_mode": "car",
            "commute_km_per_day": 16,
            "home_type": "apartment",
            "cooking_fuel": "lpg_gas",
            "budget_tier": "low_budget",
            "manual_aqi_override": 310,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["air_quality"]["aqi_us"] == 310
    assert len(data["actions"]) == 6
    assert data["impact"]["projected_risk_score"] < data["impact"]["baseline_risk_score"]
    assert data["ai_narrative"]


def test_plan_endpoint_biomass_and_zero_cost():
    res = client.post(
        "/api/plan",
        json={
            "city": "Lahore",
            "commute_mode": "two_wheeler",
            "commute_km_per_day": 12,
            "cooking_fuel": "biomass_solid",
            "budget_tier": "zero_cost",
            "manual_aqi_override": 340,
        },
    )
    assert res.status_code == 200
    titles = [a["title"] for a in res.json()["actions"]]
    assert any("Clean-Cookstove" in t for t in titles)
    assert any("Wet-Mop" in t for t in titles)


def test_chat_endpoint_answers_question():
    res = client.post(
        "/api/chat",
        json={
            "profile": {"city": "Mumbai", "manual_aqi_override": 165},
            "question": "When is it safe to open windows today?",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert len(body["answer"]) > 20
    assert body["air_quality"]["city"] == "Mumbai"
    assert body["air_quality"]["aqi_us"] == 165


def test_invalid_inputs_rejected():
    assert client.post("/api/plan", json={"city": "12345"}).status_code == 422
    assert (
        client.post(
            "/api/chat",
            json={"profile": {"city": "Delhi"}, "question": "hi"},
        ).status_code
        == 422
    )
