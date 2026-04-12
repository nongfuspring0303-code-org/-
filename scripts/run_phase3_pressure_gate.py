#!/usr/bin/env python3
"""
Phase-3 real pressure gate.

Uses real news ingestion items when available and refuses to pass on fallback
or test data. The gate checks:
1) board coverage on real items
2) p99 latency for the A->B opportunity path
3) throughput for real-item replay on the local pipeline
"""

from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import quantiles
from typing import Any, Dict, List, Sequence
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ai_event_intel import NewsIngestion
from conduction_mapper import ConductionMapper
from phase3_evidence_ledger import Phase3EvidenceLedger
from intel_modules import IntelPipeline
from opportunity_score import OpportunityScorer


@dataclass
class PressureReport:
    total_items: int
    real_items: int
    board_coverage_rate: float
    latency_p99_sec: float
    throughput_events_per_sec: float
    passed: bool


def _load_items_from_file(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"input file not found: {path}")
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        payload = json.loads(text)
    else:
        import yaml

        payload = yaml.safe_load(text)
    if isinstance(payload, dict) and "items" in payload:
        payload = payload["items"]
    if not isinstance(payload, list):
        raise ValueError("input file must contain a list of news items")
    return [item for item in payload if isinstance(item, dict)]


def _is_real_item(item: Dict[str, Any]) -> bool:
    return not bool(item.get("is_test_data")) and str(item.get("source_type", "")).lower() != "fallback"


def _news_payload(item: Dict[str, Any]) -> Dict[str, Any]:
    source = item.get("source_url") or item.get("source") or ""
    return {
        "headline": item.get("headline", ""),
        "source": source,
        "timestamp": item.get("timestamp"),
        "raw_text": item.get("raw_text", item.get("headline", "")),
        "sequence": 1,
        "vix": item.get("vix"),
        "vix_change_pct": item.get("vix_change_pct"),
        "spx_move_pct": item.get("spx_move_pct"),
        "sector_move_pct": item.get("sector_move_pct"),
    }


def _latency_p99(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    if len(values) < 2:
        return float(values[0])
    q = quantiles(list(values), n=100)
    return float(q[98])


def _normalize_ratio(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if numeric > 1.0:
        numeric /= 100.0
    return max(0.0, min(1.0, numeric))


def build_pressure_report(
    items: List[Dict[str, Any]],
    *,
    min_board_coverage: float = 0.9,
    max_p99_ms: float = 1000.0,
    min_throughput: float = 100.0,
) -> Dict[str, Any]:
    real_items = [item for item in items if _is_real_item(item)]
    if not real_items:
        raise ValueError("no real news items supplied")

    pipeline = IntelPipeline()
    conduction = ConductionMapper()
    scorer = OpportunityScorer()

    latencies: List[float] = []
    board_hits = 0
    opportunities_total = 0

    started = time.perf_counter()
    for item in real_items:
        item_start = time.perf_counter()
        intel_out = pipeline.run(_news_payload(item))
        event_object = intel_out["event_object"]

        conduction_out = conduction.run(
            {
                "event_id": event_object["event_id"],
                "category": event_object["category"],
                "severity": event_object["severity"],
                "headline": event_object["headline"],
                "summary": item.get("raw_text", event_object["headline"]),
                "lifecycle_state": "Active",
                "narrative_tags": [item.get("source_type", "real_news")],
                "policy_intervention": "NONE",
                "sector_data": item.get("sector_data", []),
            }
        ).data

        sectors = []
        for impact in conduction_out.get("sector_impacts", []):
            sectors.append(
                {
                    "name": impact.get("sector", "未知板块"),
                    "direction": "LONG" if str(impact.get("direction", "")).lower() in {"benefit", "long"} else "SHORT",
                    "impact_score": _normalize_ratio(impact.get("impact_score", conduction_out.get("confidence", 0))),
                    "confidence": _normalize_ratio(impact.get("confidence", conduction_out.get("confidence", 0))),
                }
            )

        opportunity_update = scorer.build_opportunity_update(
            {
                "trace_id": event_object["event_id"],
                "schema_version": "v1.0",
                "sectors": sectors,
                "stock_candidates": conduction_out.get("stock_candidates", []),
                "timestamp": item.get("timestamp"),
            }
        )

        elapsed = time.perf_counter() - item_start
        latencies.append(elapsed)
        if conduction_out.get("sector_impacts") and opportunity_update.get("opportunities"):
            board_hits += 1
        opportunities_total += len(opportunity_update.get("opportunities", []))

    elapsed_total = time.perf_counter() - started
    total = len(real_items)
    coverage_rate = board_hits / total if total else 0.0
    p99_sec = _latency_p99(latencies)
    throughput = total / elapsed_total if elapsed_total > 0 else math.inf

    report = PressureReport(
        total_items=total,
        real_items=total,
        board_coverage_rate=coverage_rate,
        latency_p99_sec=p99_sec,
        throughput_events_per_sec=throughput,
        passed=(
            coverage_rate >= min_board_coverage
            and (p99_sec * 1000.0) <= max_p99_ms
            and throughput >= min_throughput
            and opportunities_total > 0
        ),
    )

    return {
        "total_items": report.total_items,
        "real_items": report.real_items,
        "metrics": {
            "board_coverage_rate": round(report.board_coverage_rate, 4),
            "latency_p99_sec": round(report.latency_p99_sec, 6),
            "throughput_events_per_sec": round(report.throughput_events_per_sec, 2),
            "opportunity_count": opportunities_total,
        },
        "thresholds": {
            "board_coverage_rate": f">={min_board_coverage}",
            "latency_p99_ms": f"<={max_p99_ms}",
            "throughput_events_per_sec": f">={min_throughput}",
        },
        "passed": report.passed,
    }


def _fetch_live_items(samples: int) -> List[Dict[str, Any]]:
    out = NewsIngestion().run({"max_items": samples})
    items = out.data.get("items", [])
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the phase-3 real pressure gate")
    parser.add_argument("--samples", type=int, default=10, help="Number of real items to try to fetch")
    parser.add_argument("--min-board-coverage", type=float, default=0.9)
    parser.add_argument("--max-p99-ms", type=float, default=1000.0)
    parser.add_argument("--min-throughput", type=float, default=100.0)
    parser.add_argument("--input-json", type=str, default=None, help="Replay a captured real-news JSON/YAML list")
    parser.add_argument("--audit-dir", type=str, default=None, help="Directory for evidence ledger output")
    args = parser.parse_args()

    if args.input_json:
        items = _load_items_from_file(Path(args.input_json))
    else:
        items = _fetch_live_items(args.samples)

    if not items:
        raise SystemExit("no news items available for pressure gate")

    if any(not _is_real_item(item) for item in items):
        raise SystemExit("pressure gate requires real items only; fallback/test data detected")

    report = build_pressure_report(
        items,
        min_board_coverage=args.min_board_coverage,
        max_p99_ms=args.max_p99_ms,
        min_throughput=args.min_throughput,
    )

    ledger = Phase3EvidenceLedger(args.audit_dir)
    ledger.append_pressure_run(
        report,
        source_kind="replay" if args.input_json else "live",
        metadata={
            "input_mode": "replay" if args.input_json else "live_fetch",
            "samples": args.samples,
        },
    )

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
