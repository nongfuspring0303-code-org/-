#!/usr/bin/env python3
"""
Analysis-layer integration runner.

Consumes analysis_layer_integration_inputs.yaml and executes the declared
chains end-to-end across the five analysis-layer modules.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

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


def match_partial(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        return all(key in actual and match_partial(actual[key], value) for key, value in expected.items())
    return actual == expected


def assert_expected(actual: Dict[str, Any], expected: Dict[str, Any], chain_id: str, stage: str) -> None:
    for key, value in expected.items():
        if key.endswith("_contains"):
            actual_key = key[:-9]
            actual_value = actual.get(actual_key, [])
            if actual_key in {"conduction_path", "adjustments_applied"}:
                for item in value:
                    if item not in actual_value:
                        raise AssertionError(f"{chain_id}/{stage}: missing {item} in {actual_key}")
            else:
                for expected_item in value:
                    if not any(match_partial(item, expected_item) for item in actual_value):
                        raise AssertionError(f"{chain_id}/{stage}: missing {expected_item} in {actual_key}")
        elif key.endswith("_min"):
            actual_key = key[:-4]
            if actual[actual_key] < value:
                raise AssertionError(f"{chain_id}/{stage}: {actual_key} expected >= {value}, got {actual[actual_key]}")
        else:
            if actual.get(key) != value:
                raise AssertionError(f"{chain_id}/{stage}: {key} expected {value}, got {actual.get(key)}")


def resolve_refs(payload: Any, outputs: Dict[str, Dict[str, Any]]) -> Any:
    if isinstance(payload, dict):
        resolved = {}
        for key, value in payload.items():
            if key.endswith("_ref"):
                resolved[key[:-4]] = resolve_ref_value(value, outputs)
            else:
                resolved[key] = resolve_refs(value, outputs)
        return resolved
    if isinstance(payload, list):
        return [resolve_refs(item, outputs) for item in payload]
    return payload


def resolve_ref_value(ref: str, outputs: Dict[str, Dict[str, Any]]) -> Any:
    chain_id, output_name, *path = ref.split(".")
    current: Any = outputs[chain_id][output_name]
    for token in path:
        current = current[token]
    return current


def run_chain(chain: Dict[str, Any], outputs: Dict[str, Dict[str, Any]]) -> None:
    chain_id = chain["id"]
    outputs[chain_id] = {}

    if "lifecycle_input" in chain:
        result = LifecycleManager().run(chain["lifecycle_input"])
        if result.status != ModuleStatus.SUCCESS:
            raise AssertionError(f"{chain_id}/lifecycle failed: {result.errors}")
        outputs[chain_id]["lifecycle_output"] = result.data
        assert_expected(result.data, chain.get("expected_lifecycle", {}), chain_id, "lifecycle")

    if "fatigue_input" in chain:
        fatigue_input = resolve_refs(chain["fatigue_input"], outputs)
        result = FatigueCalculator().run(fatigue_input)
        if result.status != ModuleStatus.SUCCESS:
            raise AssertionError(f"{chain_id}/fatigue failed: {result.errors}")
        outputs[chain_id]["fatigue_output"] = result.data
        assert_expected(result.data, chain.get("expected_fatigue", {}), chain_id, "fatigue")

    if "conduction_input" in chain:
        conduction_input = resolve_refs(chain["conduction_input"], outputs)
        result = ConductionMapper().run(conduction_input)
        if result.status != ModuleStatus.SUCCESS:
            raise AssertionError(f"{chain_id}/conduction failed: {result.errors}")
        outputs[chain_id]["conduction_output"] = result.data
        assert_expected(result.data, chain.get("expected_conduction", {}), chain_id, "conduction")

    if "validation_input" in chain:
        validation_input = resolve_refs(chain["validation_input"], outputs)
        result = MarketValidator().run(validation_input)
        if result.status != ModuleStatus.SUCCESS:
            raise AssertionError(f"{chain_id}/validation failed: {result.errors}")
        outputs[chain_id]["validation_output"] = result.data
        assert_expected(result.data, chain.get("expected_validation", {}), chain_id, "validation")

    if "signal_input" in chain:
        signal_input = resolve_refs(chain["signal_input"], outputs)
        result = SignalScorer().run(signal_input)
        if result.status != ModuleStatus.SUCCESS:
            raise AssertionError(f"{chain_id}/signal failed: {result.errors}")
        outputs[chain_id]["signal_output"] = result.data
        assert_expected(result.data, chain.get("expected_signal", {}), chain_id, "signal")


def main() -> int:
    suite_path = ROOT / "tests" / "analysis_layer_integration_inputs.yaml"
    payload = yaml.safe_load(suite_path.read_text(encoding="utf-8"))

    outputs: Dict[str, Dict[str, Any]] = {}
    failures: list[tuple[str, str]] = []

    for chain in payload.get("chains", []):
        try:
            run_chain(chain, outputs)
            print(f"PASS {chain['id']} {chain['name']}")
        except Exception as exc:  # noqa: BLE001
            failures.append((chain["id"], str(exc)))
            print(f"FAIL {chain['id']} {exc}")

    if failures:
        print(f"\nFAILED {len(failures)} chains")
        for chain_id, message in failures:
            print(f"- {chain_id}: {message}")
        return 1

    print(f"\nPASSED {len(payload.get('chains', []))} integration chains")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
