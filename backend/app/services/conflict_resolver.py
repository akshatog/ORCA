"""Authority & Conflict Resolution Policy for ORCA 2.0.

Governs multi-source data reconciliation. When multiple data sources report on the
same metric (e.g., Open-Meteo external forecast vs IMD official forecast vs StormGlass),
the Conflict Resolver arbitrates strictly using the authoritative hierarchy:

    official_advisory > official_forecast > external_forecast > derived > heuristic

Tie-breakers:
    1. Confidence score (higher wins)
    2. Recency / observed_at timestamp (fresher wins)

Winning evidence items are marked `conflict_status="selected"`.
Losing evidence items are preserved (for audit/provenance) marked `conflict_status="overridden"`
with an explicit `conflict_reason`.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from ..schemas import Evidence

log = logging.getLogger(__name__)

AUTHORITY_HIERARCHY = {
    "official_advisory": 5,
    "official_forecast": 4,
    "external_forecast": 3,
    "derived": 2,
    "heuristic": 1,
}


def resolve_conflicts(evidence_list: List[Evidence]) -> Tuple[List[Evidence], List[Dict[str, Any]]]:
    """Arbitrate conflicting evidence items for identical metrics.

    Args:
        evidence_list: List of raw Evidence items gathered from various sources.

    Returns:
        Tuple of (reconciled_evidence_list, conflict_log)
    """
    if not evidence_list:
        return [], []

    by_metric: Dict[str, List[Evidence]] = {}
    for ev in evidence_list:
        by_metric.setdefault(ev.metric, []).append(ev)

    reconciled: List[Evidence] = []
    conflict_log: List[Dict[str, Any]] = []

    for metric, items in by_metric.items():
        if len(items) == 1:
            # No conflict
            single = items[0]
            if single.conflict_status is None:
                single = single.model_copy(update={"conflict_status": "selected"})
            reconciled.append(single)
            continue

        # Sort descending by:
        # 1. Authority hierarchy rank (5 down to 1)
        # 2. Confidence (1.0 down to 0.0)
        # 3. observed_at timestamp (newest first)
        def sort_key(e: Evidence):
            rank = AUTHORITY_HIERARCHY.get(e.authority_level, 0)
            conf = e.confidence
            obs_ts = e.observed_at.timestamp() if e.observed_at else 0.0
            return (rank, conf, obs_ts)

        sorted_items = sorted(items, key=sort_key, reverse=True)
        winner = sorted_items[0]
        losers = sorted_items[1:]

        # Mark winner as selected
        winner_copy = winner.model_copy(update={"conflict_status": "selected"})
        reconciled.append(winner_copy)

        overridden_entries: List[Dict[str, Any]] = []
        for loser in losers:
            reason = (
                f"Overridden by {winner.source} "
                f"(Authority: {winner.authority_level} > {loser.authority_level}, "
                f"Confidence: {winner.confidence:.2f} vs {loser.confidence:.2f})"
            )
            loser_copy = loser.model_copy(update={
                "conflict_status": "overridden",
                "conflict_reason": reason,
            })
            reconciled.append(loser_copy)
            overridden_entries.append({
                "source": loser.source,
                "value": loser.value,
                "authority_level": loser.authority_level,
                "confidence": loser.confidence,
                "reason": reason,
            })

        conflict_log.append({
            "metric": metric,
            "winner": {
                "source": winner.source,
                "value": winner.value,
                "authority_level": winner.authority_level,
                "confidence": winner.confidence,
            },
            "overridden": overridden_entries,
            "rationale": f"Authority priority: {winner.authority_level} ({winner.source}) selected",
        })

    return reconciled, conflict_log


def get_selected_evidence(evidence_list: List[Evidence]) -> List[Evidence]:
    """Filter to only active, selected Evidence items."""
    return [e for e in evidence_list if e.conflict_status == "selected"]
