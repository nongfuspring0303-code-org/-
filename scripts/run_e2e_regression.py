#!/usr/bin/env python3
"""
Run E2E regression scenarios without pytest.
"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from workflow_runner import WorkflowRunner


def _base():
    return {
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
    }


def main() -> None:
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        runner = WorkflowRunner(
            request_store_path=str(tmp_path / "seen_ids.txt"),
            audit_dir=str(tmp_path / "logs"),
        )
        scenarios = {
            "EXECUTE": _base(),
            "BLOCK": {**_base(), "vix": 40, "ted": 130, "spread_pct": 0.02},
            "FORCE_CLOSE": {**_base(), "event_state": "Dead"},
            "WATCH": {**_base(), "fatigue_index": 90},
            "PENDING_CONFIRM": {**_base(), "require_human_confirm": True, "human_confirmed": False},
        }

        summary = {}
        for name, payload in scenarios.items():
            out = runner.run(payload)
            summary[name] = out["final"]["action"]

        p = {**_base(), "request_id": "REQ-REG-001"}
        first = runner.run(p)["final"]["action"]
        second = runner.run(p)["final"]["action"]
        summary["IDEMPOTENT_FIRST"] = first
        summary["IDEMPOTENT_SECOND"] = second
        print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

