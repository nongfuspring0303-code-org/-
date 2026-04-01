#!/usr/bin/env python3
"""
Interface compatibility checks for analysis layer.

Checks one upstream adaptation path and one downstream adaptation path.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from edt_module_base import ModuleStatus
from analysis_to_execution_adapter import adapt_analysis_outputs, normalize_signal_direction
from fatigue_calculator import FatigueCalculator
from lifecycle_manager import LifecycleManager
from market_validator import MarketValidator
from signal_scorer import SignalScorer


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_upstream_eventobjectifier_to_lifecycle() -> None:
    event_output_schema = load_json(ROOT / "schemas" / "event_output.json")
    required = set(event_output_schema["required"])
    sample = {
        "event_id": "ME-C-20260330-001.V1.0",
        "category": "C",
        "source_rank": "A",
        "severity": "E3",
        "lifecycle_state": "Detected",
        "confidence": 85,
        "headline": "美国宣布新一轮关税措施",
        "detected_at": "2026-03-30T13:30:00Z",
    }
    if not required.issubset(sample.keys()):
        raise AssertionError("upstream sample does not satisfy event_output required fields")

    lifecycle_input = {
        "event_id": sample["event_id"],
        "category": sample["category"],
        "severity": sample["severity"],
        "source_rank": sample["source_rank"],
        "headline": sample["headline"],
        "detected_at": sample["detected_at"],
        "is_official_confirmed": True,
        "market_validated": True,
        "has_material_update": True,
        "elapsed_hours": 4,
    }
    result = LifecycleManager().run(lifecycle_input)
    if result.status != ModuleStatus.SUCCESS:
        raise AssertionError(f"upstream adaptation failed: {result.errors}")


def check_downstream_analysis_bundle_to_risk_input() -> None:
    lifecycle = LifecycleManager().run(
        {
            "event_id": "ME-C-20260330-001.V1.0",
            "category": "C",
            "severity": "E3",
            "source_rank": "A",
            "headline": "美国宣布新一轮关税措施",
            "detected_at": "2026-03-30T13:30:00Z",
            "is_official_confirmed": True,
            "market_validated": True,
            "has_material_update": True,
            "elapsed_hours": 4,
        }
    )
    fatigue = FatigueCalculator().run(
        {
            "event_id": "ME-C-20260330-001.V1.0",
            "category": "C",
            "lifecycle_state": lifecycle.data["lifecycle_state"],
            "narrative_tags": ["trade_war", "inflation_shock"],
            "category_active_count": 3,
            "tag_active_counts": {"trade_war": 2, "inflation_shock": 3},
            "days_since_last_dead": 5,
        }
    )
    validation = MarketValidator().run(
        {
            "event_id": "ME-C-20260330-001.V1.0",
            "conduction_output": {"conduction_path": ["关税升级"]},
            "price_changes": {"DXY": 1.2, "XLI": -1.8},
            "volume_changes": {"XLI": 2.3},
            "cross_asset_linkage": {"confirmed": True},
            "persistence_minutes": 90,
            "winner_loser_dispersion": {"confirmed": True},
            "market_timestamp": "2026-03-30T15:00:00Z",
        }
    )
    signal = SignalScorer().run(
        {
            "event_id": "ME-C-20260330-001.V1.0",
            "severity": "E3",
            "A0": 30,
            "A-1": 70,
            "A1": validation.data["A1"],
            "A1.5": 60,
            "A0.5": 0,
            "fatigue_final": fatigue.data["fatigue_final"],
            "a_minus_1_discount_factor": fatigue.data["a_minus_1_discount_factor"],
            "correlation": 0.4,
            "is_crowded": False,
            "narrative_mode": "Fact-Driven",
            "policy_intervention": "NONE",
            "base_direction": "long",
            "watch_mode": fatigue.data["watch_mode"],
            "weights_version": "score_v1",
        }
    )

    adapted = adapt_analysis_outputs(
        lifecycle.data,
        fatigue.data,
        validation.data,
        signal.data,
        severity="E3",
        correlation=0.4,
        liquidity_state="GREEN",
        policy_intervention="NONE",
        is_crowded=False,
        narrative_mode="Fact-Driven",
    )

    risk_schema = load_json(ROOT / "schemas" / "risk_gatekeeper.json")
    required = set(risk_schema["input"]["required"])
    if not required.issubset(adapted["risk_input"].keys()):
        missing = sorted(required - set(adapted["risk_input"].keys()))
        raise AssertionError(f"downstream bundle missing fields: {missing}")

    if adapted["execution_context"]["normalized_direction"] != "long":
        raise AssertionError("expected long signal to normalize to long")


def check_direction_semantics() -> None:
    flip_long = normalize_signal_direction("flip_long")
    if flip_long["normalized_direction"] != "flip" or flip_long["target_direction"] != "long":
        raise AssertionError("flip_long normalization is incorrect")

    flip_short = normalize_signal_direction("flip_short")
    if flip_short["normalized_direction"] != "flip" or flip_short["target_direction"] != "short":
        raise AssertionError("flip_short normalization is incorrect")


def main() -> int:
    check_upstream_eventobjectifier_to_lifecycle()
    print("PASS upstream EventObjectifier -> LifecycleManager")
    check_downstream_analysis_bundle_to_risk_input()
    print("PASS downstream analysis_bundle -> RiskGatekeeper input")
    check_direction_semantics()
    print("PASS direction normalization semantics")
    print("\nPASSED 3 interface checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
