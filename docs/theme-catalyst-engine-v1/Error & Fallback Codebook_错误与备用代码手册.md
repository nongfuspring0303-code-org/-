---
title: Error & Fallback Codebook
title_zh: 错误与备用代码手册
version: v1.0
status: appendix_normative
parent_doc: 主题板块催化持续性引擎 v1.0
---

# Error & Fallback Codebook｜错误与备用代码手册

## 1. 目的

统一定义：
- 错误码
- 降级输出
- fallback_reason
- 安全消费标记

避免下游把“缺数据 / 失败 / 不确定”误判为“负面结论”。

## 2. 标准输出字段

```yaml
status:
error_code:
fallback_reason:
degraded_mode:
safe_to_consume:
retryable:
missing_dependencies:
contract_name:
contract_version:
producer_module:
```

说明：
- 上述 `contract_*` 字段采用“输出信封（output envelope）”方式承载。
- 若业务对象未内嵌这些字段，必须由统一输出层补齐后再下发。

## 3. 错误码

| error_code | 含义 | 默认动作 |
|---|---|---|
| CONFIG_MISSING | 配置缺失 | 进入降级模式 |
| CONFIG_INVALID | 配置不合法 | 拒绝高置信输出 |
| THEME_MAPPING_FAILED | 主题映射失败 | 不输出 primary_theme |
| BASKET_EMPTY | 篮子为空 | 不得输出 A/B 评级 |
| MARKET_DATA_MISSING | 行情数据缺失 | 仅输出观察级别 |
| VALIDATION_SKIPPED | 验证层跳过 | 禁止 continuation 升级 |
| STATE_ENGINE_INSUFFICIENT_DATA | 状态机数据不足 | 状态锁定为 FIRST_IMPULSE 或 DEAD（需带说明） |
| DOWNSTREAM_OUTPUT_DEGRADED | 输出层降级 | 标记 safe_to_consume=false |

## 4. 降级规则

### 4.1 映射失败
- `safe_to_consume = false`
- `trade_grade = D`
- `fallback_reason = THEME_MAPPING_FAILED`

### 4.2 篮子为空
- 允许保留 `catalyst_candidate = true`
- 禁止输出 `A/B`
- `trade_grade = C` 或 `D`

### 4.3 行情验证缺失
- 不得输出 `CONTINUATION`
- 默认降级为 `FIRST_IMPULSE`
- `safe_to_consume = false`

### 4.4 状态机数据不足
- 禁止引入主文档未定义的新状态
- 默认降级为 `FIRST_IMPULSE`（信息不足但可观察）
- 或在已确认失效时降级为 `DEAD`
- `fallback_reason = STATE_ENGINE_INSUFFICIENT_DATA`

## 5. 一句话裁决

> 所有失败必须显式失败；禁止静默降级、禁止空值冒充正常结论。
