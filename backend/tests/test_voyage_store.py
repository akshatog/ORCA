import pytest
from app.data.voyage_store import (
    start_voyage,
    get_active_voyages,
    get_voyage,
    update_voyage_decision,
    end_voyage,
    clear_voyages,
)
from app.schemas_v2 import DecisionState


@pytest.fixture(autouse=True)
def clean_store():
    clear_voyages()
    yield
    clear_voyages()


def test_start_and_get_voyage():
    voyage = start_voyage(
        location={"name": "Mumbai Port", "lat": 18.92, "lon": 72.83},
        voyage_id="v-test-1",
    )
    assert voyage.voyage_id == "v-test-1"
    assert voyage.status == "ACTIVE"
    assert voyage.location["lat"] == 18.92
    assert voyage.location["lon"] == 72.83

    fetched = get_voyage("v-test-1")
    assert fetched is not None
    assert fetched.voyage_id == "v-test-1"

    active = get_active_voyages()
    assert len(active) == 1
    assert active[0].voyage_id == "v-test-1"


def test_update_voyage_decision():
    voyage = start_voyage(
        location={"lat": 18.95, "lon": 72.80},
        voyage_id="v-test-update",
    )
    assert voyage.last_decision is None

    new_decision = DecisionState(
        status="SAFE",
        risk_score=15.0,
        reasons=["Low wave height and moderate winds."],
        language="en",
        explanation="Conditions are favorable for fishing.",
        generated_at=pytest.importorskip("datetime").datetime.now(pytest.importorskip("datetime").timezone.utc),
    )
    updated = update_voyage_decision("v-test-update", new_decision)
    assert updated is not None
    assert updated.last_decision.status == "SAFE"
    assert updated.last_decision.risk_score == 15.0

    # Check that store has updated value
    fetched = get_voyage("v-test-update")
    assert fetched.last_decision.status == "SAFE"


def test_end_voyage():
    start_voyage(
        location={"lat": 18.95, "lon": 72.80},
        voyage_id="v-test-end",
    )
    assert len(get_active_voyages()) == 1

    success = end_voyage("v-test-end")
    assert success is True
    assert len(get_active_voyages()) == 0

    v = get_voyage("v-test-end")
    assert v.status == "ENDED"
    assert v.ended_at is not None

    # Ending again returns False
    assert end_voyage("v-test-end") is False
