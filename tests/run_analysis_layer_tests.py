#!/usr/bin/env python3
"""
Executable analysis-layer test runner.

Runs YAML-driven test cases for the five analysis-layer modules and a minimal
cross-module chain validation without relying on pytest, so the test suite can
run in the current Python 3.13 environment.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Iterable

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from conduction_mapper import ConductionMapper
from edt_module_base import ModuleStatus
from fatigue_calculator import FatigueCalculator
from lifecycle_manager import LifecycleManager
from market_validator import MarketValidator
from signal_scorer import SignalScorer


MODULES = {
    "lifecycle_manager": LifecycleManager,
    "fatigue_calculator": FatigueCalculator,
    "conduction_mapper": ConductionMapper,
    "market_validator": MarketValidator,
    "signal_scorer": SignalScorer,
}


def load_yaml_cases(path: Path) -> Iterable[Dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    for case in payload.get("cases", []):
        yield {"module": payload["module"], **case}


def match_partial(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        return all(key in actual and match_partial(actual[key], value) for key, value in expected.items())
    return actual == expected


def assert_expected(actual: Dict[str, Any], expected: Dict[str, Any]) -> None:
    for key, value in expected.items():
        if actual.get(key) != value:
            raise AssertionError(f"{key}: expected {value}, got {actual.get(key)}")


def assert_contains_records(actual_items: list[Dict[str, Any]], expected_items: list[Dict[str, Any]]) -> None:
    for expected in expected_items:
        if not any(match_partial(item, expected) for item in actual_items):
            raise AssertionError(f"Missing expected record: {expected}")


def run_case(case: Dict[str, Any]) -> None:
    module_name = case["module"]
    module = MODULES[module_name]()
    result = module.run(case["input"])

    if "expected_error" in case:
        if result.status != ModuleStatus.FAILED:
            raise AssertionError(f"{case['id']}: expected FAILED status, got {result.status}")
        if not result.errors:
            raise AssertionError(f"{case['id']}: expected errors but got none")
        if result.errors[0]["code"] != case["expected_error"]["code"]:
            raise AssertionError(
                f"{case['id']}: expected error {case['expected_error']['code']}, got {result.errors[0]['code']}"
            )
        return

    if result.status != ModuleStatus.SUCCESS:
        raise AssertionError(f"{case['id']}: expected SUCCESS status, got {result.status} with errors {result.errors}")

    actual = result.data
    expected = case["expected"]

    direct_expected = {
        key: value
        for key, value in expected.items()
        if not key.endswith("_contains")
        and not key.endswith("_min")
        and not key.endswith("_max")
        and key not in {"failed_checks_count", "stock_candidates_max_count"}
    }
    assert_expected(actual, direct_expected)

    for key, value in expected.items():
        if key.endswith("_min"):
            actual_key = key[:-4]
            if actual[actual_key] < value:
                raise AssertionError(f"{case['id']}: {actual_key} expected >= {value}, got {actual[actual_key]}")
        elif key.endswith("_max"):
            actual_key = key[:-4]
            if actual[actual_key] > value:
                raise AssertionError(f"{case['id']}: {actual_key} expected <= {value}, got {actual[actual_key]}")
        elif key.endswith("_contains"):
            actual_key = key[:-9]
            if actual_key in {"conduction_path", "failed_checks", "adjustments_applied"}:
                for item in value:
                    if item not in actual.get(actual_key, []):
                        raise AssertionError(f"{case['id']}: {actual_key} missing {item}")
            else:
                assert_contains_records(actual.get(actual_key, []), value)

    if "stock_candidates_max_count" in expected and len(actual.get("stock_candidates", [])) > expected["stock_candidates_max_count"]:
        raise AssertionError(
            f"{case['id']}: stock_candidates expected <= {expected['stock_candidates_max_count']}, got {len(actual.get('stock_candidates', []))}"
        )

    if "failed_checks_count" in expected and len(actual.get("failed_checks", [])) != expected["failed_checks_count"]:
        raise AssertionError(
            f"{case['id']}: failed_checks expected {expected['failed_checks_count']}, got {len(actual.get('failed_checks', []))}"
        )


def run_chain() -> None:
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
    if lifecycle.status != ModuleStatus.SUCCESS or lifecycle.data["lifecycle_state"] != "Active":
        raise AssertionError("analysis_chain: lifecycle stage failed")

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
    if fatigue.status != ModuleStatus.SUCCESS or fatigue.data["fatigue_final"] != 20:
        raise AssertionError("analysis_chain: fatigue stage failed")

    conduction = ConductionMapper().run(
        {
            "event_id": "ME-C-20260330-001.V1.0",
            "category": "C",
            "severity": "E3",
            "headline": "美国宣布新一轮关税措施",
            "summary": "进口成本上升，出口链承压",
            "lifecycle_state": lifecycle.data["lifecycle_state"],
            "narrative_tags": ["trade_war", "inflation_shock"],
            "policy_intervention": "NONE",
        }
    )
    if conduction.status != ModuleStatus.SUCCESS or not conduction.data["conduction_path"]:
        raise AssertionError("analysis_chain: conduction stage failed")

    validation = MarketValidator().run(
        {
            "event_id": "ME-C-20260330-001.V1.0",
            "conduction_output": conduction.data,
            "price_changes": {"DXY": 1.2, "XLI": -1.8},
            "volume_changes": {"XLI": 2.3},
            "cross_asset_linkage": {"confirmed": True},
            "persistence_minutes": 90,
            "winner_loser_dispersion": {"confirmed": True},
            "market_timestamp": "2026-03-30T15:00:00Z",
        }
    )
    if validation.status != ModuleStatus.SUCCESS or validation.data["A1"] < 80:
        raise AssertionError("analysis_chain: validation stage failed")

    scoring = SignalScorer().run(
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
    if scoring.status != ModuleStatus.SUCCESS or scoring.data["score"] < 40 or scoring.data["direction"] != "long":
        raise AssertionError("analysis_chain: scoring stage failed")


def main() -> int:
    case_files = [
        ROOT / "tests" / "test_lifecycle_manager.yaml",
        ROOT / "tests" / "test_fatigue_calculator.yaml",
        ROOT / "tests" / "test_conduction_mapper.yaml",
        ROOT / "tests" / "test_market_validator.yaml",
        ROOT / "tests" / "test_signal_scorer.yaml",
    ]
    cases = [case for path in case_files for case in load_yaml_cases(path)]

    failed = []
    for case in cases:
        try:
            run_case(case)
            print(f"PASS {case['id']} {case['name']}")
        except Exception as exc:  # noqa: BLE001
            failed.append((case["id"], str(exc)))
            print(f"FAIL {case['id']} {exc}")

    try:
        run_chain()
        print("PASS analysis_chain minimal_chain")
    except Exception as exc:  # noqa: BLE001
        failed.append(("analysis_chain", str(exc)))
        print(f"FAIL analysis_chain {exc}")

    if failed:
        print(f"\nFAILED {len(failed)} checks")
        for case_id, message in failed:
            print(f"- {case_id}: {message}")
        return 1

    print(f"\nPASSED {len(cases) + 1} checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
