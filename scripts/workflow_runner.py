#!/usr/bin/env python3
"""
Workflow runner for T5.1.
Chain: SignalScorer -> LiquidityChecker -> RiskGatekeeper -> PositionSizer -> ExitManager
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import yaml

from edt_module_base import ModuleStatus
from signal_scorer import SignalScorer
from execution_adapter import ExecutionAdapter
from execution_modules import ExitManager, LiquidityChecker, PositionSizer, RiskGatekeeper


class WorkflowRunner:
    """Main orchestration for execution-layer flow."""

    def __init__(
        self,
        config_path: str | None = None,
        execution_mode: str | None = None,
        audit_dir: str | None = None,
        request_store_path: str | None = None,
    ):
        self.config_path = Path(config_path) if config_path else Path(__file__).resolve().parent.parent / "configs" / "edt-modules-config.yaml"
        self.logs_dir = Path(audit_dir) if audit_dir else Path(__file__).resolve().parent.parent / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.request_store_path = Path(request_store_path) if request_store_path else self.logs_dir / "seen_request_ids.txt"
        self.request_store_path.parent.mkdir(parents=True, exist_ok=True)
        self._seen_request_ids = self._load_seen_request_ids()

        self.scorer = SignalScorer()
        self.liquidity = LiquidityChecker()
        self.gatekeeper = RiskGatekeeper()
        self.sizer = PositionSizer()
        self.exit_mgr = ExitManager()
        mode = execution_mode or self._execution_mode_from_config()
        self.executor = ExecutionAdapter(mode=mode, audit_dir=str(self.logs_dir))

    def _execution_mode_from_config(self) -> str:
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            return str(cfg.get("modules", {}).get("ExecutionAdapter", {}).get("params", {}).get("mode", "dry_run"))
        except Exception:
            return "dry_run"

    def _load_seen_request_ids(self) -> set[str]:
        if not self.request_store_path.exists():
            return set()
        ids: set[str] = set()
        with open(self.request_store_path, "r", encoding="utf-8") as f:
            for line in f:
                req = line.strip()
                if req:
                    ids.add(req)
        return ids

    def _persist_request_id(self, request_id: str) -> None:
        with open(self.request_store_path, "a", encoding="utf-8") as f:
            f.write(request_id + "\n")

    def _mark_request_processed(self, request_id: str | None) -> None:
        if not request_id:
            return
        if request_id in self._seen_request_ids:
            return
        self._seen_request_ids.add(request_id)
        self._persist_request_id(request_id)

    @staticmethod
    def _run_with_retry(module: Any, payload: Dict[str, Any], retries: int = 2) -> Any:
        out = module.run(payload)
        attempts = 0
        while out.status != ModuleStatus.SUCCESS and attempts < retries:
            attempts += 1
            out = module.run(payload)
        return out

    @staticmethod
    def _pack_step(step_name: str, module_output: Any) -> Dict[str, Any]:
        return {
            "step": step_name,
            "status": module_output.status.value,
            "data": module_output.data,
            "errors": module_output.errors,
            "warnings": module_output.warnings,
        }

    @staticmethod
    def _normalize_direction(raw_direction: Any) -> tuple[str, bool]:
        """
        Normalize analysis-layer directions for execution-layer compatibility.
        Supported upstream aliases:
        - flip_long  -> long
        - flip_short -> short
        """
        d = str(raw_direction or "long").strip().lower()
        if d in ("long", "short", "neutral"):
            return d, False
        if d == "flip_long":
            return "long", True
        if d == "flip_short":
            return "short", True
        return "neutral", False

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = {"input": payload, "steps": []}
        request_id = payload.get("request_id")
        if request_id and request_id in self._seen_request_ids:
            result["final"] = {"action": "DUPLICATE_IGNORED", "reason": f"request_id={request_id} already processed"}
            return result

        score_in = {
            "event_id": payload.get("event_id", f"EXEC-{payload.get('request_id', 'NA')}"),
            "severity": payload.get("severity", "E3"),
            "A0": payload.get("A0", 0),
            "A-1": payload.get("A-1", 0),
            "A1": payload.get("A1", 0),
            "A1.5": payload.get("A1.5", 0),
            "A0.5": payload.get("A0.5", 0),
            "fatigue_final": payload.get("fatigue_index", 0),
            "a_minus_1_discount_factor": payload.get("a_minus_1_discount_factor", 1.0),
            "correlation": payload.get("correlation", 0.5),
            "is_crowded": payload.get("is_crowded", False),
            "narrative_mode": payload.get("narrative_mode", "Fact-Driven"),
            "policy_intervention": payload.get("policy_intervention", "NONE"),
            "base_direction": payload.get("direction", "long"),
            "watch_mode": payload.get("watch_mode", False),
            "weights_version": payload.get("weights_version", "score_v1"),
        }
        score_out = self._run_with_retry(self.scorer, score_in)
        result["steps"].append(self._pack_step("signal", score_out))
        if score_out.status != ModuleStatus.SUCCESS:
            result["final"] = {"action": "ERROR", "reason": "SignalScorer failed"}
            return result
        result["signal"] = score_out.data
        score = score_out.data["score"]

        liq_in = {
            "vix": payload.get("vix", 18),
            "ted": payload.get("ted", 40),
            "correlation": payload.get("correlation", 0.5),
            "spread_pct": payload.get("spread_pct", 0.002),
        }
        liq_out = self._run_with_retry(self.liquidity, liq_in)
        result["steps"].append(self._pack_step("liquidity", liq_out))
        if liq_out.status != ModuleStatus.SUCCESS:
            result["final"] = {"action": "ERROR", "reason": "LiquidityChecker failed"}
            return result
        result["liquidity"] = liq_out.data

        gate_in = {
            "event_state": payload.get("event_state", "Active"),
            "fatigue_index": payload.get("fatigue_index", 0),
            "liquidity_state": liq_out.data["liquidity_state"],
            "spread_multiplier": liq_out.data["spread_multiplier"],
            "correlation": payload.get("correlation", 0.5),
            "score": score,
            "severity": payload.get("severity", "E3"),
            "A1": payload.get("A1", payload.get("A1", 70)),
            "policy_intervention": payload.get("policy_intervention", "NONE"),
        }
        gate_out = self._run_with_retry(self.gatekeeper, gate_in)
        result["steps"].append(self._pack_step("risk", gate_out))
        if gate_out.status != ModuleStatus.SUCCESS:
            result["final"] = {"action": "ERROR", "reason": "RiskGatekeeper failed"}
            return result
        result["risk"] = gate_out.data

        if gate_out.data["final_action"] in ("BLOCK", "FORCE_CLOSE", "WATCH"):
            result["final"] = {
                "action": gate_out.data["final_action"],
                "reason": "Blocked by gates or no valid position.",
            }
            self._mark_request_processed(request_id)
            return result

        # Human confirmation node (T5.3)
        require_human_confirm = bool(payload.get("require_human_confirm", False)) or bool(
            gate_out.data.get("human_confirm_required", False)
        )
        human_confirmed = bool(payload.get("human_confirmed", False))
        if require_human_confirm and not human_confirmed:
            result["final"] = {
                "action": "PENDING_CONFIRM",
                "reason": "Human confirmation required before execution.",
            }
            result["human_confirm"] = {
                "required": True,
                "confirmed": False,
            }
            self._mark_request_processed(request_id)
            return result

        size_in = {
            "score": score,
            "liquidity_state": liq_out.data["liquidity_state"],
            "risk_gate_multiplier": gate_out.data["position_multiplier"],
            "account_equity": payload.get("account_equity", 100000),
        }
        size_out = self._run_with_retry(self.sizer, size_in)
        result["steps"].append(self._pack_step("position", size_out))
        if size_out.status != ModuleStatus.SUCCESS:
            result["final"] = {"action": "ERROR", "reason": "PositionSizer failed"}
            return result
        result["position"] = size_out.data

        if float(size_out.data.get("final_notional", 0.0)) <= 0:
            result["final"] = {
                "action": "WATCH",
                "reason": "Final position notional is 0 after risk/position checks.",
            }
            self._mark_request_processed(request_id)
            return result

        normalized_direction, direction_was_normalized = self._normalize_direction(payload.get("direction", "long"))
        exit_in = {
            "entry_price": payload.get("entry_price", 100.0),
            "risk_per_share": payload.get("risk_per_share", 2.0),
            "direction": normalized_direction,
            "hold_days": payload.get("hold_days", 0),
            "profit_r": payload.get("profit_r", 0.0),
            "profit_retrace": payload.get("profit_retrace", 0.0),
        }
        exit_out = self._run_with_retry(self.exit_mgr, exit_in)
        result["steps"].append(self._pack_step("exit_plan", exit_out))
        if exit_out.status != ModuleStatus.SUCCESS:
            result["final"] = {"action": "ERROR", "reason": "ExitManager failed"}
            return result
        result["exit_plan"] = exit_out.data

        # Build execution order and pass to adapter (dry-run by default).
        order = {
            "action": "OPEN_LONG" if normalized_direction == "long" else "OPEN_SHORT",
            "symbol": payload.get("symbol", "UNKNOWN"),
            "notional": size_out.data["final_notional"],
            "entry_price": payload.get("entry_price", 100.0),
            "stop_loss": exit_out.data["hard_stop"],
            "take_profit_levels": exit_out.data["take_profit_levels"],
            "request_id": request_id,
        }
        execution_receipt = self.executor.execute(order)

        result["final"] = {
            "action": "EXECUTE",
            "score": score,
            "position_pct": size_out.data["final_position_pct"],
            "position_notional": size_out.data["final_notional"],
            "liquidity_state": liq_out.data["liquidity_state"],
            "execution_ticket": execution_receipt["ticket_id"],
            "execution_mode": execution_receipt["mode"],
        }
        result["human_confirm"] = {
            "required": require_human_confirm,
            "confirmed": human_confirmed,
        }
        result["direction"] = {
            "raw": payload.get("direction", "long"),
            "normalized": normalized_direction,
            "normalized_from_flip": direction_was_normalized,
        }
        result["execution_receipt"] = execution_receipt
        self._mark_request_processed(request_id)
        return result


if __name__ == "__main__":
    runner = WorkflowRunner()
    sample = {
        "A0": 30,
        "A-1": 70,
        "A1": 78,
        "A1.5": 60,
        "A0.5": 0,
        "severity": "E3",
        "fatigue_index": 45,
        "event_state": "Active",
        "correlation": 0.55,
        "vix": 19,
        "ted": 45,
        "spread_pct": 0.003,
        "account_equity": 150000,
        "entry_price": 42.5,
        "risk_per_share": 1.5,
        "direction": "long",
    }
    out = runner.run(sample)
    print(json.dumps(out, indent=2, ensure_ascii=False))
