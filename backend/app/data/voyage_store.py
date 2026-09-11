"""In-memory active voyage tracking store for ORCA 2.0.

Powers real-time offshore safety monitoring. When a vessel departs port, a voyage is
registered here. The alert engine continuously checks new incoming advisories and
weather events against all active voyages.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from ..schemas import DecisionState

log = logging.getLogger(__name__)


class Voyage(BaseModel):
    voyage_id: str
    location: Dict[str, Any]
    region_geometry: Optional[Dict[str, Any]] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    status: Literal["ACTIVE", "ENDED"] = "ACTIVE"
    last_decision: Optional[DecisionState] = None


# In-memory storage of voyages
_VOYAGES: Dict[str, Voyage] = {}


def start_voyage(
    location: Dict[str, Any],
    region_geometry: Optional[Dict[str, Any]] = None,
    initial_decision: Optional[DecisionState] = None,
    voyage_id: Optional[str] = None,
) -> Voyage:
    """Register and start monitoring a new fishing voyage."""
    v_id = voyage_id or f"v-{uuid.uuid4().hex[:6]}"
    now = datetime.now(timezone.utc)

    # Normalize location
    loc = {
        "name": location.get("name", "Offshore Vessel"),
        "lat": float(location.get("lat") or location.get("latitude", 18.92)),
        "lon": float(location.get("lon") or location.get("longitude", 72.83)),
    }

    voyage = Voyage(
        voyage_id=v_id,
        location=loc,
        region_geometry=region_geometry,
        started_at=now,
        status="ACTIVE",
        last_decision=initial_decision,
    )
    _VOYAGES[v_id] = voyage
    log.info("Voyage started: %s at (%s, %s)", v_id, loc["lat"], loc["lon"])
    return voyage


def get_active_voyages() -> List[Voyage]:
    """Retrieve all currently active voyages."""
    return [v for v in _VOYAGES.values() if v.status == "ACTIVE"]


def get_voyage(voyage_id: str) -> Optional[Voyage]:
    """Look up a voyage by ID."""
    return _VOYAGES.get(voyage_id)


def update_voyage_decision(voyage_id: str, decision: DecisionState) -> Optional[Voyage]:
    """Update the safety assessment status for an active voyage."""
    voyage = _VOYAGES.get(voyage_id)
    if not voyage:
        return None
    updated = voyage.model_copy(update={"last_decision": decision})
    _VOYAGES[voyage_id] = updated
    return updated


def end_voyage(voyage_id: str) -> bool:
    """Mark an active voyage as ended."""
    voyage = _VOYAGES.get(voyage_id)
    if not voyage or voyage.status == "ENDED":
        return False
    now = datetime.now(timezone.utc)
    _VOYAGES[voyage_id] = voyage.model_copy(update={"status": "ENDED", "ended_at": now})
    log.info("Voyage ended: %s", voyage_id)
    return True


def clear_voyages() -> None:
    """Clear store (primarily for unit tests)."""
    _VOYAGES.clear()
