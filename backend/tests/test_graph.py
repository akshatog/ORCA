import pytest
from app.graph import get_ascii_topology, run_plan, ORCAState
from app.schemas import DecisionState


def test_graph_ascii_topology():
    topo = get_ascii_topology()
    assert "intent" in topo
    assert "weather" in topo
    assert "ocean" in topo
    assert "pfz" in topo
    assert "cyclone" in topo
    assert "gis" in topo
    assert "evidence_store" in topo
    assert "conflict_resolver" in topo
    assert "constraint_engine" in topo
    assert "route" in topo
    assert "explanation" in topo


def test_graph_mock_run_produces_valid_orca_state():
    state = run_plan(
        query="Is it safe to fish off Sassoon Dock tomorrow morning?",
        language="en",
        location={"name": "Sassoon Dock", "lat": 18.91, "lon": 72.82},
    )
    assert isinstance(state, ORCAState)
    assert state.request_id.startswith("req-")
    assert state.intent in ("operational", "analytical")
    assert len(state.evidence) > 0
    assert len(state.trace) >= 10

    dec = state.decision
    assert isinstance(dec, DecisionState)
    assert dec.status in ("SAFE", "CAUTION", "UNSAFE", "INSUFFICIENT_EVIDENCE")
    assert 0.0 <= dec.risk_score <= 100.0
    assert len(dec.reasons) > 0
    assert len(dec.explanation) > 0


def test_graph_trip_economics_calculated():
    state = run_plan(
        query="Calculate trip plan and economics for Mumbai waters",
        language="en",
    )
    econ = state.decision.trip_economics
    assert econ is not None
    assert "total_cost_inr" in econ
    assert "estimated_revenue_inr" in econ
    assert "net_trip_value_inr" in econ
    assert len(econ["basis"]) >= 3
