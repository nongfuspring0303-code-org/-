import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from signal_scorer import SignalScorer


def test_signal_scorer_reads_weights_from_config(tmp_path):
    config_path = tmp_path / "signal_scorer.yaml"
    config_path.write_text(
        """
modules:
  SignalScorer:
    params:
      weights:
        A0: 1.0
        A-1: 0.0
        A1: 0.0
        A1.5: 0.0
        A0.5: 0.0
""".strip()
        + "\n",
        encoding="utf-8",
    )

    scorer = SignalScorer(config_path=str(config_path))
    out = scorer.run(
        {
            "event_id": "evt-1",
            "severity": "E3",
            "A0": 12,
            "A-1": 0,
            "A1": 0,
            "A1.5": 0,
            "A0.5": 0,
            "fatigue_final": 10,
            "correlation": 0.2,
            "watch_mode": False,
            "base_direction": "long",
            "policy_intervention": "NONE",
            "narrative_mode": "Fact-Driven",
            "is_crowded": False,
            "weights_version": "score_v1",
        }
    ).data

    assert out["weight_details"]["w_A0"] == 1.0
    assert out["score_raw"] == 12.0

