---
title: E2E Acceptance Checklist
title_zh: 端对端接受清单
version: v1.0
status: appendix_normative
parent_doc: 主题板块催化持续性引擎 v1.0
---

# E2E Acceptance Checklist｜端对端接受清单

## 1. 目的

定义从新闻输入到统一裁决输出的整链验收标准。  
不仅测模块单测，还要测链路完整性。

## 2. 基础链路验收

统一要求（适用于全部 E2E）：
- 必须给出样本 ID：`sample_id`
- 必须给出通过阈值：`pass_threshold`
- 必须给出失败处理：`on_fail_action`

### E2E-01 正常主题催化样本
输入：标准官方新闻  
断言：
- route_to_theme_engine = true
- primary_theme 非空
- basket_confirmation 合法
- current_state 可计算
- trade_grade 非空
- 下游消费字段完整
样本与门槛：
- `sample_id = theme_nvda_quantum_official_t0`
- `pass_threshold = 100% 关键断言通过`
- `on_fail_action = block_merge`

### E2E-02 映射失败样本
断言：
- fallback_reason = THEME_MAPPING_FAILED
- safe_to_consume = false
- trade_grade 不得为 A/B
样本与门槛：
- `sample_id = theme_mapping_fail_generic_news`
- `pass_threshold = 100% 关键断言通过`
- `on_fail_action = block_merge`

### E2E-03 篮子为空样本
断言：
- error_code = BASKET_EMPTY
- 不得输出高评级
- 个股池为空
样本与门槛：
- `sample_id = theme_basket_empty_case`
- `pass_threshold = 100% 关键断言通过`
- `on_fail_action = block_merge`

### E2E-04 主链与副链冲突样本
断言：
- conflict_flag = true
- final_decision_source 非空
- 最终评级受到主链封顶
样本与门槛：
- `sample_id = macro_risk_off_theme_hit_conflict`
- `pass_threshold = 100% 关键断言通过`
- `on_fail_action = block_merge`

### E2E-05 replay 一致性样本
断言：
- 同快照同配置 replay 结果一致
- 不一致时有 consistency_break_reason
样本与门槛：
- `sample_id = replay_same_snapshot_same_config`
- `pass_threshold = replay_consistency_rate >= 99%`
- `on_fail_action = freeze_release_and_open_incident`

## 3. 一句话裁决

> 单测证明模块能跑，E2E 才证明系统能接主链。
