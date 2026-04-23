import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from full_workflow_runner import FullWorkflowRunner


def _last_jsonl(path: Path) -> dict:
    content = path.read_text(encoding="utf-8").strip()
    assert content
    return json.loads(content.splitlines()[-1])


def test_stage3b_c_joint_review_trace_join_not_broken(tmp_path):
    logs_dir = tmp_path / "logs"
    runner = FullWorkflowRunner(audit_dir=str(logs_dir), state_db_path=str(tmp_path / "state.db"))
    payload = {
        "request_id": "REQ-C-S3B-JR-001",
        "batch_id": "BATCH-C-S3B-JR-001",
        "headline": "Fed signals rate-cut path while tech leadership strengthens",
        "source": "https://example.com/stage3b-joint-review",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "vix": 18,
        "vix_change_pct": -3.5,
        "spx_move_pct": 1.1,
        "sector_move_pct": 2.0,
        "account_equity": 100000,
        "entry_price": 100.0,
        "risk_per_share": 2.0,
        "direction": "long",
        "sector_data": [
            {"symbol": "XLK", "sector": "Technology", "industry": "Technology", "change_pct": 1.2},
            {"symbol": "XLF", "sector": "Financial Services", "industry": "Financial Services", "change_pct": 0.8},
        ],
    }

    out = runner.run(payload)
    trace_id = out["execution"]["trace_id"]

    required_files = [
        "raw_news_ingest.jsonl",
        "market_data_provenance.jsonl",
        "decision_gate.jsonl",
        "replay_write.jsonl",
        "replay_join_validation.jsonl",
        "execution_emit.jsonl",
    ]
    for name in required_files:
        assert (logs_dir / name).exists(), name

    raw_record = _last_jsonl(logs_dir / "raw_news_ingest.jsonl")
    gate_record = _last_jsonl(logs_dir / "decision_gate.jsonl")
    replay_record = _last_jsonl(logs_dir / "replay_write.jsonl")
    join_record = _last_jsonl(logs_dir / "replay_join_validation.jsonl")

    assert raw_record["trace_id"] == trace_id
    assert gate_record["trace_id"] == trace_id
    assert replay_record["trace_id"] == trace_id
    assert gate_record["event_hash"] == replay_record["event_hash"] == raw_record["event_hash"]
    assert gate_record["request_id"] == replay_record["request_id"] == "REQ-C-S3B-JR-001"
    assert gate_record["batch_id"] == replay_record["batch_id"] == "BATCH-C-S3B-JR-001"

    assert join_record["orphan_replay_count"] == 0
    assert join_record["replay_primary_key_completeness_ratio"] == 1.0
    assert join_record["validation_status"] == "pass"

    emit_content = (logs_dir / "execution_emit.jsonl").read_text(encoding="utf-8").strip()
    if out["execution"]["final"]["action"] == "EXECUTE":
        emit_record = json.loads(emit_content.splitlines()[-1])
        assert emit_record["trace_id"] == trace_id
        assert emit_record["event_hash"] == raw_record["event_hash"]
    else:
        assert emit_content == ""
