#!/usr/bin/env python3
"""
Phase-3 evidence ledger.

This module persists pressure-gate runs into an append-only JSONL ledger and
produces rolling window statistics that can be consumed by health checks and
project audits.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List


def _root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def _default_log_dir() -> Path:
    return _root_dir() / "logs"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_ts(value: str) -> datetime:
    text = str(value or "").strip().replace("Z", "+00:00")
    return datetime.fromisoformat(text)


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    ordered = sorted(values)
    index = int(round((pct / 100.0) * (len(ordered) - 1)))
    index = max(0, min(len(ordered) - 1, index))
    return float(ordered[index])


@dataclass
class Phase3EvidenceRecord:
    kind: str
    source_kind: str
    created_at: str
    total_items: int
    real_items: int
    board_coverage_rate: float
    latency_p99_sec: float
    throughput_events_per_sec: float
    opportunity_count: int
    passed: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


class Phase3EvidenceLedger:
    def __init__(self, audit_dir: str | None = None):
        self.audit_dir = Path(audit_dir) if audit_dir else _default_log_dir()
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_file = self.audit_dir / "phase3_evidence.jsonl"
        self.summary_file = self.audit_dir / "phase3_evidence_summary.json"
        self.report_file = self.audit_dir / "phase3_evidence_report.json"

    def append_pressure_run(
        self,
        report: Dict[str, Any],
        *,
        source_kind: str,
        metadata: Dict[str, Any] | None = None,
    ) -> Phase3EvidenceRecord:
        metrics = report.get("metrics", {})
        record = Phase3EvidenceRecord(
            kind="pressure_gate",
            source_kind=source_kind,
            created_at=_now_iso(),
            total_items=int(report.get("total_items", 0) or 0),
            real_items=int(report.get("real_items", 0) or 0),
            board_coverage_rate=float(metrics.get("board_coverage_rate", 0.0) or 0.0),
            latency_p99_sec=float(metrics.get("latency_p99_sec", 0.0) or 0.0),
            throughput_events_per_sec=float(metrics.get("throughput_events_per_sec", 0.0) or 0.0),
            opportunity_count=int(metrics.get("opportunity_count", 0) or 0),
            passed=bool(report.get("passed")),
            metadata=metadata or {},
        )
        with open(self.ledger_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
        self.write_summary()
        return record

    def _load_records(self, window_days: int = 30) -> List[Dict[str, Any]]:
        if not self.ledger_file.exists():
            return []
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
        rows: List[Dict[str, Any]] = []
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                try:
                    if _parse_ts(row.get("created_at", "")) < cutoff:
                        continue
                except Exception:
                    continue
                rows.append(row)
        return rows

    def summarize(self, window_days: int = 30) -> Dict[str, Any]:
        records = self._load_records(window_days=window_days)
        total_runs = len(records)
        live_run_count = sum(1 for row in records if row.get("source_kind") == "live")
        replay_run_count = sum(1 for row in records if row.get("source_kind") == "replay")
        passed_run_count = sum(1 for row in records if row.get("passed"))
        real_item_total = sum(int(row.get("real_items", 0) or 0) for row in records)

        coverage_values = [float(row.get("board_coverage_rate", 0.0) or 0.0) for row in records]
        latency_values = [float(row.get("latency_p99_sec", 0.0) or 0.0) for row in records]
        throughput_values = [float(row.get("throughput_events_per_sec", 0.0) or 0.0) for row in records]

        summary = {
            "schema_version": "v1.0",
            "window_days": window_days,
            "generated_at": _now_iso(),
            "has_evidence": total_runs > 0,
            "real_flow_evidence": live_run_count > 0,
            "total_runs": total_runs,
            "live_run_count": live_run_count,
            "replay_run_count": replay_run_count,
            "passed_run_count": passed_run_count,
            "pass_rate": round(passed_run_count / total_runs, 4) if total_runs else 0.0,
            "real_item_total": real_item_total,
            "board_coverage_mean": round(mean(coverage_values), 4) if coverage_values else 0.0,
            "board_coverage_p99": round(_percentile(coverage_values, 99), 4),
            "latency_p99_sec_mean": round(mean(latency_values), 6) if latency_values else 0.0,
            "latency_p99_sec_p99": round(_percentile(latency_values, 99), 6),
            "throughput_events_per_sec_mean": round(mean(throughput_values), 2) if throughput_values else 0.0,
            "throughput_events_per_sec_p99": round(_percentile(throughput_values, 99), 2),
            "last_record": records[-1] if records else {},
        }
        return summary

    def write_summary(self, window_days: int = 30) -> Dict[str, Any]:
        summary = self.summarize(window_days=window_days)
        with open(self.summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        self.write_report(window_days=window_days, summary=summary)
        return summary

    def read_summary(self) -> Dict[str, Any]:
        if not self.summary_file.exists():
            return self.write_summary()
        try:
            return json.loads(self.summary_file.read_text(encoding="utf-8"))
        except Exception:
            return self.write_summary()

    def build_report(self, window_days: int = 30, summary: Dict[str, Any] | None = None) -> Dict[str, Any]:
        summary = summary or self.summarize(window_days=window_days)
        return {
            "schema_version": "v1.0",
            "window_days": window_days,
            "generated_at": _now_iso(),
            "summary": summary,
            "live_vs_replay": {
                "live_run_count": summary.get("live_run_count", 0),
                "replay_run_count": summary.get("replay_run_count", 0),
                "real_flow_evidence": summary.get("real_flow_evidence", False),
            },
            "recent_last_record": summary.get("last_record", {}),
        }

    def write_report(self, window_days: int = 30, summary: Dict[str, Any] | None = None) -> Dict[str, Any]:
        report = self.build_report(window_days=window_days, summary=summary)
        with open(self.report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return report

    def read_report(self) -> Dict[str, Any]:
        if not self.report_file.exists():
            return self.write_report()
        try:
            return json.loads(self.report_file.read_text(encoding="utf-8"))
        except Exception:
            return self.write_report()


if __name__ == "__main__":
    ledger = Phase3EvidenceLedger()
    print(json.dumps(ledger.read_summary(), ensure_ascii=False, indent=2))
