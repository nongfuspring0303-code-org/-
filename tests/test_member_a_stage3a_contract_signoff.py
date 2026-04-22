import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from workflow_runner import REPLAY_JOIN_REQUIRED_KEYS, WorkflowRunner


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return []
    return [json.loads(line) for line in content.splitlines() if line.strip()]


def _base_payload() -> dict:
    return {
        "request_id": "REQ-A-S3A-001",
        "batch_id": "BATCH-A-S3A-001",
        "event_hash": "EVHASH-A-S3A-001",
        "A0": 30,
        "A-1": 70,
        "A1": 78,
        "A1.5": 60,
        "A0.5": 0,
        "severity": "E3",
        "fatigue_index": 45,
        "event_state": "Active",
        "correlation": 0.5,
        "vix": 18,
        "ted": 40,
        "spread_pct": 0.002,
        "account_equity": 100000,
        "entry_price": 100.0,
        "risk_per_share": 2.0,
        "direction": "long",
        "symbol": "SPY",
        "has_opportunity": True,
        "market_data_present": True,
        "market_data_source": "payload_direct",
        "market_data_stale": False,
        "market_data_default_used": False,
        "market_data_fallback_used": False,
        "tradeable": True,
    }


def test_stage3a_a_required_keys_contract_frozen():
    assert REPLAY_JOIN_REQUIRED_KEYS == (
        "event_trace_id",
        "request_id",
        "batch_id",
        "event_hash",
    )


def test_stage3a_a_tradeable_false_blocks_execute_and_keeps_join_evidence(tmp_path):
    logs_dir = tmp_path / "logs"
    runner = WorkflowRunner(
        request_store_path=str(tmp_path / "seen_ids_a_s3a_1.txt"),
        audit_dir=str(logs_dir),
    )
    payload = _base_payload()
    payload["tradeable"] = False

    out = runner.run(payload)

    assert out["final"]["action"] != "EXECUTE"
    assert "tradeable_false" in out["final"]["reason"]

    emit_records = _read_jsonl(logs_dir / "execution_emit.jsonl")
    assert emit_records == []

    validation = out["replay_join_validation"]
    assert validation["replay_primary_key_complete"] is True
    assert validation["orphan_replay_count"] == 0
    assert validation["execution_emit_expected"] is False
    assert validation["validation_status"] == "pass"
