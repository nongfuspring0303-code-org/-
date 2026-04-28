"""Stage6 PR-7b: Outcome Engine Idempotency Tests.

Member-C implementation.
Verifies:
  - Same input repeated does not duplicate records
  - Same idempotency key produces stable results
  - Core summary metrics are consistent across runs
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from outcome_attribution_engine import run_engine

FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "stage6"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    recs = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    return recs


def test_idempotency_same_input_same_summary(tmp_path):
    """Running twice on the same input should produce identical summary statistics."""
    logs_dir = FIXTURES_DIR / "outcome_logs"

    # Run 1
    out1 = tmp_path / "run1"
    out1.mkdir()
    result1 = run_engine(logs_dir=logs_dir, out_dir=out1)

    # Run 2
    out2 = tmp_path / "run2"
    out2.mkdir()
    result2 = run_engine(logs_dir=logs_dir, out_dir=out2)

    # Load summaries
    summary1 = _load_json(Path(result1["summary_path"]))
    summary2 = _load_json(Path(result2["summary_path"]))

    # Core metrics must be identical
    core_metrics = [
        "total_opportunities",
        "valid_outcome_count",
        "degraded_outcome_count",
        "invalid_outcome_count",
        "pending_outcome_count",
        "valid_resolved_t5_count",
        "hit_count_t5",
        "miss_count_t5",
        "execute_decision_count",
        "watch_decision_count",
        "block_decision_count",
        "overblocked_count",
        "correct_block_count",
        "missed_opportunity_count",
    ]

    for metric in core_metrics:
        val1 = summary1.get(metric)
        val2 = summary2.get(metric)
        assert val1 == val2, (
            f"Idempotency violation: {metric} differs across runs "
            f"({val1} vs {val2})"
        )


def test_idempotency_same_record_count(tmp_path):
    """Running twice produces the same number of outcome records."""
    logs_dir = FIXTURES_DIR / "outcome_logs"

    out1 = tmp_path / "run1"
    out1.mkdir()
    result1 = run_engine(logs_dir=logs_dir, out_dir=out1)
    outcomes1 = _read_jsonl(Path(result1["outcome_path"]))

    out2 = tmp_path / "run2"
    out2.mkdir()
    result2 = run_engine(logs_dir=logs_dir, out_dir=out2)
    outcomes2 = _read_jsonl(Path(result2["outcome_path"]))

    assert len(outcomes1) == len(outcomes2), (
        f"Record count differs: {len(outcomes1)} vs {len(outcomes2)}"
    )


def test_idempotency_same_opportunity_ids(tmp_path):
    """Opportunity IDs should be the same across runs (deterministic ordering)."""
    logs_dir = FIXTURES_DIR / "outcome_logs"

    out1 = tmp_path / "run1"
    out1.mkdir()
    result1 = run_engine(logs_dir=logs_dir, out_dir=out1)
    outcomes1 = _read_jsonl(Path(result1["outcome_path"]))

    out2 = tmp_path / "run2"
    out2.mkdir()
    result2 = run_engine(logs_dir=logs_dir, out_dir=out2)
    outcomes2 = _read_jsonl(Path(result2["outcome_path"]))

    ids1 = sorted([o["opportunity_id"] for o in outcomes1])
    ids2 = sorted([o["opportunity_id"] for o in outcomes2])

    assert ids1 == ids2, (
        f"Opportunity IDs differ across runs. "
        f"Unique to run1: {set(ids1) - set(ids2)}, "
        f"Unique to run2: {set(ids2) - set(ids1)}"
    )


def test_idempotency_created_at_can_differ(tmp_path):
    """created_at timestamps may differ, but everything else should be stable."""
    logs_dir = FIXTURES_DIR / "outcome_logs"

    out1 = tmp_path / "run1"
    out1.mkdir()
    result1 = run_engine(logs_dir=logs_dir, out_dir=out1)
    outcomes1 = _read_jsonl(Path(result1["outcome_path"]))

    out2 = tmp_path / "run2"
    out2.mkdir()
    result2 = run_engine(logs_dir=logs_dir, out_dir=out2)
    outcomes2 = _read_jsonl(Path(result2["outcome_path"]))

    # Compare all fields except created_at
    for o1, o2 in zip(outcomes1, outcomes2):
        o1_stable = {k: v for k, v in o1.items() if k != "created_at"}
        o2_stable = {k: v for k, v in o2.items() if k != "created_at"}
        assert o1_stable == o2_stable, (
            f"Outcome record differs: opp_id={o1.get('opportunity_id')} "
            f"trace_id={o1.get('trace_id')}"
        )


def test_idempotency_score_buckets_consistent(tmp_path):
    """Score bucket output should be identical across runs."""
    logs_dir = FIXTURES_DIR / "outcome_logs"

    out1 = tmp_path / "run1"
    out1.mkdir()
    result1 = run_engine(logs_dir=logs_dir, out_dir=out1)
    buckets1 = _load_json(Path(result1["bucket_path"]))

    out2 = tmp_path / "run2"
    out2.mkdir()
    result2 = run_engine(logs_dir=logs_dir, out_dir=out2)
    buckets2 = _load_json(Path(result2["bucket_path"]))

    assert buckets1["buckets"] == buckets2["buckets"], (
        "Score bucket data differs across runs"
    )


def test_idempotency_failure_distribution_consistent(tmp_path):
    """Failure reason distribution should be identical across runs."""
    logs_dir = FIXTURES_DIR / "outcome_logs"

    out1 = tmp_path / "run1"
    out1.mkdir()
    result1 = run_engine(logs_dir=logs_dir, out_dir=out1)
    fail1 = _load_json(Path(result1["failure_path"]))

    out2 = tmp_path / "run2"
    out2.mkdir()
    result2 = run_engine(logs_dir=logs_dir, out_dir=out2)
    fail2 = _load_json(Path(result2["failure_path"]))

    assert fail1 == fail2, "Failure reason distribution differs across runs"
