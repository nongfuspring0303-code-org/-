#!/usr/bin/env python3
"""
Run core execution scenarios for quick acceptance.
"""

from __future__ import annotations

import json

from workflow_runner import WorkflowRunner


def _base_payload():
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


def main():
    runner = WorkflowRunner()
    scenarios = {
        "S1_EXECUTE_NORMAL": _base_payload(),
        "S2_BLOCK_LIQUIDITY": {**_base_payload(), "vix": 38, "ted": 130, "spread_pct": 0.02},
        "S3_FORCE_CLOSE_DEAD": {**_base_payload(), "event_state": "Dead"},
        "S4_WATCH_FATIGUE": {**_base_payload(), "fatigue_index": 90},
    }

    summary = {}
    for name, payload in scenarios.items():
        out = runner.run(payload)
        summary[name] = {
            "final_action": out["final"]["action"],
            "score": out.get("final", {}).get("score"),
            "liquidity": out.get("liquidity", {}).get("liquidity_state"),
        }

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

