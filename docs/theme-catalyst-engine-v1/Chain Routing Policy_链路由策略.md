---
title: Chain Routing Policy
title_zh: 主链 / 副链链路由策略
version: v1.0
status: appendix_normative
parent_doc: 主题板块催化持续性引擎 v1.0
---

# Chain Routing Policy｜主链 / 副链链路由策略

## 1. 目的

定义当 **宏观主链** 与 **主题副链** 同时命中时，如何进行：
- 优先级裁决
- 信号合并
- 风险封顶
- 回退输出

## 2. 基本原则

### 2.1 默认优先级
`macro > sector_theme`

解释：
- 宏观风险方向优先于主题机会方向
- 副链可以加分，但不得在高风险宏观环境下无条件翻案

### 2.2 宏观环境分层
- `RISK_OFF`
- `MIXED`
- `RISK_ON`

### 2.3 副链作用边界
- 在 `RISK_OFF` 下：副链最多输出“仅日内 / 轻仓 / 观察”
- 在 `MIXED` 下：副链参与排序，但不能忽略宏观冲突
- 在 `RISK_ON` 下：副链可正常释放权重

## 3. 冲突类型

### C1 宏观回避 vs 副链可做
处理：
- 最终输出以宏观主链为上限
- 副链结果保留，但标记为受限信号

### C2 宏观中性 vs 副链强催化
处理：
- 可允许副链抬升优先级
- 但必须保留 `conflict_flag=false`

### C3 宏观顺风 vs 副链弱催化
处理：
- 不因宏观顺风自动抬升副链评级
- 副链仍按自身证据链评级

## 4. 统一输出字段

```yaml
conflict_flag:
conflict_type:
final_decision_source:
macro_regime:
theme_capped_by_macro:
macro_override_reason:
final_trade_cap:
```

## 5. 合并规则

### 5.1 trade_grade 封顶规则
- 若宏观 = `RISK_OFF`，副链 `A/B` 最终封顶为 `C`
- 若宏观 = `MIXED`，副链可维持原评级，但须附冲突解释
- 若宏观 = `RISK_ON`，副链不被额外封顶

### 5.2 持有周期封顶规则
- `RISK_OFF`：最多 `INTRADAY`
- `MIXED`：最多 `1_TO_2_DAYS`
- `RISK_ON`：可按副链原结论

### 5.3 `final_decision_source` 取值
- `mainchain_only`
- `mainchain_capped_theme`
- `theme_only_degraded`
- `theme_only`

## 6. 回退规则

若主链结果缺失：
- 副链不得假定宏观安全
- 输出 `final_decision_source = theme_only_degraded`
- 输出 `fallback_reason = MAINCHAIN_MISSING`
- 标记 `safe_to_consume = false`

## 7. 一句话裁决

> 主链决定风险天花板，副链决定主题排序与机会精细度。
