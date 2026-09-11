"""LangGraph state definition for ORCA 2.0 with reducers for parallel execution."""
from __future__ import annotations

import operator
from typing import Annotated, Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from ..schemas import AdvisoryConstraint, DecisionState, Evidence, ORCAState


class ORCAGraphState(BaseModel):
    """Internal LangGraph state with list reducers to support parallel node fan-in."""
    request_id: str
    intent: Literal["operational", "analytical"] = "operational"
    raw_query: str = ""
    language: str = "en"
    location: Optional[dict] = None
    evidence: Annotated[List[Evidence], operator.add] = Field(default_factory=list)
    advisories: Annotated[List[AdvisoryConstraint], operator.add] = Field(default_factory=list)
    conflict_log: Annotated[List[dict], operator.add] = Field(default_factory=list)
    decision: Optional[DecisionState] = None
    trace: Annotated[List[dict], operator.add] = Field(default_factory=list)

    def to_orca_state(self) -> ORCAState:
        return ORCAState(
            request_id=self.request_id,
            intent=self.intent,
            raw_query=self.raw_query,
            language=self.language,
            location=self.location,
            evidence=self.evidence,
            advisories=self.advisories,
            conflict_log=self.conflict_log,
            decision=self.decision,
            trace=self.trace,
        )


__all__ = ["ORCAGraphState", "ORCAState", "Evidence", "AdvisoryConstraint", "DecisionState"]
