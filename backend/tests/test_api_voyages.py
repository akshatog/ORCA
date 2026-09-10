from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.data.voyage_store import clear_voyages
from app.main import app


@pytest.fixture(autouse=True)
def clean_store():
    clear_voyages()
    yield
    clear_voyages()


def test_voyage_and_alert_full_lifecycle():
    client = TestClient(app)

    # 1. Start a voyage from Ratnagiri
    start_resp = client.post(
        "/voyages/start",
        json={
            "location": {"name": "Ratnagiri Coast", "lat": 16.99, "lon": 73.25},
            "voyage_id": "v-ratnagiri-101",
        },
    )
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    assert start_data["voyage_id"] == "v-ratnagiri-101"
    assert start_data["status"] == "ACTIVE"
    assert "started_at" in start_data

    # 2. Verify it shows up in GET /voyages/active
    active_resp = client.get("/voyages/active")
    assert active_resp.status_code == 200
    active_data = active_resp.json()
    assert len(active_data) == 1
    assert active_data[0]["voyage_id"] == "v-ratnagiri-101"

    # 3. Trigger alert with severe advisory
    alert_resp = client.post(
        "/alerts/trigger",
        json={
            "advisory": {
                "authority": "IMD",
                "constraint_type": "NO_GO",
                "severity": "SEVERE",
                "source_text": "Cyclone approaching Maharashtra and Goa coast. Total suspension of fishing operations.",
            }
        },
    )
    assert alert_resp.status_code == 200
    alerts = alert_resp.json()["alerts"]
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["voyage_id"] == "v-ratnagiri-101"
    assert alert["previous_status"] == "SAFE"
    assert alert["new_status"] == "UNSAFE"
    assert alert["safe_port"]["name"] == "Ratnagiri"
    assert alert["safe_port"]["distance_km"] > 0

    # 4. Check that active voyage last_decision is now UNSAFE
    active_resp2 = client.get("/voyages/active")
    assert active_resp2.status_code == 200
    updated_voyage = active_resp2.json()[0]
    assert updated_voyage["last_decision"]["status"] == "UNSAFE"

    # 5. End the voyage
    end_resp = client.post("/voyages/v-ratnagiri-101/end")
    assert end_resp.status_code == 200
    assert end_resp.json() == {"status": "ended", "voyage_id": "v-ratnagiri-101"}

    # 6. Active list is now empty
    active_resp3 = client.get("/voyages/active")
    assert active_resp3.status_code == 200
    assert len(active_resp3.json()) == 0

    # 7. Non-existent voyage returns 404
    bad_end_resp = client.post("/voyages/v-nonexistent/end")
    assert bad_end_resp.status_code == 404
