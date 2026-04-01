#!/usr/bin/env python3
"""
Analysis modules for EDT (T3.1 - T3.5 pre-chain).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from edt_module_base import EDTModule, ModuleInput, ModuleOutput, ModuleStatus, SignalScorer


def _default_config_path() -> str:
    return str(Path(__file__).resolve().parent.parent / "configs" / "edt-modules-config.yaml")


class LifecycleManager(EDTModule):
    """Manage event lifecycle transitions."""

    def __init__(self, config_path: Optional[str] = None):
        super().__init__("LifecycleManager", "1.0.0", config_path or _default_config_path())

    def validate_input(self, input_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        if "event_state" not in input_data:
            return False, "Missing required field: event_state"
        return True, None

    def execute(self, input_data: ModuleInput) -> ModuleOutput:
        raw = input_data.raw_data
        prev = raw["event_state"]
        state = prev
        verified = bool(raw.get("verified", False))
        elapsed_hours = float(raw.get("elapsed_hours", 0))
        reaction_decay = float(raw.get("reaction_decay", 0))
        force_dead = bool(raw.get("force_dead", False))

        if force_dead:
            state = "Dead"
        elif prev == "Detected" and verified:
            state = "Verified"
        elif prev == "Verified" and elapsed_hours >= 1:
            state = "Active"
        elif prev == "Active" and elapsed_hours >= 24:
            state = "Continuation"
        elif prev == "Continuation" and reaction_decay >= 0.5:
            state = "Exhaustion"
        elif prev == "Exhaustion" and elapsed_hours >= 72:
            state = "Dead"

        catalyst_map = {
            "Detected": "first_impulse",
            "Verified": "first_impulse",
            "Active": "first_impulse",
            "Continuation": "continuation",
            "Exhaustion": "exhaustion",
            "Dead": "dead",
            "Archived": "dead",
        }

        return ModuleOutput(
            status=ModuleStatus.SUCCESS,
            data={
                "previous_state": prev,
                "lifecycle_state": state,
                "state_changed": prev != state,
                "catalyst_state": catalyst_map.get(state, "dead"),
            },
        )


class FatigueCalculator(EDTModule):
    """Calculate category/tag fatigue and final fatigue."""

    def __init__(self, config_path: Optional[str] = None):
        super().__init__("FatigueCalculator", "1.0.0", config_path or _default_config_path())

    def validate_input(self, input_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        if "category_event_count" not in input_data or "tag_event_count" not in input_data:
            return False, "Missing required fields: category_event_count/tag_event_count"
        return True, None

    @staticmethod
    def _calc(count: int) -> float:
        return max(0.0, min(100.0, (count - 2) * 20.0))

    def execute(self, input_data: ModuleInput) -> ModuleOutput:
        raw = input_data.raw_data
        c_count = int(raw["category_event_count"])
        t_count = int(raw["tag_event_count"])

        fatigue_category = self._calc(c_count)
        fatigue_tag = self._calc(t_count)
        fatigue_final = max(fatigue_category, fatigue_tag)
        risk_level = "HIGH" if fatigue_final > 85 else ("MEDIUM" if fatigue_final >= 70 else "LOW")

        return ModuleOutput(
            status=ModuleStatus.SUCCESS,
            data={
                "fatigue_category": fatigue_category,
                "fatigue_tag": fatigue_tag,
                "fatigue_final": fatigue_final,
                "risk_level": risk_level,
            },
        )


class ConductionMapper(EDTModule):
    """Map event category to macro/sector/stock conduction."""

    def __init__(self, config_path: Optional[str] = None):
        super().__init__("ConductionMapper", "1.0.0", config_path or _default_config_path())

    def validate_input(self, input_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        if "category" not in input_data:
            return False, "Missing required field: category"
        return True, None

    def execute(self, input_data: ModuleInput) -> ModuleOutput:
        raw = input_data.raw_data
        category = raw["category"]
        severity = raw.get("severity", "E2")
        mapping = self._get_config("modules.ConductionMapper.params.event_conduction", {})
        category_mapping = mapping.get(category, {"macro": ["unknown"], "sector": ["unknown"]})

        severity_strength = {"E0": 0.1, "E1": 0.25, "E2": 0.5, "E3": 0.75, "E4": 1.0}
        candidate_stocks = raw.get("candidate_stocks", [])

        return ModuleOutput(
            status=ModuleStatus.SUCCESS,
            data={
                "conduction": {
                    "macro": category_mapping.get("macro", []),
                    "sector": category_mapping.get("sector", []),
                    "stock": candidate_stocks[:3],
                },
                "conduction_strength": severity_strength.get(severity, 0.5),
            },
        )


class MarketValidator(EDTModule):
    """Validate whether market is trading the narrative and produce A1."""

    def __init__(self, config_path: Optional[str] = None):
        super().__init__("MarketValidator", "1.0.0", config_path or _default_config_path())

    def validate_input(self, input_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        required = ["price_reaction", "volume", "correlation", "persistence", "divergence"]
        for key in required:
            if key not in input_data:
                return False, f"Missing required field: {key}"
        return True, None

    @staticmethod
    def _as_score(v: Any) -> float:
        if isinstance(v, bool):
            return 100.0 if v else 0.0
        return max(0.0, min(100.0, float(v)))

    def execute(self, input_data: ModuleInput) -> ModuleOutput:
        raw = input_data.raw_data
        weights = self._get_config("modules.MarketValidator.params.weights", {})
        weight_sum = float(sum(weights.values())) or 100.0

        checks = {
            "price_reaction": self._as_score(raw["price_reaction"]),
            "volume": self._as_score(raw["volume"]),
            "correlation": self._as_score(raw["correlation"]),
            "persistence": self._as_score(raw["persistence"]),
            "divergence": self._as_score(raw["divergence"]),
        }

        score = 0.0
        for k, v in checks.items():
            score += (float(weights.get(k, 0)) / weight_sum) * v

        thresholds = self._get_config("modules.MarketValidator.params.thresholds", {})
        strong = float(thresholds.get("strong", 80))
        medium = float(thresholds.get("medium", 60))
        tier = "strong" if score >= strong else ("medium" if score >= medium else "weak")

        return ModuleOutput(
            status=ModuleStatus.SUCCESS,
            data={
                "A1": round(score, 2),
                "validation_tier": tier,
                "validated": score >= medium,
                "check_scores": checks,
            },
        )


class AnalysisPipeline:
    """Pipeline: lifecycle -> fatigue -> conduction -> market -> signal scorer."""

    def __init__(self):
        self.lifecycle = LifecycleManager()
        self.fatigue = FatigueCalculator()
        self.conduction = ConductionMapper()
        self.market = MarketValidator()
        self.scorer = SignalScorer()

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        lifecycle_out = self.lifecycle.run(payload)
        fatigue_out = self.fatigue.run(payload)
        conduction_out = self.conduction.run(payload)
        market_out = self.market.run(payload)

        signal_in = {
            "A0": payload.get("A0", 20),
            "A-1": payload.get("A-1", 50),
            "A1": market_out.data["A1"],
            "A1.5": payload.get("A1.5", 50),
            "A0.5": payload.get("A0.5", 0),
            "severity": payload.get("severity", "E2"),
            "fatigue_index": fatigue_out.data["fatigue_final"],
            "correlation": payload.get("correlation", 0.5),
            "policy_intervention": payload.get("policy_intervention", "NONE"),
        }
        score_out = self.scorer.run(signal_in)

        return {
            "lifecycle": lifecycle_out.data,
            "fatigue": fatigue_out.data,
            "conduction": conduction_out.data,
            "market_validation": market_out.data,
            "signal": score_out.data,
        }


if __name__ == "__main__":
    out = AnalysisPipeline().run(
        {
            "event_state": "Active",
            "verified": True,
            "elapsed_hours": 26,
            "reaction_decay": 0.3,
            "category_event_count": 4,
            "tag_event_count": 3,
            "category": "C",
            "severity": "E3",
            "candidate_stocks": ["XLF", "JPM", "GS"],
            "price_reaction": 80,
            "volume": 75,
            "correlation": 70,
            "persistence": 65,
            "divergence": 60,
            "A0": 30,
            "A-1": 70,
            "A1.5": 60,
            "A0.5": 0,
        }
    )
    import json

    print(json.dumps(out, indent=2, ensure_ascii=False))

