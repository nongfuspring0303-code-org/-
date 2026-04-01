import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from edt_module_base import SignalScorer


def test_signal_scorer_analysis_chain_output():
    scorer = SignalScorer()
    out = scorer.run(
        {
            "A0": 30,
            "A-1": 70,
            "A1": 78,
            "A1.5": 60,
            "A0.5": 0,
            "severity": "E3",
            "fatigue_index": 45,
            "correlation": 0.5,
        }
    )
    assert out.status.value == "success"
    assert out.data["score_tier"] in ("G1", "G2", "G3", "G5")
    assert -100 <= out.data["score"] <= 100

