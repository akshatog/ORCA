"""ORCA 2.0 LangGraph StateGraph Compilation and Execution.

Topology:
intent → [weather, ocean, pfz, cyclone, gis] → evidence_store → conflict_resolver → constraint_engine → route → explanation
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from langgraph.graph import END, START, StateGraph

from ..schemas import ORCAState
from .state import ORCAGraphState
from .nodes import (
    conflict_resolver_node,
    constraint_engine_node,
    cyclone_node,
    evidence_store_node,
    explanation_node,
    gis_node,
    intent_node,
    ocean_node,
    pfz_node,
    route_node,
    weather_node,
)

log = logging.getLogger(__name__)

_COMPILED_GRAPH = None


def build_graph():
    """Build and compile the ORCA 2.0 LangGraph pipeline."""
    builder = StateGraph(ORCAGraphState)

    # Register nodes
    builder.add_node("intent", intent_node)
    builder.add_node("weather", weather_node)
    builder.add_node("ocean", ocean_node)
    builder.add_node("pfz", pfz_node)
    builder.add_node("cyclone", cyclone_node)
    builder.add_node("gis", gis_node)
    builder.add_node("evidence_store", evidence_store_node)
    builder.add_node("conflict_resolver", conflict_resolver_node)
    builder.add_node("constraint_engine", constraint_engine_node)
    builder.add_node("route", route_node)
    builder.add_node("explanation", explanation_node)

    # Edge connections
    builder.add_edge(START, "intent")

    # Parallel specialists fan-out
    builder.add_edge("intent", "weather")
    builder.add_edge("intent", "ocean")
    builder.add_edge("intent", "pfz")
    builder.add_edge("intent", "cyclone")
    builder.add_edge("intent", "gis")

    # Fan-in to evidence store
    builder.add_edge("weather", "evidence_store")
    builder.add_edge("ocean", "evidence_store")
    builder.add_edge("pfz", "evidence_store")
    builder.add_edge("cyclone", "evidence_store")
    builder.add_edge("gis", "evidence_store")

    # Core sequential pipeline
    builder.add_edge("evidence_store", "conflict_resolver")
    builder.add_edge("conflict_resolver", "constraint_engine")
    builder.add_edge("constraint_engine", "route")
    builder.add_edge("route", "explanation")
    builder.add_edge("explanation", END)

    return builder.compile()


def get_compiled_graph():
    global _COMPILED_GRAPH
    if _COMPILED_GRAPH is None:
        _COMPILED_GRAPH = build_graph()
    return _COMPILED_GRAPH


def get_ascii_topology() -> str:
    """Return the ASCII representation of the compiled graph topology."""
    graph = get_compiled_graph()
    try:
        return graph.get_graph().draw_ascii()
    except Exception:
        return (
            "START -> intent\n"
            "intent -> [weather, ocean, pfz, cyclone, gis]\n"
            "[weather, ocean, pfz, cyclone, gis] -> evidence_store\n"
            "evidence_store -> conflict_resolver -> constraint_engine -> route -> explanation -> END"
        )


def run_plan(
    query: str,
    language: str = "en",
    location: Optional[dict] = None,
    request_id: Optional[str] = None,
) -> ORCAState:
    """Execute the full ORCA 2.0 graph for a user query."""
    req_id = request_id or f"req-{uuid.uuid4().hex[:8]}"
    initial_state = ORCAGraphState(
        request_id=req_id,
        intent="operational",
        raw_query=query,
        language=language,
        location=location,
        evidence=[],
        advisories=[],
        conflict_log=[],
        decision=None,
        trace=[],
    )

    graph = get_compiled_graph()
    final_output = graph.invoke(initial_state)
    
    if isinstance(final_output, dict):
        return ORCAState(
            request_id=final_output.get("request_id", req_id),
            intent=final_output.get("intent", "operational"),
            raw_query=final_output.get("raw_query", query),
            language=final_output.get("language", language),
            location=final_output.get("location"),
            evidence=final_output.get("evidence", []),
            advisories=final_output.get("advisories", []),
            conflict_log=final_output.get("conflict_log", []),
            decision=final_output.get("decision"),
            trace=final_output.get("trace", []),
        )
    elif hasattr(final_output, "to_orca_state"):
        return final_output.to_orca_state()
    return final_output
