import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from execution_modules import RiskGatekeeper


def _make_cfg(tmp_path: Path, params_overrides: dict) -> str:
    base = {
        "modules": {
            "RiskGatekeeper": {
                "params": {
                    "gates": {
                        "G1_liquidity": {"action": "BLOCK_NEW"},
                        "G2_lifecycle": {"action": "FORCE_CLOSE"},
                        "G3_fatigue": {"action": "BLOCK_NEW"},
                        "G4_correlation": {"action": "A15_ADJUST"},
                        "G6_policy": {"action": "DIRECTION_FLIP"},
                    },
                    "g1_liquidity": {
                        "spread_multiplier_threshold": 5,
                        "red_state_value": "RED",
                        "final_action_on_trigger": "BLOCK",
                        "human_confirm_required": True,
                    },
                    "g2_lifecycle": {
                        "blocked_states": ["Dead", "Archived"],
                        "final_action_on_trigger": "FORCE_CLOSE",
                        "human_confirm_required": False,
                    },
                    "g3_fatigue": {
                        "threshold": 85,
                        "final_action_on_trigger": "WATCH",
                        "human_confirm_required": False,
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

    # shallow merge for this test scope
    for k, v in params_overrides.items():
        base["modules"]["RiskGatekeeper"]["params"][k] = v

    path = tmp_path / "risk_cfg.yaml"
    path.write_text(yaml.safe_dump(base, allow_unicode=True), encoding="utf-8")
    return str(path)


@pytest.mark.parametrize(
    "overrides,payload,expected_action,expected_gate",
    [
        (
            {"g1_liquidity": {"spread_multiplier_threshold": 1.2, "red_state_value": "RED", "final_action_on_trigger": "BLOCK", "human_confirm_required": True}},
            {"spread_multiplier": 1.3, "liquidity_state": "GREEN"},
            "BLOCK",
            "G1",
        ),
        (
            {"g2_lifecycle": {"blocked_states": ["Exhaustion"], "final_action_on_trigger": "FORCE_CLOSE", "human_confirm_required": False}},
            {"event_state": "Exhaustion"},
            "FORCE_CLOSE",
            "G2",
        ),
        (
            {"g3_fatigue": {"threshold": 70, "final_action_on_trigger": "WATCH", "human_confirm_required": False}},
            {"fatigue_index": 71},
            "WATCH",
            "G3",
        ),
    ],
)
def test_risk_gatekeeper_g123_configurable(tmp_path, overrides, payload, expected_action, expected_gate):
    cfg = _make_cfg(tmp_path, overrides)
    mod = RiskGatekeeper(config_path=cfg)
    base_payload = {
        "event_state": "Active",
        "fatigue_index": 20,
        "liquidity_state": "GREEN",
        "correlation": 0.5,
        "score": 80,
        "severity": "E3",
        "A1": 70,
        "policy_intervention": "NONE",
        "spread_multiplier": 1.0,
    }
    base_payload.update(payload)
    out = mod.run(base_payload)
    assert out.data["final_action"] == expected_action
    assert out.data["first_triggered_gate"] == expected_gate


def test_risk_gatekeeper_g4_configurable(tmp_path):
    cfg = _make_cfg(
        tmp_path,
        {
            "g4_correlation": {
                "threshold": 0.7,
                "e4_position_multiplier": 0.33,
                "default_position_multiplier": 0.11,
                "warning": "custom-corr-warning",
            }
        },
    )
    mod = RiskGatekeeper(config_path=cfg)

    out_e4 = mod.run(
        {
            "event_state": "Active",
            "fatigue_index": 20,
            "liquidity_state": "GREEN",
            "spread_multiplier": 1.0,
            "correlation": 0.75,
            "score": 80,
            "severity": "E4",
            "A1": 70,
            "policy_intervention": "NONE",
        }
    )
    assert out_e4.data["final_action"] == "EXECUTE"
    assert out_e4.data["position_multiplier"] == pytest.approx(0.264, rel=1e-6)
    assert "custom-corr-warning" in out_e4.data["warnings"]


def test_risk_gatekeeper_g6_configurable(tmp_path):
    cfg = _make_cfg(
        tmp_path,
        {
            "g6_policy": {
                "intervention_value": "EMERGENCY",
                "a1_threshold": 50,
                "direction_on_trigger": "flip_short",
            }
        },
    )
    mod = RiskGatekeeper(config_path=cfg)
    out = mod.run(
        {
            "event_state": "Active",
            "fatigue_index": 20,
            "liquidity_state": "GREEN",
            "spread_multiplier": 1.0,
            "correlation": 0.5,
            "score": 80,
            "severity": "E3",
            "A1": 55,
            "policy_intervention": "EMERGENCY",
        }
    )
    assert out.data["final_action"] == "EXECUTE"
    assert out.data["direction"] == "flip_short"
