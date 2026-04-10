#!/usr/bin/env python3
"""Feature-flagged semantic analyzer with deterministic fallback."""

from __future__ import annotations

import time
from typing import Any, Dict

from config_center import ConfigCenter


class SemanticAnalyzer:
    def __init__(self, config_path: str | None = None):
        self.config = ConfigCenter(config_path=config_path)

    def _semantic_cfg(self) -> Dict[str, Any]:
        runtime = self.config.data.get("runtime", {}) if isinstance(self.config.data, dict) else {}
        semantic = runtime.get("semantic", {}) if isinstance(runtime, dict) else {}
        return semantic if isinstance(semantic, dict) else {}

    def _enabled(self) -> bool:
        return bool(self._semantic_cfg().get("enabled", False))

    def _emergency_disabled(self) -> bool:
        return bool(self._semantic_cfg().get("emergency_disable", False))

    def _full_enabled(self) -> bool:
        return bool(self._semantic_cfg().get("full_enable", True))

    def _min_confidence(self) -> int:
        value = self._semantic_cfg().get("min_confidence", 70)
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return 70
        return max(0, min(100, parsed))

    def _timeout_ms(self) -> int:
        value = self._semantic_cfg().get("timeout_ms", 3000)
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return 3000
        return max(1, parsed)

    def _provider_name(self) -> str:
        provider = self._semantic_cfg().get("provider", "deterministic")
        return str(provider or "deterministic")

    def _model_name(self) -> str:
        model = self._semantic_cfg().get("model", "")
        return str(model or "")

    def _abstain_response(
        self,
        *,
        fallback_reason: str,
        provider: str,
        latency_ms: int = 0,
    ) -> Dict[str, Any]:
        return {
            "event_type": "unknown",
            "sentiment": "neutral",
            "confidence": 0,
            "recommended_chain": "",
            "verdict": "abstain",
            "reason": fallback_reason,
            "provider": provider,
            "latency_ms": int(max(0, latency_ms)),
            "fallback_reason": fallback_reason,
        }

    def _coerce_output(self, payload: Dict[str, Any], provider: str, latency_ms: int) -> Dict[str, Any]:
        try:
            confidence = int(float(payload.get("confidence", 0) or 0))
        except (TypeError, ValueError):
            confidence = 0
        confidence = max(0, min(100, confidence))

        try:
            parsed_latency = int(float(payload.get("latency_ms", latency_ms) or latency_ms))
        except (TypeError, ValueError):
            parsed_latency = latency_ms

        output = {
            "event_type": str(payload.get("event_type", "unknown") or "unknown"),
            "sentiment": str(payload.get("sentiment", "neutral") or "neutral"),
            "confidence": confidence,
            "recommended_chain": str(payload.get("recommended_chain", "") or ""),
            "verdict": "abstain",
            "reason": str(payload.get("reason", "") or ""),
            "provider": str(payload.get("provider", provider) or provider),
            "latency_ms": int(max(0, parsed_latency)),
            "fallback_reason": str(payload.get("fallback_reason", "") or ""),
        }
        return output

    def _call_provider(
        self,
        headline: str,
        raw_text: str,
        *,
        provider: str,
        model: str,
        timeout_ms: int,
    ) -> Dict[str, Any]:
        _ = (provider, model, timeout_ms)
        text = f"{headline} {raw_text}".lower()
        if any(k in text for k in ["trade meeting", "trade talks", "贸易会议", "贸易谈判", "谈判"]):
            return {
                "event_type": "trade_talks",
                "sentiment": "neutral",
                "confidence": 80,
                "recommended_chain": "trade_talks_chain",
                "reason": "deterministic keyword match",
            }
        if any(k in text for k in ["tariff", "trade war", "关税", "贸易战"]):
            return {
                "event_type": "tariff",
                "sentiment": "negative",
                "confidence": 82,
                "recommended_chain": "tariff_chain",
                "reason": "deterministic keyword match",
            }
        return {
            "event_type": "unknown",
            "sentiment": "neutral",
            "confidence": 50,
            "recommended_chain": "",
            "reason": "deterministic fallback",
        }

    def analyze(self, headline: str, raw_text: str = "") -> Dict[str, Any]:
        provider = self._provider_name()
        model = self._model_name()
        timeout_ms = self._timeout_ms()

        if not self._enabled():
            return self._abstain_response(
                fallback_reason="semantic_disabled",
                provider=provider,
            )

        if self._emergency_disabled():
            return self._abstain_response(
                fallback_reason="emergency_disabled",
                provider=provider,
            )

        if not self._full_enabled():
            return self._abstain_response(
                fallback_reason="full_enable_disabled",
                provider=provider,
            )

        started = time.perf_counter()
        try:
            payload = self._call_provider(
                headline,
                raw_text,
                provider=provider,
                model=model,
                timeout_ms=timeout_ms,
            )
        except TimeoutError:
            elapsed = int((time.perf_counter() - started) * 1000.0)
            return self._abstain_response(
                fallback_reason="timeout",
                provider=provider,
                latency_ms=elapsed,
            )
        except Exception:
            elapsed = int((time.perf_counter() - started) * 1000.0)
            return self._abstain_response(
                fallback_reason="provider_error",
                provider=provider,
                latency_ms=elapsed,
            )

        elapsed = int((time.perf_counter() - started) * 1000.0)
        out = self._coerce_output(payload if isinstance(payload, dict) else {}, provider, elapsed)

        if out["confidence"] < self._min_confidence():
            out["verdict"] = "abstain"
            out["fallback_reason"] = "confidence_below_threshold"
            if not out["reason"]:
                out["reason"] = "confidence below threshold"
            return out

        if out["recommended_chain"]:
            out["verdict"] = "hit"
            if not out["reason"]:
                out["reason"] = "semantic hit"
            out["fallback_reason"] = ""
            return out

        out["verdict"] = "abstain"
        out["fallback_reason"] = "chain_missing"
        if not out["reason"]:
            out["reason"] = "missing recommended chain"
        return out
