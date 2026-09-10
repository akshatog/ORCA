"""ORCA 2.0 Active Voyage Tracking and Real-Time Alert Endpoints.

Endpoints:
- POST /voyages/start: Register and track an active voyage.
- GET /voyages/active: List all active voyages being monitored.
- POST /voyages/{voyage_id}/end: Stop tracking a voyage when the vessel returns.
- POST /alerts/trigger: Inject new evidence/advisories to simulate conditions deteriorating.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..data.voyage_store import (
    Voyage,
    end_voyage,
    get_active_voyages,
    get_voyage,
    start_voyage,
)
from ..schemas_v2 import AdvisoryConstraint, AlertEvent, DecisionState, Evidence, make_evidence
from ..services.alert_engine import on_evidence_change, trigger_manual_alert

log = logging.getLogger(__name__)

router = APIRouter(tags=["ORCA 2.0 Voyage & Alert Monitor"])


class StartVoyageRequest(BaseModel):
    location: Dict[str, Any]
    region_geometry: Optional[Dict[str, Any]] = None
    initial_decision: Optional[DecisionState] = None
    voyage_id: Optional[str] = None


class StartVoyageResponse(BaseModel):
    voyage_id: str
    started_at: str
    status: str = "ACTIVE"
    location: Dict[str, Any]


class EndVoyageResponse(BaseModel):
    status: str = "ended"
    voyage_id: str


class TriggerAlertRequest(BaseModel):
    voyage_id: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    advisory: Optional[Dict[str, Any]] = None
    severity: Optional[str] = "SEVERE"
    headline: Optional[str] = "Severe weather warning issued"


class TriggerAlertResponse(BaseModel):
    alerts: List[AlertEvent] = Field(default_factory=list)


@router.post("/voyages/start", response_model=StartVoyageResponse)
@router.post("/api/voyages/start", response_model=StartVoyageResponse, include_in_schema=False)
def start_voyage_endpoint(req: StartVoyageRequest) -> StartVoyageResponse:
    """Start tracking a new voyage for real-time alert monitoring."""
    voyage = start_voyage(
        location=req.location,
        region_geometry=req.region_geometry,
        initial_decision=req.initial_decision,
        voyage_id=req.voyage_id,
    )
    return StartVoyageResponse(
        voyage_id=voyage.voyage_id,
        started_at=voyage.started_at.isoformat(),
        status=voyage.status,
        location=voyage.location,
    )


@router.get("/voyages/active", response_model=List[Voyage])
@router.get("/api/voyages/active", response_model=List[Voyage], include_in_schema=False)
def get_active_voyages_endpoint() -> List[Voyage]:
    """Retrieve all currently active voyages."""
    return get_active_voyages()


@router.post("/voyages/{voyage_id}/end", response_model=EndVoyageResponse)
@router.post("/api/voyages/{voyage_id}/end", response_model=EndVoyageResponse, include_in_schema=False)
def end_voyage_endpoint(voyage_id: str) -> EndVoyageResponse:
    """End an active voyage."""
    voyage = get_voyage(voyage_id)
    if not voyage:
        raise HTTPException(status_code=404, detail=f"Voyage {voyage_id} not found")
    success = end_voyage(voyage_id)
    if not success:
        log.warning("Voyage %s was already ended or cannot be ended", voyage_id)
    return EndVoyageResponse(status="ended", voyage_id=voyage_id)


@router.post("/alerts/trigger", response_model=TriggerAlertResponse)
@router.post("/api/alerts/trigger", response_model=TriggerAlertResponse, include_in_schema=False)
def trigger_alert_endpoint(req: TriggerAlertRequest) -> TriggerAlertResponse:
    """Simulate an incoming alert or new hazard reading against active voyages."""
    if req.advisory:
        adv_data = req.advisory
        now = datetime.now(timezone.utc)
        adv = AdvisoryConstraint(
            authority=adv_data.get("authority", "IMD"),
            constraint_type=adv_data.get("constraint_type", "NO_GO"),
            named_region=adv_data.get("named_region", "Coastal Waters"),
            severity=adv_data.get("severity", req.severity or "SEVERE"),
            valid_from=adv_data.get("valid_from", now),
            valid_until=adv_data.get("valid_until", now),
            source_text=adv_data.get("source_text", req.headline or "Severe marine bulletin"),
            source_reference=adv_data.get("source_reference", "MANUAL-INJECT"),
            confidence=float(adv_data.get("confidence", 0.95)),
        )
        alerts = on_evidence_change(new_advisories=[adv])
    elif req.evidence:
        ev_dict = dict(req.evidence)
        ev = make_evidence(**ev_dict)
        alerts = on_evidence_change(new_evidence=[ev])
    else:
        alerts = trigger_manual_alert(
            voyage_id=req.voyage_id,
            headline=req.headline or "Severe weather warning issued",
            severity=req.severity or "SEVERE",
        )

    return TriggerAlertResponse(alerts=alerts)
