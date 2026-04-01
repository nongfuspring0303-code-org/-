#!/usr/bin/env python3
"""
FatigueCalculator for EDT analysis layer.

This module calculates category fatigue, narrative-tag fatigue, and the final
fatigue constraint used by scoring and execution decisions.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from edt_module_base import EDTModule, ModuleInput, ModuleOutput, ModuleStatus


class FatigueCalculator(EDTModule):
    """Narrative fatigue calculator."""

    def __init__(self, config_path: Optional[str] = None):
        super().__init__("FatigueCalculator", "1.0.0", config_path)

    def validate_input(self, input_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        required = ["event_id", "category", "lifecycle_state"]
        for key in required:
            if key not in input_data:
                return False, f"Missing required field: {key}"
        return True, None

    @staticmethod
    def _score_from_count(count: int) -> int:
        if count <= 2:
            return 0
        if count == 3:
            return 20
        if count == 4:
            return 40
        if count == 5:
            return 60
        if count == 6:
            return 80
        return 100

    def execute(self, input_data: ModuleInput) -> ModuleOutput:
        raw = input_data.raw_data

        if "category_active_count" not in raw:
            return ModuleOutput(
                status=ModuleStatus.FAILED,
                data={},
                errors=[{"code": "MISSING_HISTORY_CONTEXT", "message": "Missing category_active_count"}],
            )

        category_count = int(raw.get("category_active_count", 0))
        tag_counts = raw.get("tag_active_counts", {}) or {}
        days_since_last_dead = float(raw.get("days_since_last_dead", 0))

        fatigue_category = self._score_from_count(category_count)
        fatigue_tag = max((self._score_from_count(int(count)) for count in tag_counts.values()), default=0)

        if raw.get("lifecycle_state") == "Dead" and days_since_last_dead >= 30:
            fatigue_category = 0
            fatigue_tag = 0
            reset_eligible = True
        else:
            reset_eligible = False

        fatigue_final = max(fatigue_category, fatigue_tag)
        watch_mode = fatigue_final > 85

        if fatigue_final > 70:
            discount = 0.5
            take_profit_penalty = 0.5
        else:
            discount = 1.0
            take_profit_penalty = 0.0

        return ModuleOutput(
            status=ModuleStatus.SUCCESS,
            data={
                "event_id": raw["event_id"],
                "fatigue_category": fatigue_category,
                "fatigue_tag": fatigue_tag,
                "fatigue_final": fatigue_final,
                "watch_mode": watch_mode,
                "a_minus_1_discount_factor": discount,
                "take_profit_penalty": take_profit_penalty,
                "reset_eligible": reset_eligible,
                "reasoning": "最终疲劳度取类别疲劳与标签疲劳的最大值",
                "audit": {
                    "module": self.name,
                    "rule_version": "fatigue_v1",
                    "decision_trace": [fatigue_category, fatigue_tag, fatigue_final, watch_mode],
                },
            },
        )


if __name__ == "__main__":
    payload = {
        "event_id": "ME-E-20260331-002.V1.0",
        "category": "E",
        "lifecycle_state": "Continuation",
        "narrative_tags": ["policy_pivot"],
        "category_active_count": 6,
        "tag_active_counts": {"policy_pivot": 7},
        "days_since_last_dead": 3,
    }
    print(FatigueCalculator().run(payload).data)
