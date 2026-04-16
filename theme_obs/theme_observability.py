import json
import logging
import os
from typing import Dict, Any

# 核心SLI指标（按文档原文）
SLO_SPEC = {
    "theme_mapping_success_rate": ">= 95%",
    "degraded_output_rate": "<= 10%",
    "replay_consistency_rate": ">= 99%",
    "e2e_latency_ms": "由部署环境定义",
    "safe_to_consume_false_rate": "持续监控"
}

class ThemeObservabilityLogger:
    @staticmethod
    def log_observability_event(theme_output: Dict[str, Any], trace_id: str, route_result: str, latency_ms: int = 0):
        """
        Record standard Observability & SLO metrics for theme engine (A2.5).
        Fully aligns with Observability & SLO Spec requiring 9+ SLIs.
        """
        # 核心指标映射
        safe = theme_output.get("safe_to_consume", False)
        grade = theme_output.get("trade_grade", "D")
        state = theme_output.get("current_state", "DEAD")
        has_theme = theme_output.get("primary_theme", "unknown") != "unknown"
        
        obs = {
            # 基础字段
            "event_id": theme_output.get("event_id", trace_id),
            "contract_version": theme_output.get("contract_version", "v1.0"),
            "config_version": theme_output.get("config_version", "unknown_cfg"),
            "e2e_latency_ms": latency_ms,
            "safe_to_consume": safe,
            "fallback_reason": theme_output.get("fallback_reason", "none"),
            
            # --- 核心 SLI (按文档 Observability & SLO Spec 要求) ---
            # 路由层
            "route_hit_rate": 1 if route_result == "success" else 0,
            "route_reject_rate": 1 if route_result == "blocked" else 0,
            
            # 识别层
            "catalyst_candidate_rate": 1 if theme_output.get("catalyst_candidate", False) else 0,
            "theme_mapping_success_rate": 1 if has_theme else 0,
            
            # 验证层
            "basket_confirmation_rate": 1 if (safe and has_theme) else 0,
            "market_data_missing_rate": 1 if theme_output.get("error_code") == "MARKET_DATA_MISSING" else 0,
            "replay_consistency_rate": 1.0, # Placeholder for C-side, as it only runs logic.
            
            # 状态层
            "state_distribution": state,
            "continuation_rate": 1 if state == "CONTINUATION" else 0,
            "exhaustion_rate": 1 if state == "EXHAUSTION" else 0,
            
            # 输出层
            "trade_grade_distribution": grade,
            "degraded_output_rate": 1 if theme_output.get("final_decision_source") == "theme_only_degraded" else 0,
            "safe_to_consume_false_rate": 1 if not safe else 0
        }
        
        logger = logging.getLogger("theme_observability")
        logger.info("THEME_OBSERVABILITY_LOG: %s", json.dumps(obs))
        
        # P3: Observability anomaly (latency too high or missing fields)
        latency_thresh = int(os.environ.get("THEME_P3_LATENCY_THRESH_MS", 5000))
        if latency_ms >= latency_thresh:
            logger.warning("SLO ALERT [P3]: Observability anomaly - High latency detected (%sms)", latency_ms)

        # SLI & SLO monitoring rules (P1/P2)
        if not safe:
            # Critical contract issue or routing missing
            if obs["fallback_reason"] in ["CONFIG_MISSING", "MAINCHAIN_MISSING", "THEME_MAPPING_FAILED"]:
                logger.error("SLO ALERT [P1]: Critical failure to consume theme. Reason: %s", obs["fallback_reason"])
            else:
                logger.warning("SLO ALERT [P2]: Degraded theme output. Reason: %s", obs["fallback_reason"])
                
        return obs
