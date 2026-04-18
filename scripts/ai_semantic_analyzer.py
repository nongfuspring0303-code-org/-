#!/usr/bin/env python3
"""Feature-flagged semantic analyzer with GLM-4.7 Flash API support."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests

from config_center import ConfigCenter

ZAI_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"


class SemanticAnalyzer:
    ALLOWED_EVENT_TYPES = {
        "tariff",
        "geo_political",
        "earnings",
        "monetary",
        "energy",
        "shipping",
        "industrial",
        "tech",
        "healthcare",
        "regulatory",
        "merger",
        "inflation",
        "commodity",
        "credit",
        "natural_disaster",
        "pandemic",
        "other",
    }

    def __init__(self, config_path: str | None = None):
        self.config = ConfigCenter(config_path=config_path)
        self.model_name = self._model_name() or "glm-4.7-flash"

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

    def _get_oauth_token(self) -> str:
        now = time.time()
        if self._oauth_cache.get("token") and now < self._oauth_cache.get("expires_at", 0):
            return str(self._oauth_cache["token"])
        
        cfg = self._semantic_cfg()
        url = cfg.get("oauth_url", "")
        client_id = os.getenv(cfg.get("oauth_client_id_env", "OAUTH_CLIENT_ID"), "")
        client_secret = os.getenv(cfg.get("oauth_client_secret_env", "OAUTH_CLIENT_SECRET"), "")
        
        try:
            resp = requests.post(url, data={"grant_type": "client_credentials"}, auth=(client_id, client_secret), timeout=5)
            resp.raise_for_status()
            data = resp.json()
            token = data["access_token"]
            expires_in = data.get("expires_in", 3600)
            self._oauth_cache = {"token": token, "expires_at": now + expires_in - 60}
            return str(token)
        except Exception:
            return ""

    def _api_key(self) -> str:
        # Priority: env > .env.local > (none)
        # OAuth Support: If provider is OAuth-based, this returns the Client Secret or specific key
        provider = self._provider_name().lower()
        
        if self._semantic_cfg().get("auth_method") == "oauth":
            return self._get_oauth_token()

        env_names = []
        if "openai" in provider:
            env_names = ["OPENAI_API_KEY"]
        
        cfg_env = str(self._semantic_cfg().get("api_key_env") or "")
        if cfg_env:
            env_names.insert(0, cfg_env)
        
        # Default back to ZAI if nothing else specified
        if not env_names:
            env_names = ["ZAI_API_KEY"]

        # 1. Environment variables
        for env_name in env_names:
            value = os.getenv(env_name, "").strip()
            if value:
                return value
        
        # 2. .env.local file
        project_root = Path(__file__).parent.parent
        env_local = project_root / ".env.local"
        if env_local.exists():
            with open(env_local) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        resolved_key = key.strip()
                        if resolved_key in env_names:
                            return val.strip().strip('"')
        
        return ""

    def _abstain_response(
        self,
        *,
        fallback_reason: str,
        provider: str,
        model: str = "",
        latency_ms: int = 0,
    ) -> Dict[str, Any]:
        return {
            "event_type": "unknown",
            "sentiment": "neutral",
            "confidence": 0,
            "recommended_chain": "",
            "recommended_stocks": [],
            "verdict": "abstain",
            "reason": fallback_reason,
            "provider": provider,
            "model": str(model or self.model_name or ""),
            "semantic_status": "fallback",
            "latency_ms": int(max(0, latency_ms)),
            "fallback_reason": fallback_reason,
            "a0_event_strength": 0,
            "expectation_gap": 0,
            "event_state": "Initial",
            "transmission_candidates": [],
            "evidence_spans": [],
            "risk_flags": [fallback_reason] if fallback_reason else [],
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
            "event_type": self._normalize_event_type(payload.get("event_type", "other")),
            "sentiment": str(payload.get("sentiment", "neutral") or "neutral"),
            "confidence": confidence,
            "recommended_chain": str(payload.get("recommended_chain", "") or ""),
            "recommended_stocks": payload.get("recommended_stocks", []),
            "verdict": "abstain",
            "reason": str(payload.get("reason", "") or ""),
            "provider": str(payload.get("provider", provider) or provider),
            "model": str(payload.get("model", self.model_name) or self.model_name),
            "semantic_status": str(payload.get("semantic_status", "") or ""),
            "latency_ms": int(max(0, parsed_latency)),
            "fallback_reason": str(payload.get("fallback_reason", "") or ""),
            "a0_event_strength": self._clamp_int(payload.get("a0_event_strength", confidence), 0, 100, confidence),
            "expectation_gap": self._clamp_int(payload.get("expectation_gap", 0), -100, 100, 0),
            "event_state": self._normalize_event_state(payload.get("event_state") or payload.get("narrative_stage"), ""),
            "transmission_candidates": payload.get("transmission_candidates", []),
            "evidence_spans": payload.get("evidence_spans", []),
            "risk_flags": payload.get("risk_flags", []),
        }
        if not isinstance(output["transmission_candidates"], list):
            output["transmission_candidates"] = []
        output["transmission_candidates"] = [str(x) for x in output["transmission_candidates"] if str(x).strip()][:3]
        if not isinstance(output["evidence_spans"], list):
            output["evidence_spans"] = []
        output["evidence_spans"] = [str(x) for x in output["evidence_spans"] if str(x).strip()][:3]
        if not isinstance(output["risk_flags"], list):
            output["risk_flags"] = []
        output["risk_flags"] = [str(x) for x in output["risk_flags"] if str(x).strip()]
        return output

    @classmethod
    def _normalize_event_type(cls, raw_type: Any) -> str:
        event_type = str(raw_type or "").strip().lower()
        return event_type if event_type in cls.ALLOWED_EVENT_TYPES else "other"

    @staticmethod
    def _clamp_int(value: Any, low: int, high: int, default: int) -> int:
        try:
            parsed = int(float(value))
        except (TypeError, ValueError):
            parsed = default
        return max(low, min(high, parsed))

    @staticmethod
    def _normalize_event_state(raw_state: Any, text: str) -> str:
        mapping = {
            "initial": "Initial",
            "developing": "Developing",
            "peak": "Peak",
            "fading": "Fading",
            "dead": "Dead",
            "continuation": "Developing",
            "exhaustion": "Peak",
        }
        state = str(raw_state or "").strip().lower()
        if state in mapping:
            return mapping[state]
        lower = text.lower()
        if any(k in lower for k in ["resolved", "cancelled", "辟谣", "失效", "终止"]):
            return "Dead"
        if any(k in lower for k in ["surge", "spike", "高潮", "拥挤"]):
            return "Peak"
        if any(k in lower for k in ["cooling", "回落", "衰退", "fading"]):
            return "Fading"
        return "Initial"

    @staticmethod
    def _event_strength(confidence: int, verdict: str) -> int:
        boost = 8 if verdict == "hit" else -12
        return max(0, min(100, confidence + boost))

    @staticmethod
    def _expectation_gap(sentiment: str, confidence: int, headline: str) -> int:
        sign = 0
        s = str(sentiment or "").lower()
        if s == "positive":
            sign = 1
        elif s == "negative":
            sign = -1
        base = max(0, min(100, confidence))
        text = (headline or "").lower()
        if any(k in text for k in ["unexpected", "surprise", "超预期", "意外", "unexpectedly"]):
            base = min(100, base + 10)
        return int(sign * base)

    @staticmethod
    def _evidence_spans(headline: str, raw_text: str) -> List[str]:
        spans: List[str] = []
        if headline:
            spans.append(str(headline).strip())
        for chunk in str(raw_text or "").replace("\n", " ").split("."):
            piece = chunk.strip()
            if len(piece) >= 18:
                spans.append(piece)
            if len(spans) >= 3:
                break
        return spans[:3]

    @staticmethod
    def _transmission_candidates(event_type: str, sentiment: str) -> List[str]:
        et = str(event_type or "").lower()
        s = str(sentiment or "").lower()
        if et in {"tariff", "trade_talks"}:
            return ["import_cost", "export_margin", "supply_chain"]
        if et in {"monetary", "inflation"}:
            return ["real_rate", "usd_liquidity", "duration_asset"]
        if et in {"energy", "geo_political"}:
            return ["oil_price", "shipping_cost", "defense_demand"]
        if s == "positive":
            return ["risk_appetite", "sector_rotation", "leader_momentum"]
        if s == "negative":
            return ["risk_aversion", "valuation_compression", "liquidity_tightening"]
        return ["market_attention", "headline_sensitivity"]

    def _call_provider(
        self,
        headline: str,
        raw_text: str,
        *,
        provider: str,
        model: str,
        timeout_ms: int,
    ) -> Dict[str, Any]:
        text = f"{headline} {raw_text}"

        provider_lower = provider.lower()
        if "openai" in provider_lower or "gpt" in model.lower():
            return self._call_openai_api(text, timeout_ms, model=model)

        if provider_lower in ("glm_4", "glm-4.7-flash", "glm-4.7", "glm-4-flash", "gemini_flash_lite") or "glm" in model.lower():
            return self._call_glm_api(text, timeout_ms, model=model)

        text_lower = text.lower()
        if any(k in text_lower for k in ["trade meeting", "trade talks", "贸易会议", "贸易谈判", "谈判"]):
            return {
                "event_type": "trade_talks",
                "sentiment": "neutral",
                "confidence": 80,
                "recommended_chain": "trade_talks_chain",
                "recommended_stocks": [],
                "reason": "deterministic keyword match",
            }
        if any(k in text_lower for k in ["tariff", "trade war", "关税", "贸易战"]):
            return {
                "event_type": "tariff",
                "sentiment": "negative",
                "confidence": 82,
                "recommended_chain": "tariff_chain",
                "recommended_stocks": [],
                "reason": "deterministic keyword match",
            }
    def _get_oauth_token(self) -> str:
        """Handles OAuth 2.0 token exchange and caching."""
        # Simple file-based cache to avoid redundant hits
        cache_path = Path(__file__).parent.parent / "logs" / ".oauth_cache.json"
        
        if cache_path.exists():
            try:
                cache = json.loads(cache_path.read_text())
                if cache.get("expiry", 0) > time.time() + 60: # 1 min buffer
                    return cache.get("access_token", "")
            except:
                pass

        # Exchange Client ID/Secret for Token
        client_id = os.getenv("EDT_AUTH_CLIENT_ID", "")
        client_secret = os.getenv("EDT_AUTH_CLIENT_SECRET", "")
        token_url = str(self._semantic_cfg().get("oauth_token_url", ""))

        if not (client_id and client_secret and token_url):
            return ""

        try:
            resp = requests.post(
                token_url,
                data={"grant_type": "client_credentials"},
                auth=(client_id, client_secret),
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            token = data["access_token"]
            expiry = time.time() + data.get("expires_in", 3600)
            
            # Save to cache
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps({"access_token": token, "expiry": expiry}))
            
            return token
        except Exception as e:
            print(f"OAuth Failed: {e}")
            return ""

    def _call_openai_api(self, text: str, timeout_ms: int, *, model: str = "") -> Dict[str, Any]:
        prompt = self._get_prompt(text)
        api_key = self._api_key()
        if not api_key:
            return self._abstain_response(fallback_reason="api_key_missing_openai", provider="openai")

        endpoint = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
        use_model = model or "gpt-4o-mini" # Fast & cheap default

        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": use_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 300,
                "response_format": {"type": "json_object"} if "gpt-4" in use_model or "gpt-3.5-turbo-0125" in use_model else None
            }
            timeout_seconds = max(5.0, timeout_ms / 1000.0)
            response = requests.post(endpoint, headers=headers, json=payload, timeout=timeout_seconds)
            response.raise_for_status()
            result = response.json()

            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"].strip()
                return self._parse_ai_content(content)
            
            return self._abstain_response(fallback_reason="openai_no_choices", provider="openai")
        except Exception as e:
            return self._abstain_response(fallback_reason=f"openai_error: {str(e)[:50]}", provider="openai")

    def _get_prompt(self, text: str) -> str:
        return f"""You are an Event Object extractor for an event-driven trading system.

