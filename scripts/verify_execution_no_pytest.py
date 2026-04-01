#!/usr/bin/env python3
"""
Fallback verifier when pytest is unavailable.
Runs core assertions with plain Python.
"""

from __future__ import annotations

from execution_modules import ExitManager, LiquidityChecker, PositionSizer, RiskGatekeeper
from workflow_runner import WorkflowRunner


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    liq = LiquidityChecker().run({"vix": 35, "ted": 120, "correlation": 0.85, "spread_pct": 0.02})
    _assert(liq.data["liquidity_state"] == "RED", "LiquidityChecker RED case failed")

    gate = RiskGatekeeper().run(
        {
            "event_state": "Dead",
            "fatigue_index": 20,
            "liquidity_state": "GREEN",
            "correlation": 0.5,
            "score": 80,
            "severity": "E3",
            "A1": 70,
        }
    )
    _assert(gate.data["final_action"] == "FORCE_CLOSE", "RiskGatekeeper dead case failed")

    size = PositionSizer().run(
        {
            "score": 72,
            "liquidity_state": "GREEN",
            "risk_gate_multiplier": 1.0,
            "account_equity": 100000,
        }
    )
    _assert(size.data["score_tier"] == "G2", "PositionSizer tier case failed")
    _assert(size.data["final_notional"] == 50000.0, "PositionSizer notional case failed")

    ex = ExitManager().run({"entry_price": 100.0, "risk_per_share": 2.0, "direction": "long"})
    _assert(len(ex.data["take_profit_levels"]) == 3, "ExitManager TP count failed")
    _assert(ex.data["hard_stop"] == 96.0, "ExitManager hard stop failed")

    out = WorkflowRunner().run(
        {
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
    )
    _assert(out["final"]["action"] in ("EXECUTE", "WATCH", "BLOCK", "FORCE_CLOSE"), "Workflow output invalid")
    print("OK: execution-layer fallback verification passed")


if __name__ == "__main__":
    main()

