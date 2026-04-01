#!/usr/bin/env python3
"""
MarketValidator for EDT analysis layer.

This module scores whether the market is validating the mapped event logic
through price, volume, linkage, persistence, and dispersion.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from edt_module_base import EDTModule, ModuleInput, ModuleOutput, ModuleStatus


class MarketValidator(EDTModule):
    """Market validation scorer."""

    def __init__(self, config_path: Optional[str] = None):
        super().__init__("MarketValidator", "1.0.0", config_path)

    def validate_input(self, input_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        required = ["event_id", "conduction_output", "market_timestamp"]
        for key in required:
            if key not in input_data:
                return False, f"Missing required field: {key}"
        return True, None

    def execute(self, input_data: ModuleInput) -> ModuleOutput:
        raw = input_data.raw_data
        conduction_output = raw.get("conduction_output", {})

        if not raw.get("price_changes") and not raw.get("volume_changes"):
            return ModuleOutput(
                status=ModuleStatus.FAILED,
                data={},
                errors=[{"code": "MISSING_MARKET_DATA", "message": "Missing price and volume context"}],
            )

        if not conduction_output:
            return ModuleOutput(
                status=ModuleStatus.FAILED,
                data={},
                errors=[{"code": "MISSING_CONDUCTION_CONTEXT", "message": "Missing conduction output"}],
            )

        price_changes = raw.get("price_changes", {})
        volume_changes = raw.get("volume_changes", {})
        linkage = raw.get("cross_asset_linkage", {})
        persistence_minutes = float(raw.get("persistence_minutes", 0))
        dispersion = raw.get("winner_loser_dispersion", {})

        price_score = 20 if any(abs(v) >= 0.8 for v in price_changes.values()) else 5
        volume_score = 15 if any(v >= 1.4 for v in volume_changes.values()) else 0
        linkage_score = 20 if linkage.get("confirmed") else 0
        persistence_score = 25 if persistence_minutes >= 60 else (15 if persistence_minutes >= 30 else 0)
        divergence_score = 20 if dispersion.get("confirmed") else 0

        a1 = price_score + volume_score + linkage_score + persistence_score + divergence_score

        failed_checks = []
        if price_score < 20:
            failed_checks.append("price_confirmation")
        if volume_score < 15:
            failed_checks.append("volume_confirmation")
        if linkage_score < 20:
            failed_checks.append("cross_asset_linkage")
        if persistence_score < 25:
            failed_checks.append("persistence")
        if divergence_score < 20:
            failed_checks.append("winner_loser_divergence")

        if a1 >= 80:
            state = "validated"
        elif a1 >= 60:
            state = "partially_validated"
        elif linkage.get("confirmed") is False and price_score > 0:
            state = "not_validated"
        else:
            state = "counter_validated" if a1 < 20 else "not_validated"

        return ModuleOutput(
            status=ModuleStatus.SUCCESS,
            data={
                "event_id": raw["event_id"],
                "price_score": price_score,
                "volume_score": volume_score,
                "linkage_score": linkage_score,
                "persistence_score": persistence_score,
                "divergence_score": divergence_score,
                "A1": a1,
                "validation_state": state,
                "failed_checks": failed_checks,
                "validation_notes": "市场验证按价格、量能、联动、持续性、分化五项计算",
                "needs_manual_review": False,
                "audit": {
                    "module": self.name,
                    "rule_version": "validation_v1",
                    "decision_trace": [price_score, volume_score, linkage_score, persistence_score, divergence_score],
                },
            },
        )


if __name__ == "__main__":
    payload = {
        "event_id": "ME-C-20260330-001.V1.0",
        "conduction_output": {"conduction_path": ["关税升级", "通胀压力上升"]},
        "price_changes": {"DXY": 1.2, "XLI": -1.8},
        "volume_changes": {"XLI": 2.3},
        "cross_asset_linkage": {"confirmed": True},
        "persistence_minutes": 90,
        "winner_loser_dispersion": {"confirmed": True},
        "market_timestamp": "2026-03-30T15:00:00Z",
    }
    print(MarketValidator().run(payload).data)