STRICT OUTPUT CONTRACT:
- Return ONE JSON object only. No markdown, no prose.
- Required fields:
  - event_type: one of [tariff, geo_political, earnings, monetary, energy, shipping, industrial, tech, healthcare, regulatory, merger, inflation, commodity, credit, natural_disaster, pandemic, other]
  - sentiment: one of [positive, negative, neutral]
  - confidence: integer 0..100
  - a0_event_strength: integer 0..100
  - expectation_gap: integer -100..100
  - event_state: one of [Initial, Developing, Peak, Fading, Dead]
  - transmission_candidates: array of short strings, 0..3 items
  - evidence_spans: array of short source snippets, 1..3 items
  - risk_flags: array of strings
  - reason: short sentence

News text:
{text}
"""

    def _parse_ai_content(self, content: str) -> Dict[str, Any]:
        clean_content = content.strip()
        if clean_content.startswith("```json"):
            clean_content = clean_content[7:]
        if clean_content.endswith("```"):
            clean_content = clean_content[:-3]
        if clean_content.startswith("```"):
            clean_content = clean_content[3:]
        
        try:
            parsed = json.loads(clean_content.strip())
            return {
                "event_type": self._normalize_event_type(parsed.get("event_type", "other")),
                "sentiment": parsed.get("sentiment", "neutral"),
                "confidence": parsed.get("confidence", 50),
                "recommended_chain": parsed.get("recommended_chain", ""),
                "recommended_stocks": parsed.get("recommended_stocks", []),
                "a0_event_strength": parsed.get("a0_event_strength", parsed.get("confidence", 50)),
                "expectation_gap": parsed.get("expectation_gap", 0),
                "event_state": parsed.get("event_state", "Initial"),
                "transmission_candidates": parsed.get("transmission_candidates", []),
                "evidence_spans": parsed.get("evidence_spans", []),
                "risk_flags": parsed.get("risk_flags", []),
                "reason": parsed.get("reason", "success"),
            }
        except:
             return self._abstain_response(fallback_reason="json_parse_failed", provider="ai")

    def _call_glm_api(self, text: str, timeout_ms: int, *, model: str = "") -> Dict[str, Any]:
        prompt = self._get_prompt(text)
        api_key = self._api_key()
        if not api_key:
            return self._abstain_response(
                fallback_reason="api_key_missing",
                provider=self._provider_name(),
                model=model or self.model_name,
            )

        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model or self.model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 200,
            }
            timeout_seconds = max(5.0, timeout_ms / 1000.0)
            response = requests.post(
                f"{ZAI_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout_seconds,
            )
            response.raise_for_status()
            result = response.json()

            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.endswith("```"):
                    content = content[:-3]
                if content.startswith("```"):
                    content = content[3:]
                content = content.strip()
                try:
                    parsed = json.loads(content)
                    return {
                        "event_type": self._normalize_event_type(parsed.get("event_type", "other")),
                        "sentiment": parsed.get("sentiment", "neutral"),
                        "confidence": parsed.get("confidence", 50),
                        "recommended_chain": parsed.get("recommended_chain", ""),
                        "recommended_stocks": parsed.get("recommended_stocks", []),
                        "a0_event_strength": parsed.get("a0_event_strength", parsed.get("confidence", 50)),
                        "expectation_gap": parsed.get("expectation_gap", 0),
                        "event_state": parsed.get("event_state", parsed.get("narrative_stage", "Initial")),
                        "transmission_candidates": parsed.get("transmission_candidates", []),
                        "evidence_spans": parsed.get("evidence_spans", []),
                        "risk_flags": parsed.get("risk_flags", []),
                        "reason": parsed.get("reason", f"{self.model_name} api response"),
                    }
                except json.JSONDecodeError:
                    return {
                        "event_type": "other",
                        "sentiment": "neutral",
                        "confidence": 50,
                        "recommended_chain": "",
                        "recommended_stocks": [],
                        "reason": f"{self.model_name} response parsing failed: {content[:200]}",
                    }

            return {
                "event_type": "other",
                "sentiment": "neutral",
                "confidence": 50,
                "recommended_chain": "",
                "recommended_stocks": [],
                "reason": f"{self.model_name} no choices returned",
            }

        except requests.exceptions.Timeout:
            return {
                "event_type": "other",
                "sentiment": "neutral",
                "confidence": 50,
                "recommended_chain": "",
                "recommended_stocks": [],
                "reason": f"{self.model_name} timeout",
            }
        except requests.exceptions.RequestException as e:
            return {
                "event_type": "other",
                "sentiment": "neutral",
                "confidence": 50,
                "recommended_chain": "",
                "recommended_stocks": [],
                "reason": f"{self.model_name} API error: {str(e)[:100]}",
            }
        except Exception as e:
            return {
                "event_type": "other",
                "sentiment": "neutral",
                "confidence": 50,
                "recommended_chain": "",
                "recommended_stocks": [],
                "reason": f"{self.model_name} error: {str(e)[:100]}",
            }

    def analyze(self, headline: str, raw_text: str = "") -> Dict[str, Any]:
        provider = self._provider_name()
        model = self._model_name()
        timeout_ms = self._timeout_ms()

        if not self._enabled():
            out = self._abstain_response(
                fallback_reason="semantic_disabled",
                provider=provider,
                model=model,
            )
            out.update(self.analyze_event(headline, raw_text))
            return out

        if self._emergency_disabled():
            out = self._abstain_response(
                fallback_reason="emergency_disabled",
                provider=provider,
                model=model,
            )
            out.update(self.analyze_event(headline, raw_text))
            return out

        if not self._full_enabled():
            out = self._abstain_response(
                fallback_reason="full_enable_disabled",
                provider=provider,
                model=model,
            )
            out.update(self.analyze_event(headline, raw_text))
            return out

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
            out = self._abstain_response(
                fallback_reason="timeout",
                provider=provider,
                model=model,
                latency_ms=elapsed,
            )
            out.update(self.analyze_event(headline, raw_text))
            return out
        except Exception:
            elapsed = int((time.perf_counter() - started) * 1000.0)
            out = self._abstain_response(
                fallback_reason="provider_error",
                provider=provider,
                model=model,
                latency_ms=elapsed,
            )
            out.update(self.analyze_event(headline, raw_text))
            return out

        elapsed = int((time.perf_counter() - started) * 1000.0)
        out = self._coerce_output(payload if isinstance(payload, dict) else {}, provider, elapsed)

        if out["confidence"] < self._min_confidence():
            out["verdict"] = "abstain"
            out["semantic_status"] = "fallback"
            if not out.get("fallback_reason"):
                out["fallback_reason"] = "confidence_below_threshold"
            if not out["reason"]:
                out["reason"] = "confidence below threshold"
            out.update(self.analyze_event(headline, raw_text, semantic_output=out))
            return out

        if out["recommended_chain"] or out.get("transmission_candidates"):
            out["verdict"] = "hit"
            out["semantic_status"] = "hit"
            if not out["reason"]:
                out["reason"] = "semantic hit"
            if not out.get("fallback_reason"):
                out["fallback_reason"] = ""
            out.update(self.analyze_event(headline, raw_text, semantic_output=out))
            return out

        out["verdict"] = "abstain"
        out["semantic_status"] = "fallback"
        if not out.get("fallback_reason"):
            out["fallback_reason"] = "chain_missing"
        if not out["reason"]:
            out["reason"] = "missing recommended chain"
        out.update(self.analyze_event(headline, raw_text, semantic_output=out))
        return out

    def analyze_event(
        self,
        headline: str,
        raw_text: str = "",
        *,
        semantic_output: Dict[str, Any] | None = None,
        event_id: str = "",
        event_time: str = "",
    ) -> Dict[str, Any]:
        """Build contract-style EventObject for downstream rule systems."""
        semantic = semantic_output if isinstance(semantic_output, dict) else {}
        confidence = self._clamp_int(semantic.get("confidence", 0), 0, 100, 0)
        sentiment = str(semantic.get("sentiment", "neutral"))
        event_type = self._normalize_event_type(semantic.get("event_type", "other"))
        state = self._normalize_event_state(
            semantic.get("event_state") or semantic.get("narrative_stage"),
            f"{headline} {raw_text}",
        )
        verdict = str(semantic.get("verdict", "abstain"))
        fallback_reason = str(semantic.get("fallback_reason", "") or "")
        semantic_candidates = semantic.get("transmission_candidates", [])
        if not isinstance(semantic_candidates, list):
            semantic_candidates = []
        normalized_candidates = [str(x) for x in semantic_candidates if str(x).strip()][:3]

        generated_event_time = event_time
        if not generated_event_time:
            generated_event_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        evidence_grade = "C"
        if confidence >= 85:
            evidence_grade = "A"
        elif confidence >= 70:
            evidence_grade = "B"
        elif confidence >= 55:
            evidence_grade = "B-"

        risk_flags: List[str] = []
        if fallback_reason:
            risk_flags.append(fallback_reason)
        if verdict != "hit":
            risk_flags.append("semantic_not_hit")

        return {
            "event_id": str(event_id or ""),
            "event_type": event_type,
            "event_time": generated_event_time,
            "a0_event_strength": self._event_strength(confidence, verdict),
            "expectation_gap": self._expectation_gap(sentiment, confidence, headline),
            "event_state": state,
            "transmission_candidates": normalized_candidates or self._transmission_candidates(event_type, sentiment)[:3],
            "evidence_grade": evidence_grade,
            "evidence_spans": self._evidence_spans(headline, raw_text),
            "risk_flags": risk_flags,
        }
