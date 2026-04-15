---
title: Observability & SLO Spec
title_zh: 可观测性与 SLO 规范
version: v1.0
status: appendix_normative
parent_doc: 主题板块催化持续性引擎 v1.0
---

# Observability & SLO Spec｜可观测性与 SLO 规范

## 1. 目的

建立稳定运行所需的核心观测指标与目标值。

## 2. 核心 SLI

### 路由层
- route_hit_rate
- route_reject_rate

### 识别层
- catalyst_candidate_rate
- theme_mapping_success_rate

### 验证层
- basket_confirmation_rate
- market_data_missing_rate

### 状态层
- state_distribution
- continuation_rate
- exhaustion_rate

### 输出层
- trade_grade_distribution
- degraded_output_rate
- safe_to_consume_false_rate

### 系统层
- e2e_latency_ms
- replay_consistency_rate

## 3. 建议 SLO

| 指标 | 建议目标 |
|---|---|
| theme_mapping_success_rate | >= 95%（标准样本集） |
| degraded_output_rate | <= 10% |
| replay_consistency_rate | >= 99% |
| e2e_latency_ms | 由部署环境定义，建议设上限 |
| safe_to_consume_false_rate | 持续监控，不设静态硬目标 |

## 4. 统计窗口

统一窗口：
- `5m`：实时波动监控
- `1h`：值守与告警主窗口
- `1d`：日报/周报分析窗口

规则：
- SLO 判定默认以 `1h` 与 `1d` 为准
- `5m` 主要用于异常尖刺检测，不单独作为发布阻断依据

## 5. 告警与升级策略

告警分级：
- `P1`：核心契约不可消费（如 `safe_to_consume=false` 异常飙升、replay 一致性严重下降）
- `P2`：质量显著退化（如映射成功率持续低于阈值）
- `P3`：可观测性异常（单项指标短时抖动）

升级策略：
- 连续两个 `1h` 窗口违反核心 SLO：升级为 `P1`，冻结发布
- 单个 `1h` 窗口违反非核心 SLO：记为 `P2`，要求 24h 内修复
- `5m` 尖刺仅触发预警，不直接阻断发布

## 6. 监控要求

每次运行至少记录：
- event_id
- contract_version
- config_version
- route_result
- mapping_result
- validation_result
- state_result
- trade_grade
- fallback_reason
- safe_to_consume
- e2e_latency_ms

## 7. 一句话裁决

> 没有观测，就没有稳定性；没有 SLO，就没有长期维护。
