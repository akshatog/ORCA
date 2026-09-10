"""ORCA 2.0 /plan and /trace endpoints.

POST /plan: Primary decision endpoint invoking the LangGraph pipeline.
GET /trace/{request_id}: Returns node trace execution telemetry for visualizer.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from ..graph import run_plan
from ..schemas_v2 import DecisionState, ORCAState

log = logging.getLogger(__name__)

router = APIRouter(tags=["ORCA 2.0 Plan & Trace"])

# In-memory store for ORCAState objects keyed by request_id
STATE_STORE: Dict[str, ORCAState] = {}


class PlanRequest(BaseModel):
    location: Optional[Dict[str, Any]] = None
    intent_text: Optional[str] = None
    query: Optional[str] = None
    language: str = Field(default="en")


@router.post("/plan", response_model=DecisionState)
def plan_endpoint(req: PlanRequest, response: Response) -> DecisionState:
    """Run the ORCA 2.0 LangGraph decision pipeline for an operational or analytical query."""
    user_query = req.intent_text or req.query or "Can I safely go fishing?"
    
    state = run_plan(
        query=user_query,
        language=req.language,
        location=req.location,
    )

    STATE_STORE[state.request_id] = state
    response.headers["X-Request-ID"] = state.request_id

    if not state.decision:
        raise HTTPException(status_code=500, detail="Pipeline failed to produce a valid DecisionState")

    return state.decision


@router.get("/trace/{request_id}")
def trace_endpoint(request_id: str) -> List[Dict[str, Any]]:
    """Retrieve the execution trace of all LangGraph pipeline nodes for a given request."""
    state = STATE_STORE.get(request_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Trace not found for request_id: {request_id}")
    return state.trace
