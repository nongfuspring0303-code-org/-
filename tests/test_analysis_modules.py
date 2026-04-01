import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from analysis_modules import AnalysisPipeline, ConductionMapper, FatigueCalculator, LifecycleManager, MarketValidator


def test_lifecycle_transition_detected_to_verified():
    out = LifecycleManager().run({"event_state": "Detected", "verified": True})
    assert out.data["lifecycle_state"] == "Verified"


def test_fatigue_final_max_rule():
    out = FatigueCalculator().run({"category_event_count": 6, "tag_event_count": 3})
    assert out.data["fatigue_final"] == max(out.data["fatigue_category"], out.data["fatigue_tag"])


def test_conduction_mapping_category_c():
    out = ConductionMapper().run({"category": "C", "severity": "E3", "candidate_stocks": ["A", "B", "C", "D"]})
    assert "macro" in out.data["conduction"]
    assert len(out.data["conduction"]["stock"]) == 3


def test_market_validator_generates_a1():
    out = MarketValidator().run(
        {
            "price_reaction": 80,
            "volume": 75,
            "correlation": 70,
            "persistence": 65,
            "divergence": 60,
        }
    )
    assert 0 <= out.data["A1"] <= 100
    assert out.data["validation_tier"] in ("strong", "medium", "weak")


def test_analysis_pipeline_end_to_end():
    out = AnalysisPipeline().run(
        {
            "event_state": "Detected",
            "verified": True,
            "elapsed_hours": 2,
            "category_event_count": 4,
            "tag_event_count": 3,
            "category": "C",
            "severity": "E3",
            "candidate_stocks": ["XLF", "JPM", "GS"],
            "price_reaction": 80,
            "volume": 75,
            "correlation": 70,
            "persistence": 65,
            "divergence": 60,
            "A0": 30,
            "A-1": 70,
            "A1.5": 60,
            "A0.5": 0,
        }
    )
    assert "signal" in out
    assert "score" in out["signal"]

