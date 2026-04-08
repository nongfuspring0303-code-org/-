import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import run_phase3_pressure_gate as gate


class _DummyResult:
    def __init__(self, data):
        self.data = data


class _FakeIntelPipeline:
    def run(self, payload):
        return {
            "event_object": {
                "event_id": "evt_pressure_001",
                "category": "macro",
                "severity": "E2",
                "headline": payload["headline"],
            }
        }


class _FakeConductionMapper:
    def run(self, payload):
        return _DummyResult(
            {
                "sector_impacts": [
                    {"sector": "科技", "direction": "benefit", "impact_score": 82, "confidence": 90},
                    {"sector": "金融", "direction": "hurt", "impact_score": 0.41, "confidence": 0.72},
                ],
                "conduction_path": ["宏观", "科技", "AI"],
                "confidence": 90,
                "stock_candidates": [{"symbol": "NVDA", "sector": "科技", "direction": "LONG"}],
            }
        )


class _FakeOpportunityScorer:
    def build_opportunity_update(self, payload):
        return {
            "opportunities": [
                {
                    "symbol": "NVDA",
                    "name": "英伟达",
                    "sector": "科技",
                    "signal": "LONG",
                    "entry_zone": {"support": 1120, "resistance": 1180},
                    "risk_flags": [],
                    "final_action": "EXECUTE",
                    "reasoning": "景气延续",
                    "confidence": 0.87,
                }
            ],
            "timestamp": payload["timestamp"],
        }


def test_pressure_gate_accepts_real_items(monkeypatch):
    monkeypatch.setattr(gate, "IntelPipeline", _FakeIntelPipeline)
    monkeypatch.setattr(gate, "ConductionMapper", _FakeConductionMapper)
    monkeypatch.setattr(gate, "OpportunityScorer", _FakeOpportunityScorer)

    items = [
        {
            "headline": "Fed signals policy shift",
            "source_url": "https://example.com/news-1",
            "raw_text": "policy shift",
            "source_type": "rss",
            "timestamp": "2026-04-09T01:02:03Z",
        },
        {
            "headline": "AI spending remains strong",
            "source_url": "https://example.com/news-2",
            "raw_text": "ai spending",
            "source_type": "official",
            "timestamp": "2026-04-09T01:02:04Z",
        },
    ]

    report = gate.build_pressure_report(
        items,
        min_board_coverage=0.5,
        max_p99_ms=5000.0,
        min_throughput=0.1,
    )

    assert report["passed"] is True
    assert report["metrics"]["board_coverage_rate"] >= 0.5
    assert report["metrics"]["latency_p99_sec"] > 0
    assert report["metrics"]["throughput_events_per_sec"] > 0
    assert report["metrics"]["opportunity_count"] == 2


def test_pressure_gate_rejects_fallback_or_test_items(monkeypatch):
    monkeypatch.setattr(gate, "IntelPipeline", _FakeIntelPipeline)
    monkeypatch.setattr(gate, "ConductionMapper", _FakeConductionMapper)
    monkeypatch.setattr(gate, "OpportunityScorer", _FakeOpportunityScorer)

    with pytest.raises(ValueError):
        gate.build_pressure_report(
            [
                {
                    "headline": "Fallback item",
                    "is_test_data": True,
                    "source_type": "fallback",
                    "timestamp": "2026-04-09T01:02:03Z",
                }
            ]
        )

