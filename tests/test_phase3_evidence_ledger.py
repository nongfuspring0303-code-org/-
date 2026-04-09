import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from phase3_evidence_ledger import Phase3EvidenceLedger


def test_phase3_evidence_ledger_records_and_summarizes(tmp_path):
    ledger = Phase3EvidenceLedger(audit_dir=str(tmp_path))
    report = {
        "total_items": 2,
        "real_items": 2,
        "metrics": {
            "board_coverage_rate": 1.0,
            "latency_p99_sec": 0.01,
            "throughput_events_per_sec": 101.5,
            "opportunity_count": 2,
        },
        "passed": True,
    }

    ledger.append_pressure_run(report, source_kind="live", metadata={"input_mode": "live_fetch"})
    ledger.append_pressure_run(report, source_kind="replay", metadata={"input_mode": "replay"})

    summary = ledger.read_summary()
    assert summary["total_runs"] == 2
    assert summary["live_run_count"] == 1
    assert summary["replay_run_count"] == 1
    assert summary["real_item_total"] == 4
    assert summary["has_evidence"] is True
    assert summary["real_flow_evidence"] is True
    assert summary["pass_rate"] == 1.0
    assert summary["board_coverage_p99"] == 1.0
    assert (tmp_path / "phase3_evidence_report.json").exists()
    report_data = ledger.read_report()
    assert report_data["summary"]["total_runs"] == 2
    assert report_data["live_vs_replay"]["live_run_count"] == 1
