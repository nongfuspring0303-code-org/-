#!/usr/bin/env python3
"""
LifecycleManager for EDT analysis layer.

This module converts normalized event objects into lifecycle and catalyst
states, and provides a minimal trade eligibility judgment for downstream
fatigue, conduction, and scoring modules.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from edt_module_base import EDTModule, ModuleInput, ModuleOutput, ModuleStatus


class LifecycleManager(EDTModule):
    """Lifecycle state manager for event objects."""

    VALID_STATES = {
        "Detected",
        "Verified",
        "Active",
        "Continuation",
        "Exhaustion",
        "Dead",
        "Archived",
    }

    VALID_CATALYST_STATES = {
        "first_impulse",
        "continuation",
        "exhaustion",
        "dead",
    }

    def __init__(self, config_path: Optional[str] = None):
        super().__init__("LifecycleManager", "1.0.0", config_path)

    def validate_input(self, input_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        required = ["event_id", "category", "severity", "source_rank", "detected_at"]
        for key in required:
            if key not in input_data:
                return False, f"Missing required field: {key}"
        return True, None

    def execute(self, input_data: ModuleInput) -> ModuleOutput:
        raw = input_data.raw_data

        elapsed_hours = float(raw.get("elapsed_hours", 0))
        source_rank = raw.get("source_rank")
        previous_state = raw.get("previous_lifecycle_state")
        contradicted = bool(raw.get("contradicted_by_new_fact", False))
        official = bool(raw.get("is_official_confirmed", False))
        market_validated = bool(raw.get("market_validated", False))
        material_update = bool(raw.get("has_material_update", False))

        if contradicted:
            lifecycle_state = "Dead"
            catalyst_state = "dead"
            trade_eligibility = "blocked"
            holding_horizon = "none"
            reason = "事件被新事实证伪或覆盖"
        elif previous_state in {"Active", "Continuation"} and elapsed_hours >= 48 and not material_update and not market_validated:
            lifecycle_state = "Exhaustion"
            catalyst_state = "exhaustion"
            trade_eligibility = "watch"
            holding_horizon = "none"
            reason = "超过时间窗口且市场边际反应减弱"
        elif source_rank == "C" and not official:
            lifecycle_state = "Detected"
            catalyst_state = "first_impulse"
            trade_eligibility = "watch"
            holding_horizon = "intraday"
            reason = "来源等级不足，未完成升源确认"
        elif official and market_validated and previous_state in {"Active", "Continuation"} and elapsed_hours >= 24 and material_update:
            lifecycle_state = "Continuation"
            catalyst_state = "continuation"
            trade_eligibility = "tradable"
            holding_horizon = "multiweek"
            reason = "事件确认后持续发酵，进入延续阶段"
        elif official and market_validated:
            lifecycle_state = "Active"
            catalyst_state = "first_impulse"
            trade_eligibility = "tradable"
            holding_horizon = "overnight"
            reason = "A级确认且市场验证通过"
        elif official:
            lifecycle_state = "Verified"
            catalyst_state = "first_impulse"
            trade_eligibility = "watch"
            holding_horizon = "intraday"
            reason = "事件已确认，但市场验证尚未完成"
        else:
            lifecycle_state = "Detected"
            catalyst_state = "first_impulse"
            trade_eligibility = "watch"
            holding_horizon = "intraday"
            reason = "事件刚进入系统，等待进一步确认"

        next_review_at = (
            datetime.now(timezone.utc) + timedelta(hours=1 if lifecycle_state in {"Detected", "Verified"} else 4)
        ).isoformat()

        return ModuleOutput(
            status=ModuleStatus.SUCCESS,
            data={
                "event_id": raw["event_id"],
                "lifecycle_state": lifecycle_state,
                "catalyst_state": catalyst_state,
                "trade_eligibility": trade_eligibility,
                "holding_horizon": holding_horizon,
                "transition_reason": reason,
                "next_review_at": next_review_at,
                "needs_manual_review": False,
                "state_version": "lifecycle_v1",
                "reasoning": reason,
                "audit": {
                    "module": self.name,
                    "rule_version": "lifecycle_v1",
                    "decision_trace": [lifecycle_state, catalyst_state, trade_eligibility],
                },
            },
        )


if __name__ == "__main__":
    payload = {
        "event_id": "ME-C-20260330-001.V1.0",
        "category": "C",
        "severity": "E3",
        "source_rank": "A",
        "headline": "美国宣布新一轮关税措施",
        "detected_at": "2026-03-30T13:30:00Z",
        "is_official_confirmed": True,
        "market_validated": True,
        "has_material_update": True,
        "elapsed_hours": 4,
    }
    print(LifecycleManager().run(payload).data)
