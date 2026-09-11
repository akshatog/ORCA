from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_post_plan_valid_decision_state():
    payload = {
        "location": {"lat": 19.07, "lon": 72.87},
        "intent_text": "Can I safely fish tomorrow off Mumbai?",
        "language": "en",
    }
    response = client.post("/plan", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert "status" in data
    assert data["status"] in ("SAFE", "CAUTION", "UNSAFE", "INSUFFICIENT_EVIDENCE")
    assert "risk_score" in data
    assert 0.0 <= data["risk_score"] <= 100.0
    assert "reasons" in data
    assert isinstance(data["reasons"], list)
    assert len(data["reasons"]) > 0
    assert "explanation" in data
    assert len(data["explanation"]) > 0
    assert "trip_economics" in data
    assert data["trip_economics"] is not None

    req_id = response.headers.get("X-Request-ID")
    assert req_id is not None
    assert req_id.startswith("req-")

    # Now verify GET /trace/{request_id}
    trace_res = client.get(f"/trace/{req_id}")
    assert trace_res.status_code == 200
    trace_items = trace_res.json()
    assert isinstance(trace_items, list)
    assert len(trace_items) >= 10

    agent_names = [t["agent"] for t in trace_items]
    assert "intent" in agent_names
    assert "weather" in agent_names
    assert "ocean" in agent_names
    assert "constraint_engine" in agent_names
    assert "route" in agent_names
    assert "explanation" in agent_names


def test_get_trace_not_found():
    response = client.get("/trace/non-existent-request-id-12345")
    assert response.status_code == 404
    assert "not found" in response.json().get("detail", "").lower()
