import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from edt_module_base import ModuleStatus
from execution_modules import RiskGatekeeper


def _write_cfg(tmp_path: Path, cfg: dict) -> str:
    path = tmp_path / "risk_cfg_guardrails.yaml"
    path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return str(path)


def _base_payload() -> dict:
    return {
        "event_state": "Active",
        "fatigue_index": 20,
        "liquidity_state": "GREEN",
        "spread_multiplier": 1.0,
        "correlation": 0.5,
        "score": 80,
        "severity": "E3",
        "A1": 70,
        "policy_intervention": "NONE",
    }


def test_missing_risk_gatekeeper_params_falls_back_to_defaults(tmp_path):
    cfg = {
        "modules": {
            # 故意不提供 RiskGatekeeper.params，验证默认回退不崩
            "RiskGatekeeper": {},
            "PositionSizer": {
                "params": {
                    "tiers": {
                        "G1": {"score_range": [80, 100], "position_pct": 0.8},
                        "G2": {"score_range": [60, 80], "position_pct": 0.5},
                        "G3": {"score_range": [40, 60], "position_pct": 0.2},
                        "G4": {"score_range": [20, 40], "position_pct": 0.0},
                        "G5": {"score_range": [0, 20], "position_pct": 0.0},
                    }
                }
            },
        }
    }
    mod = RiskGatekeeper(config_path=_write_cfg(tmp_path, cfg))
    out = mod.run(_base_payload())
    assert out.status == ModuleStatus.SUCCESS
    assert out.data["final_action"] == "EXECUTE"


def test_invalid_numeric_threshold_fails_fast(tmp_path):
    cfg = {
        "modules": {
            "RiskGatekeeper": {
                "params": {
                    "gates": {"G4_correlation": {"action": "A15_ADJUST"}},
                    "g4_correlation": {
                        # 非法值：应触发执行失败，而不是静默继续
                        "threshold": "not-a-number",
                        "e4_position_multiplier": 0.5,
                        "default_position_multiplier": 0.0,
                        "warning": "x",
                    },
                }
            },
            "PositionSizer": {
                "params": {
                    "tiers": {
                        "G1": {"score_range": [80, 100], "position_pct": 0.8},
                    }
                }
            },
        }
    }
    mod = RiskGatekeeper(config_path=_write_cfg(tmp_path, cfg))
    payload = _base_payload()
    payload["correlation"] = 0.9
    out = mod.run(payload)
    assert out.status == ModuleStatus.FAILED
    assert out.errors
    assert out.errors[0]["code"] == "EXECUTION_ERROR"


def test_missing_tiers_results_in_watch_not_crash(tmp_path):
    cfg = {
        "modules": {
            "RiskGatekeeper": {
                "params": {
                    "gates": {
                        "G4_correlation": {"action": "A15_ADJUST"},
                        "G6_policy": {"action": "DIRECTION_FLIP"},
                    },
                    "g4_correlation": {
                        "threshold": 0.8,
                        "e4_position_multiplier": 0.5,
                        "default_position_multiplier": 0.0,
                        "warning": "Correlation collapse mode.",
                    },
                    "g6_policy": {
                        "intervention_value": "STRONG",
                        "a1_threshold": 60,
                        "direction_on_trigger": "flip",
                    },
                }
            },
            # 故意不给 PositionSizer.tiers
            "PositionSizer": {"params": {}},
        }
    }
    mod = RiskGatekeeper(config_path=_write_cfg(tmp_path, cfg))
    out = mod.run(_base_payload())
    assert out.status == ModuleStatus.SUCCESS
    assert out.data["final_action"] == "WATCH"
    assert out.data["position_multiplier"] == 0.0
