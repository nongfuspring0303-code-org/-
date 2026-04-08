import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from conduction_mapper import ConductionMapper


def test_conduction_mapper_uses_chain_template_for_trade_war():
    out = ConductionMapper().run(
        {
            "event_id": "ME-C-TEST-001",
            "category": "C",
            "severity": "E3",
            "headline": "Trade war escalates after new tariffs",
            "summary": "Tariff escalation affects exporters",
            "lifecycle_state": "Active",
            "sector_data": [
                {"sector": "Industrials", "industry": "Industrials"},
                {"sector": "Technology", "industry": "Technology"},
            ],
        }
    )

    assert out.status.value == "success"
    assert out.data["mapping_source"] == "template:tariff_chain"
    assert out.data["conduction_path"]
    assert out.data["sector_impacts"]


def test_conduction_mapper_matches_rate_cut_template():
    out = ConductionMapper().run(
        {
            "event_id": "ME-E-TEST-002",
            "category": "E",
            "severity": "E2",
            "headline": "Fed signals rate cuts ahead",
            "summary": "Policy easing expected",
            "lifecycle_state": "Active",
            "sector_data": [
                {"sector": "Technology", "industry": "Technology"},
                {"sector": "Financial Services", "industry": "Financial Services"},
            ],
        }
    )

    assert out.status.value == "success"
    assert out.data["mapping_source"] == "template:rate_cut_chain"
    assert out.data["sector_impacts"]
