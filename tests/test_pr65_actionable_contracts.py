import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from market_validator import MarketValidator
from workflow_runner import WorkflowRunner


def test_market_validator_emits_three_layer_confirmations():
    out = MarketValidator().run(
        {
            "event_id": "ME-X-001",
            "conduction_output": {"conduction_path": ["x", "y"]},
            "price_changes": {"SPY": 1.0},
            "volume_changes": {"SPY": 1.8},
            "cross_asset_linkage": {"confirmed": True},
            "persistence_minutes": 75,
            "winner_loser_dispersion": {"confirmed": True},
            "market_timestamp": "2026-04-17T10:00:00Z",
        }
    )
    assert out.status.value == "success"
    assert out.data["macro_confirmation"] in {"supportive", "neutral", "hostile"}
    assert out.data["sector_confirmation"] in {"strong", "medium", "weak", "none"}
    assert out.data["leader_confirmation"] in {"confirmed", "partial", "unconfirmed", "failed"}
    assert out.data["a1_market_validation"] in {"pass", "partial", "fail"}


def test_workflow_runner_emits_action_card_with_hard_a1_gate():
    runner = WorkflowRunner()
    out = runner.run(
        {
            "event_id": "ME-X-002",
            "A0": 70,
            "A-1": 65,
            "A1": 20,
            "A1.5": 60,
            "A0.5": 0,
            "severity": "E3",
            "fatigue_index": 20,
            "event_state": "Developing",
            "correlation": 0.55,
            "vix": 22,
            "ted": 45,
            "spread_pct": 0.002,
            "account_equity": 100000,
            "entry_price": 100.0,
            "risk_per_share": 2.0,
            "direction": "long",
            "symbol": "SPY",
            "headline": "Sample macro shock",
            "a1_market_validation": "fail",
        }
    )
    card = out["action_card"]
    assert card["a1_market_validation"] == "fail"
    assert card["trade_decision"] in {"observe_only", "avoid"}
    assert card["position_tier"] == "none"
    assert "A1 market validation fail" in card["blockers"]
