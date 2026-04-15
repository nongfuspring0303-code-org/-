---
title: Replay / Idempotency Policy
title_zh: 重放 / 幂等政策
version: v1.0
status: appendix_normative
parent_doc: 主题板块催化持续性引擎 v1.0
---

# Replay / Idempotency Policy｜重放 / 幂等政策

## 1. 目的

保证：
- 同一事件不会被无控制重复消费
- 状态推进有规则
- live 与 replay 结果可复现、可解释

## 2. 幂等主键

默认幂等键：

```text
idempotency_key = event_id + config_version + evaluation_window
```

字段来源与缺省：
- `event_id`：事件对象主键（必填）
- `config_version`：配置版本（优先读取运行时配置中心；缺失时置为 `unknown_config_version`）
- `evaluation_window`：评估窗口（优先读取运行态窗口；缺失时按规则归一为 `T0`）

若使用缺省值生成幂等键，必须附带：

```yaml
idempotency_degraded: true
idempotency_degraded_reason:
```

## 3. 同一事件重复进入规则

### 允许：
- 同一 event_id 在新 evaluation_window 进入，用于状态推进
- 同一 event_id 在新 config_version 下 replay，用于复盘

### 不允许：
- 同一 event_id 在同一 config_version + 同一 evaluation_window 下重复写入新结果

## 4. 状态推进规则

- 状态允许前进：`FIRST_IMPULSE → CONTINUATION → EXHAUSTION → DEAD`
- 禁止无说明逆向跳变
- 若发生逆向修正，必须记录：
  - `state_override_reason`
  - `manual_or_system_override`
  - `previous_state`

## 5. replay 一致性要求

同一：
- `event_id`
- `input_snapshot`
- `config_version`
- `evaluation_window`

必须得到可复现结果。  
若不同，必须输出：

```yaml
replay_consistency: false
consistency_break_reason:
```

## 6. 一句话裁决

> live 可以推进，replay 必须可复现；幂等是审计前提，不是可选优化。
