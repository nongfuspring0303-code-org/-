import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from run_ab_real_push import normalize_event_update, normalize_opportunity_update, normalize_sector_update


def _load_schema(name: str) -> dict:
    path = ROOT / "schemas" / name
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _required(schema: dict) -> set[str]:
    return set(schema.get("required", []))


def test_c_schemas_keep_traces_and_contract_fields_aligned():
    event_schema = _load_schema("event_update.yaml")
    sector_schema = _load_schema("sector_update.yaml")
    opportunity_schema = _load_schema("opportunity_update.yaml")

    for schema in (event_schema, sector_schema, opportunity_schema):
        trace_schema = schema["properties"]["trace_id"]
        patterns = [item["pattern"] for item in trace_schema.get("anyOf", [])]
        assert any(pattern.startswith("^TRC-") for pattern in patterns)
        assert any(pattern.startswith("^REQ-") for pattern in patterns)
        assert any(pattern.startswith("^BATCH-") for pattern in patterns)
        assert any(pattern.startswith("^evt_") for pattern in patterns)

    assert _required(event_schema) >= {"type", "trace_id", "schema_version", "headline", "source", "timestamp"}
    assert _required(sector_schema) >= {"type", "trace_id", "schema_version", "sectors", "timestamp"}
    assert _required(opportunity_schema) >= {"type", "trace_id", "schema_version", "opportunities", "timestamp"}

    assert event_schema["properties"]["type"]["const"] == "event_update"
    assert sector_schema["properties"]["type"]["const"] == "sector_update"
    assert opportunity_schema["properties"]["type"]["const"] == "opportunity_update"

    source_sector = opportunity_schema["properties"]["source_sector_update"]
    assert "request_id" in source_sector["properties"]
    assert "batch_id" in source_sector["properties"]


def test_normalizers_emit_schema_compatible_c_payloads():
    ts = datetime(2026, 4, 9, 1, 2, 3, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    trace_id = "TRC-TEST-001"
    request_id = f"REQ-{trace_id}"
    batch_id = f"BATCH-{trace_id}"
    result = {
        "intel": {
            "event_object": {
                "headline": "Fed signals policy shift",
                "source_url": "https://example.com/news",
                "severity": "E2",
                "detected_at": ts,
            },
            "severity": {"A0": 88},
        },
        "analysis": {
            "signal": {"narrative_mode": "Fact-Driven"},
            "conduction": {
                "sector_impacts": [
                    {"sector": "科技", "direction": "benefit", "impact_score": 82, "confidence": 90},
                    {"sector": "金融", "direction": "hurt", "impact_score": 0.41, "confidence": 0.72},
                ],
                "conduction_path": ["宏观", "科技", "AI"],
                "confidence": 90,
            },
            "opportunity_update": {
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
                "timestamp": ts,
            },
        },
    }

    event_update = normalize_event_update(result, trace_id, request_id, batch_id, ts)
    sector_update = normalize_sector_update(result["analysis"]["conduction"], trace_id, request_id, batch_id, ts)
    opportunity_update = normalize_opportunity_update(result, trace_id, request_id, batch_id, ts)

    assert event_update["type"] == "event_update"
    assert sector_update["type"] == "sector_update"
    assert opportunity_update["type"] == "opportunity_update"

    assert event_update["trace_id"] == trace_id
    assert sector_update["request_id"] == request_id
    assert opportunity_update["batch_id"] == batch_id

    assert event_update["headline"] == "Fed signals policy shift"
    assert sector_update["sectors"]
    assert opportunity_update["opportunities"]

    trace_re = re.compile(r"^(TRC|REQ|BATCH)-[A-Za-z0-9_-]+$|^evt_[A-Za-z0-9_-]+$")
    assert trace_re.match(event_update["trace_id"])
    assert trace_re.match(sector_update["trace_id"])
    assert trace_re.match(opportunity_update["trace_id"])
