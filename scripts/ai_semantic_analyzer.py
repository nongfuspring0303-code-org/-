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

    def _api_key(self) -> str:
        # Priority: env > .env.local > (none)
        env_name = str(self._semantic_cfg().get("api_key_env") or "ZAI_API_KEY")

        # 1. Environment variable
        value = os.getenv(env_name, "").strip()
        if value:
            return value
        
        # 2. .env.local file (项目根目录，不提交git)
        project_root = Path(__file__).parent.parent
        env_local = project_root / ".env.local"
        if env_local.exists():
            with open(env_local) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        if key.strip() == env_name:
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
            "recommended_stocks": payload.get("recommended_stocks", []),
            "verdict": "abstain",
            "reason": str(payload.get("reason", "") or ""),
            "provider": str(payload.get("provider", provider) or provider),
            "model": str(payload.get("model", self.model_name) or self.model_name),
            "semantic_status": str(payload.get("semantic_status", "") or ""),
            "latency_ms": int(max(0, parsed_latency)),
            "fallback_reason": str(payload.get("fallback_reason", "") or ""),
        }
        return output

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

        if provider in ("glm_4", "glm-4.7-flash", "glm-4.7", "glm-4-flash", "gemini_flash_lite") or "glm" in model.lower():
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
        return {
            "event_type": "unknown",
            "sentiment": "neutral",
            "confidence": 50,
            "recommended_chain": "",
            "recommended_stocks": [],
            "reason": "deterministic fallback",
        }

    def _call_glm_api(self, text: str, timeout_ms: int, *, model: str = "") -> Dict[str, Any]:
        prompt = f"""分析这条金融新闻，判断是否影响金融市场，返回纯JSON。

sentiment 定义（基于对股票市场的直接影响）：
- positive: 利好股市（如降息、财政刺激、超预期财报、并购利好、流动性宽松）
- negative: 利空股市（如加息、衰退担忧、地缘冲突、监管收紧、流动性紧缩）
- neutral: 中性影响（如中性政策、无重大影响）

重要规则：
1. 关注事件对市场的直接影响，而非事件发生的原因
2. 货币政策：降息/量化宽松 = positive（流动性宽松）；加息/量化紧缩 = negative（流动性收紧）
3. 财报：超预期 = positive；不及预期 = negative；符合预期 = neutral
4. 地缘政治：冲突升级 = negative；和平谈判 = positive
5. 监管政策：放松监管 = positive；加强监管 = negative

event_type 可选：
- tariff: 关税、贸易战
- geo_political: 地缘政治、军事冲突
- earnings: 财报、业绩
- monetary: 央行、利率
- energy: 能源、油气
- shipping: 航运、海运
- industrial: 工业、制造
- tech: 科技
- healthcare: 医疗
- regulatory: 监管政策、法规
- merger: 并购、重组
- inflation: 通胀
- commodity: 大宗商品
- credit: 信用违约、债券
- natural_disaster: 自然灾害
- pandemic: 疫情、公共卫生
- other: 其他

confidence: 0-100
recommended_chain: 推荐的分析链（可选）
recommended_stocks: 推荐的股票列表（可选），格式为股票代码数组，如["NVDA","AAPL","MSFT"]

示例：
{{"event_type":"monetary","sentiment":"positive","confidence":90,"recommended_chain":"rate_cut_chain","recommended_stocks":["NVDA","AAPL"],"reason":"美联储降息，流动性宽松，利好科技股"}}

新闻：{text}

只返回JSON，不要解释。"""

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
                        "event_type": parsed.get("event_type", "unknown"),
                        "sentiment": parsed.get("sentiment", "neutral"),
                        "confidence": parsed.get("confidence", 50),
                        "recommended_chain": parsed.get("recommended_chain", ""),
                        "recommended_stocks": parsed.get("recommended_stocks", []),
                        "reason": parsed.get("reason", f"{self.model_name} api response"),
                    }
                except json.JSONDecodeError:
                    return {
                        "event_type": "unknown",
                        "sentiment": "neutral",
                        "confidence": 50,
                        "recommended_chain": "",
                        "recommended_stocks": [],
                        "reason": f"{self.model_name} response parsing failed: {content[:200]}",
                    }

            return {
                "event_type": "unknown",
                "sentiment": "neutral",
                "confidence": 50,
                "recommended_chain": "",
                "recommended_stocks": [],
                "reason": f"{self.model_name} no choices returned",
            }

        except requests.exceptions.Timeout:
            return {
                "event_type": "unknown",
                "sentiment": "neutral",
                "confidence": 50,
                "recommended_chain": "",
                "recommended_stocks": [],
                "reason": f"{self.model_name} timeout",
            }
        except requests.exceptions.RequestException as e:
            return {
                "event_type": "unknown",
                "sentiment": "neutral",
                "confidence": 50,
                "recommended_chain": "",
                "recommended_stocks": [],
                "reason": f"{self.model_name} API error: {str(e)[:100]}",
            }
        except Exception as e:
            return {
                "event_type": "unknown",
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

        if out["recommended_chain"]:
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
        event_type = str(semantic.get("event_type", "unknown"))
        state = self._normalize_event_state(
            semantic.get("event_state") or semantic.get("narrative_stage"),
            f"{headline} {raw_text}",
        )
        verdict = str(semantic.get("verdict", "abstain"))
        fallback_reason = str(semantic.get("fallback_reason", "") or "")

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
            "transmission_candidates": self._transmission_candidates(event_type, sentiment)[:3],
            "evidence_grade": evidence_grade,
            "evidence_spans": self._evidence_spans(headline, raw_text),
            "risk_flags": risk_flags,
        }
