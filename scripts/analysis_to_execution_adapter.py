#!/usr/bin/env python3
"""
Adapter between analysis-layer outputs and execution-layer inputs.
"""

from __future__ import annotations

from typing import Any, Dict


def normalize_signal_direction(direction: Any) -> Dict[str, Any]:
    raw = str(direction or "neutral").strip().lower()
    if raw == "flip_long":
        return {"raw_direction": raw, "normalized_direction": "flip", "target_direction": "long"}
    if raw == "flip_short":
        return {"raw_direction": raw, "normalized_direction": "flip", "target_direction": "short"}
    if raw in ("long", "short", "neutral"):
        return {"raw_direction": raw, "normalized_direction": raw, "target_direction": raw}
    return {"raw_direction": raw, "normalized_direction": "neutral", "target_direction": "neutral"}


def adapt_analysis_outputs(
    lifecycle_output: Dict[str, Any],
    fatigue_output: Dict[str, Any],
    validation_output: Dict[str, Any],
    signal_output: Dict[str, Any],
    *,
    severity: str,
    correlation: float,
    liquidity_state: str,
    policy_intervention: str = "NONE",
    is_crowded: bool = False,
    narrative_mode: str = "Fact-Driven",
) -> Dict[str, Any]:
    direction = normalize_signal_direction(signal_output.get("direction", "neutral"))
    risk_input = {
        "event_state": lifecycle_output.get("lifecycle_state", "Detected"),
        "fatigue_index": fatigue_output.get("fatigue_final", 0),
        "liquidity_state": liquidity_state,
        "correlation": correlation,
        "score": signal_output.get("score", 0),
        "severity": severity,
        "A1": validation_output.get("A1", 0),
        "policy_intervention": policy_intervention,
        "is_crowded": is_crowded,
        "narrative_mode": narrative_mode,
    }
    return {
        "risk_input": risk_input,
        "execution_context": {
            "normalized_direction": direction["target_direction"],
            "direction_semantics": direction["normalized_direction"],
            "raw_direction": direction["raw_direction"],
        },
    }

