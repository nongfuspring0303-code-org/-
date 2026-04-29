# Stage6 PR-7 Final Sign-off Template

> 文件类型：最终验收模板 / Final Acceptance Gate
> 适用范围：Stage6 PR-7 Outcome Attribution / Signal Quality
> 当前用途：在 PR-7b-1 / PR-7b-2 / PR-7b-3 全部完成后，用于 PR-7 Final 全量验收
> 最高优先级：若本文与 `docs/stage6/STAGE6_SCOPE_CANONICAL.md` 冲突，以 `STAGE6_SCOPE_CANONICAL.md` 为准
> 核心边界：只读消费上游证据；不改 Gate；不改 execution；不改 final_action；不改 Stage5 日志结构；不提交真实 runtime 产物

---

## 0. 一句话结论

Stage6 PR-7 Final 不是新的功能开发 PR，而是 Stage6 PR-7 当前范围的最终验收包。

它用于确认：

```text
PR-7a 契约冻结已完成；
PR98 v2.1 execution docs 已落地；
PR-7b-1 / PR-7b-2 / PR-7b-3 工程实现、归因规则、报告输出、幂等与回放一致性均已完成；
A / B / C 三方 review 通过；
Stage6 输出仅用于人工审核与后续规则优化，不进入生产自动执行链路。
```

---

## 1. Final Sign-off 基本信息

| 字段 | 内容 |
|---|---|
| 项目 | Stage6 Signal Quality / Outcome Attribution |
| Final Gate | PR-7 Final |
| 验收对象 | Outcome Engine / Summary / Report / Attribution / Replay / Idempotency |
| 基准分支 | `main` |
| 验收分支 | `review/stage6-pr7-final-signoff` |
| 对应 PR | `TBD - draft PR before final review` |
| 验收日期 | `2026-04-30` |
| 审查模板 | PR 正式审查模板 v2.1（强制版） |
| 最终结论 | `REQUEST CHANGES` |

当前状态说明：A/B/C Review 已完成，当前不满足 Final PASS 条件，需要后续 fix PR 修复后复审。

### 当前预检事实

| 项目 | 结果 |
|---|---|
| Engine CLI | PASS, processed 24 opportunities |
| Generated files | 9/10 |
| Missing file | `outcome_report.md` |
| test_opportunity_outcome_schema.py | PASS, 5 passed |
| test_stage6_metric_dictionary.py | PASS, 5 passed |
| test_outcome_attribution_engine.py | PASS, 34 passed |
| test_outcome_idempotency.py | PASS, 5 passed |
| test_outcome_replay_consistency.py | PASS, 7 passed |
| `python3 scripts/system_healthcheck.py --mode dev` | PASS, OVERALL GREEN with unrelated canary/data YELLOW note |
| Runtime artifact note | `logs/system_health_daily_report.md` must not be committed |

### 三方验收状态

| Review | Status |
|---|---|
| A Review | REQUEST CHANGES |
| B Review | REQUEST CHANGES |
| C Review | REQUEST CHANGES |

---

## 2. 前置条件检查

PR-7 Final 开始前，必须满足以下前置条件。

| 前置条件 | 状态 | 证据 / 链接 | 备注 |
|---|---:|---|---|
| PR-7a / PR97 Contract Freeze 已合并 | ☐ PASS / ☐ FAIL | `<link>` | 冻结 schema / policy / registry / metric dictionary / tests |
| PR98 v2.1 Implementation Plan 已合并 | ☐ PASS / ☐ FAIL | `<link>` | docs-only plan 落地 |
| PR-7b-1 已合并 | ☐ PASS / ☐ FAIL | `<link>` | fixtures + 最小 engine |
| PR-7b-2 已合并 | ☐ PASS / ☐ FAIL | `<link>` | 标签与归因规则 |
| PR-7b-3 已合并 | ☐ PASS / ☐ FAIL | `<link>` | 报告、alpha、idempotency、replay |
| 最新 `main` 已同步 | ☐ PASS / ☐ FAIL | `git rev-parse HEAD` | 必须基于最新 main 验收 |
| CI / healthcheck 可运行 | ☐ PASS / ☐ FAIL | `<log>` | 不允许因 Stage6 变更导致 RED |

---

## 3. 范围声明

### 3.1 In Scope

PR-7 Final 验收以下内容：

```text
1. Stage6 schema / policy / registry / metric_dictionary 是否一致。
2. Outcome attribution engine 是否可运行。
3. fixtures 是否覆盖核心路径。
4. EXECUTE / WATCH / BLOCK / PENDING_CONFIRM / UNKNOWN 是否按规则归因。
5. pending / invalid / degraded / valid 是否正确进入或排除统计。
6. alpha / benchmark / score bucket / failure_reason 是否可追踪。
7. outcome_summary / outcome_report / score bucket / failure distribution / log trust 等报告是否可生成。
8. idempotency 是否通过。
9. replay consistency 是否通过。
10. decision_suggestions 是否只用于人工审核，不被生产执行自动消费。
```

### 3.2 Out of Scope

PR-7 Final 不允许新增或修改以下内容：

```text
1. workflow_runner.py
2. full_workflow_runner.py
3. Gate 规则
4. final_action 语义
5. decision_gate 生产结构
6. execution_emit 生产逻辑
7. Stage5 日志生产结构
8. broker / live trading
9. portfolio PnL
10. kill switch
11. 自动调参
12. 自动修改 playbook
13. 提交真实 logs/*
14. 提交真实 reports/outcome/* runtime 产物
```

---

## 4. 契约真源检查

以下文件必须存在，且不得与 PR97 / PR98 合并后的 contract 发生漂移。

| 文件 | 检查项 | 状态 | 备注 |
|---|---|---:|---|
| `docs/stage6/STAGE6_SCOPE_CANONICAL.md` | 最高范围文件存在且未被弱化 | ☐ PASS / ☐ FAIL | 最高优先级 |
| `schemas/opportunity_outcome.schema.json` | required / enum / nullable / audit-only 规则一致 | ☐ PASS / ☐ FAIL | 主 outcome schema |
| `schemas/mapping_attribution.schema.json` | mapping_status / failure_reason enum 一致 | ☐ PASS / ☐ FAIL | mapping 归因 |
| `schemas/log_trust.schema.json` | log trust 输出契约存在 | ☐ PASS / ☐ FAIL | 日志可信度 |
| `schemas/outcome_by_score_bucket.schema.json` | strong schema，`additionalProperties:false` | ☐ PASS / ☐ FAIL | score bucket 输出 |
| `configs/outcome_scoring_policy.yaml` | 阈值单一真源 | ☐ PASS / ☐ FAIL | 禁止 Python 硬编码 |
| `configs/metric_dictionary.yaml` | Stage6 metrics + legacy compatibility 保留 | ☐ PASS / ☐ FAIL | 指标字典 |
| `module-registry.yaml` | Stage6 module / contract_artifacts 绑定完整 | ☐ PASS / ☐ FAIL | registry 一致性 |
| `docs/tasks/stage6-pr7-outcome-attribution.md` | PR-7a / PR-7b / Final 口径一致 | ☐ PASS / ☐ FAIL | taskbook |
| `docs/review/pr7_rules_test_mapping.md` | PR-7a complete 与 PR-7b implemented/planned 状态表述准确 | ☐ PASS / ☐ FAIL | rule ↔ test traceability |

---

## 5. Engine 可运行验收

### 5.1 运行命令

PR-7 Final 必须验证以下命令可运行：

```bash
python3 scripts/outcome_attribution_engine.py \
  --logs-dir tests/fixtures/stage6/outcome_logs \
  --out-dir /tmp/stage6_outcome_test
```

### 5.2 期望输出

engine 应在 `/tmp/stage6_outcome_test` 或 pytest `tmp_path` 中生成以下文件：

| 输出文件 | 必须生成 | schema / 校验 | 备注 |
|---|---:|---|---|
| `opportunity_outcome.jsonl` | ☐ YES / ☐ NO | `schemas/opportunity_outcome.schema.json` | 核心 outcome records |
| `outcome_summary.json` | ☐ YES / ☐ NO | metric dictionary 对齐 | 汇总指标 |
| `outcome_report.md` | ☐ YES / ☐ NO | 人工可读 | 不进入执行链路 |
| `outcome_by_score_bucket.json` | ☐ YES / ☐ NO | `schemas/outcome_by_score_bucket.schema.json` | score bucket |
| `score_monotonicity_report.json` | ☐ YES / ☐ NO | policy 阈值 | 单调性 |
| `failure_reason_distribution.json` | ☐ YES / ☐ NO | failure enum | 失败原因分布 |
| `alpha_report.json` | ☐ YES / ☐ NO | alpha / benchmark 规则 | 超额收益报告 |
| `log_trust_report.json` | ☐ YES / ☐ NO | log trust schema | 日志可信度 |
| `mapping_attribution.jsonl` | ☐ YES / ☐ NO | mapping schema | 映射归因 |
| `decision_suggestions.json` | ☐ YES / ☐ NO | human review only | 禁止生产自动消费 |

### 5.3 Git 入仓规则

```text
真实 reports/outcome/* 不得提交到 git。
真实 logs/* 不得提交到 git。
测试输出只能写入 /tmp 或 pytest tmp_path。
```

---

## 6. Fixtures 覆盖验收

`tests/fixtures/stage6/outcome_logs/` 至少应覆盖以下场景。

| 场景 | fixture 存在 | expected outcome 存在 | 备注 |
|---|---:|---:|---|
| EXECUTE LONG hit | ☐ YES / ☐ NO | ☐ YES / ☐ NO | valid resolved outcome |
| EXECUTE LONG miss | ☐ YES / ☐ NO | ☐ YES / ☐ NO | valid resolved outcome |
| EXECUTE SHORT hit | ☐ YES / ☐ NO | ☐ YES / ☐ NO | short 方向正确 |
| EXECUTE SHORT miss | ☐ YES / ☐ NO | ☐ YES / ☐ NO | short 方向正确 |
| WATCH correct_watch | ☐ YES / ☐ NO | ☐ YES / ☐ NO | 未错过机会 |
| WATCH missed_opportunity | ☐ YES / ☐ NO | ☐ YES / ☐ NO | 错过机会 |
| WATCH neutral_watch | ☐ YES / ☐ NO | ☐ YES / ☐ NO | 低证据 / 不足样本 |
| BLOCK correct_block | ☐ YES / ☐ NO | ☐ YES / ☐ NO | 正确阻断 |
| BLOCK overblocked | ☐ YES / ☐ NO | ☐ YES / ☐ NO | 过度阻断 |
| BLOCK neutral_block | ☐ YES / ☐ NO | ☐ YES / ☐ NO | 无优势 / 不足样本 |
| PENDING_CONFIRM audit-only | ☐ YES / ☐ NO | ☐ YES / ☐ NO | 不进入 primary stats |
| UNKNOWN audit-only | ☐ YES / ☐ NO | ☐ YES / ☐ NO | 不进入 primary stats |
| invalid_join_key | ☐ YES / ☐ NO | ☐ YES / ☐ NO | invalid，不进入 primary stats |
| benchmark_missing | ☐ YES / ☐ NO | ☐ YES / ☐ NO | 不进入 alpha 主统计 |
| market_data_missing | ☐ YES / ☐ NO | ☐ YES / ☐ NO | degraded / invalid |
| insufficient_sample | ☐ YES / ☐ NO | ☐ YES / ☐ NO | monotonicity 不得 passed |
| mock/test source | ☐ YES / ☐ NO | ☐ YES / ☐ NO | 不进入 primary stats |

---

## 7. 归因规则验收

### 7.1 EXECUTE 规则

| 规则 | 状态 | 备注 |
|---|---:|---|
| EXECUTE LONG hit / miss 判定正确 | ☐ PASS / ☐ FAIL | 按 policy / expected_outcomes |
| EXECUTE SHORT hit / miss 判定正确 | ☐ PASS / ☐ FAIL | short 方向必须反向计算 |
| neutral 不得误标 hit / miss | ☐ PASS / ☐ FAIL | 低证据 / 不足样本 |
| pending 不得提前 hit / miss | ☐ PASS / ☐ FAIL | pending_t1 / t5 / t20 |
| invalid 不进入 primary stats | ☐ PASS / ☐ FAIL | invalid_join_key 等 |

### 7.2 WATCH 规则

| 规则 | 状态 | 备注 |
|---|---:|---|
| correct_watch 判定正确 | ☐ PASS / ☐ FAIL | WATCH 后无有效机会 |
| missed_opportunity 判定正确 | ☐ PASS / ☐ FAIL | WATCH 后出现显著机会 |
| neutral_watch 判定正确 | ☐ PASS / ☐ FAIL | 低证据 / 样本不足 |
| WATCH 低证据不得强行归因 | ☐ PASS / ☐ FAIL | neutral_watch |

### 7.3 BLOCK 规则

| 规则 | 状态 | 备注 |
|---|---:|---|
| correct_block 判定正确 | ☐ PASS / ☐ FAIL | BLOCK 后无机会或避免损失 |
| overblocked 判定正确 | ☐ PASS / ☐ FAIL | BLOCK 后机会显著 |
| neutral_block 判定正确 | ☐ PASS / ☐ FAIL | 无优势 / 样本不足 |
| BLOCK no-advantage 不能算 overblocked | ☐ PASS / ☐ FAIL | neutral_block |

### 7.4 Failure Reason 规则

| failure_reason | 状态 | 备注 |
|---|---:|---|
| `mapping_wrong` | ☐ PASS / ☐ FAIL | 映射错误 |
| `timing_wrong` | ☐ PASS / ☐ FAIL | 时间窗口错误 |
| `market_rejected` | ☐ PASS / ☐ FAIL | 市场拒绝 |
| `source_bad` | ☐ PASS / ☐ FAIL | 来源质量差 |
| `risk_too_strict` | ☐ PASS / ☐ FAIL | 风控过严 |
| `risk_too_loose` | ☐ PASS / ☐ FAIL | 风控过松 |
| `provider_bad` | ☐ PASS / ☐ FAIL | provider 异常 |
| `market_data_bad` | ☐ PASS / ☐ FAIL | 市场数据异常 |
| `score_not_predictive` | ☐ PASS / ☐ FAIL | 评分无预测性 |
| `gate_rule_wrong` | ☐ PASS / ☐ FAIL | Gate 规则错误 |
| `execution_missing` | ☐ PASS / ☐ FAIL | 执行缺失 |
| `join_key_missing` | ☐ PASS / ☐ FAIL | join key 缺失 |
| `benchmark_missing` | ☐ PASS / ☐ FAIL | benchmark 缺失 |
| `insufficient_sample` | ☐ PASS / ☐ FAIL | 样本不足 |

---

## 8. Primary Stats 排除规则验收

以下记录不得进入 primary stats。

| 排除项 | 状态 | 备注 |
|---|---:|---|
| `data_quality=invalid` | ☐ PASS / ☐ FAIL | 必须排除 |
| `data_quality=pending` | ☐ PASS / ☐ FAIL | 必须排除 |
| `PENDING_CONFIRM` | ☐ PASS / ☐ FAIL | audit-only |
| `UNKNOWN` | ☐ PASS / ☐ FAIL | audit-only |
| pending outcome | ☐ PASS / ☐ FAIL | 不得 hit/miss |
| mock/test source | ☐ PASS / ☐ FAIL | 不得污染主统计 |
| `benchmark_missing` | ☐ PASS / ☐ FAIL | 不进入 alpha 主统计 |
| insufficient sample | ☐ PASS / ☐ FAIL | monotonicity 不得 passed |

---

## 9. Metric Dictionary / Policy 单一真源验收

| 检查项 | 状态 | 备注 |
|---|---:|---|
| 所有阈值来自 `configs/outcome_scoring_policy.yaml` | ☐ PASS / ☐ FAIL | 禁止 Python 硬编码 |
| 所有 summary 指标已注册在 `configs/metric_dictionary.yaml` | ☐ PASS / ☐ FAIL | Stage6 metrics |
| legacy Stage4/5 metrics 未被破坏 | ☐ PASS / ☐ FAIL | `ai_confidence` 等保留 |
| failure reason enum 与 schema 一致 | ☐ PASS / ☐ FAIL | 三方一致 |
| output file 字段与 metric_dictionary 可追踪 | ☐ PASS / ☐ FAIL | summary/report |

---

## 10. Idempotency 验收

必须通过：

```bash
python3 -m pytest -q tests/test_outcome_idempotency.py
```

验收要求：

| 检查项 | 状态 | 备注 |
|---|---:|---|
| 同一输入重复运行输出一致 | ☐ PASS / ☐ FAIL | hash / json 比较 |
| 同一 key 不重复写入冲突记录 | ☐ PASS / ☐ FAIL | opportunity_id / trace_id |
| 输出顺序确定性 | ☐ PASS / ☐ FAIL | deterministic ordering |
| 无时间戳随机污染测试输出 | ☐ PASS / ☐ FAIL | created_at 除外需可控 |

---

## 11. Replay Consistency 验收

必须通过：

```bash
python3 -m pytest -q tests/test_outcome_replay_consistency.py
```

验收要求：

| 检查项 | 状态 | 备注 |
|---|---:|---|
| replay 后 outcome 一致 | ☐ PASS / ☐ FAIL | 同输入同输出 |
| join key 稳定 | ☐ PASS / ☐ FAIL | opportunity_id / trace_id |
| orphan replay 不进入 primary stats | ☐ PASS / ☐ FAIL | orphan_replay |
| replay missing decision 可审计 | ☐ PASS / ☐ FAIL | log_trust_report |

---

## 12. Score Monotonicity 验收

| 检查项 | 状态 | 备注 |
|---|---:|---|
| `outcome_by_score_bucket.json` 生成 | ☐ PASS / ☐ FAIL | bucket 输出 |
| `score_monotonicity_report.json` 生成 | ☐ PASS / ☐ FAIL | 单调性报告 |
| 样本不足时 status = `insufficient_sample` | ☐ PASS / ☐ FAIL | 不得 passed |
| bucket 顺序固定 | ☐ PASS / ☐ FAIL | 80_PLUS / 60_79 / 40_59 / LT_40 |
| score bucket schema validate 通过 | ☐ PASS / ☐ FAIL | additionalProperties:false |

---

## 13. Alpha / Benchmark 验收

| 检查项 | 状态 | 备注 |
|---|---:|---|
| benchmark_return_t5 可计算 | ☐ PASS / ☐ FAIL | benchmark 存在时 |
| sector_relative_alpha_t5 可计算 | ☐ PASS / ☐ FAIL | sector benchmark 存在时 |
| benchmark_missing 不进入 alpha 主统计 | ☐ PASS / ☐ FAIL | must exclude |
| alpha_report.json 可生成 | ☐ PASS / ☐ FAIL | 报告输出 |
| LONG / SHORT alpha 方向正确 | ☐ PASS / ☐ FAIL | short 方向需特别检查 |

---

## 14. Log Trust / Mapping Attribution 验收

| 检查项 | 状态 | 备注 |
|---|---:|---|
| `log_trust_report.json` 可生成 | ☐ PASS / ☐ FAIL | 日志可信度 |
| `mapping_attribution.jsonl` 可生成 | ☐ PASS / ☐ FAIL | 映射归因 |
| `join_key_missing` 可落盘 | ☐ PASS / ☐ FAIL | trace_id nullable |
| mapping_failure_reason enum 有效 | ☐ PASS / ☐ FAIL | schema validate |
| provider failure 不伪造数据 | ☐ PASS / ☐ FAIL | provider_bad / market_data_bad |

---

## 15. Decision Suggestions 验收

| 检查项 | 状态 | 备注 |
|---|---:|---|
| `decision_suggestions.json` 可生成 | ☐ PASS / ☐ FAIL | human review only |
| 不被 production execution 自动消费 | ☐ PASS / ☐ FAIL | 硬约束 |
| 不改 final_action | ☐ PASS / ☐ FAIL | 禁止语义漂移 |
| 建议项可追踪到 outcome evidence | ☐ PASS / ☐ FAIL | audit trail |

---

## 16. 必跑测试命令

PR-7 Final 必须贴出以下命令结果。

```bash
python3 -m pytest -q tests/test_opportunity_outcome_schema.py
python3 -m pytest -q tests/test_stage6_metric_dictionary.py
python3 -m pytest -q tests/test_outcome_attribution_engine.py
python3 -m pytest -q tests/test_outcome_idempotency.py
python3 -m pytest -q tests/test_outcome_replay_consistency.py
python3 scripts/system_healthcheck.py --mode dev
```

| 命令 | 结果 | 证据 |
|---|---:|---|
| `test_opportunity_outcome_schema.py` | ☐ PASS / ☐ FAIL | `<paste>` |
| `test_stage6_metric_dictionary.py` | ☐ PASS / ☐ FAIL | `<paste>` |
| `test_outcome_attribution_engine.py` | ☐ PASS / ☐ FAIL | `<paste>` |
| `test_outcome_idempotency.py` | ☐ PASS / ☐ FAIL | `<paste>` |
| `test_outcome_replay_consistency.py` | ☐ PASS / ☐ FAIL | `<paste>` |
| `system_healthcheck.py --mode dev` | ☐ PASS / ☐ FAIL | `<paste>` |

---

## 17. 最低验收指标

| 指标 | 最低要求 | 实际值 | 状态 |
|---|---:|---:|---:|
| outcome coverage | `>= 95%` | `100%` | ☐ PASS / ☐ FAIL |
| execute coverage | `100%` | `100%` | ☐ PASS |
| schema validate | `PASS` | `PASS` | ☐ PASS |
| idempotency | `PASS` | `PASS` | ☐ PASS |
| replay consistency | `PASS` | `PASS` | ☐ PASS |
| failure reason coverage | `>= 95%` | `0.25` | ☐ FAIL |
| score monotonicity | `PASS or insufficient_sample when applicable` | `insufficient_sample` | ☐ PASS |
| healthcheck | `PASS or unrelated known issue documented` | `OVERALL GREEN with unrelated canary/data YELLOW note` | ☐ PASS |

---

## 18. 风险复核

| 风险 | 是否发生 | 处理 |
|---|---:|---|
| outcome_report.md 缺失 | YES | REQUEST CHANGES |
| failure_reason_coverage_rate 未达标 | YES | REQUEST CHANGES |
| join_key_missing 与 join_key_valid_count 口径疑点 | YES | NEEDS FOLLOW-UP |
| Python 中硬编码阈值 | NO | N/A |
| invalid 进入 primary stats | NO | N/A |
| pending 提前 hit/miss | NO | N/A |
| mock/test 进入 primary stats | NO | N/A |
| PENDING_CONFIRM / UNKNOWN 进入 primary stats | NO | N/A |
| benchmark_missing 进入 alpha 主统计 | NO | N/A |
| score monotonicity 样本不足仍 passed | NO | N/A |
| 真实 reports/outcome 入仓 | NO | N/A |
| 真实 logs 入仓 | NO | N/A |
| 改 Gate / execution / workflow_runner / final_action | NO | N/A |

---

## 19. A / B / C 三方 Review

### 19.1 A Review — Contract / Schema / Boundary

Status: `REQUEST CHANGES`

| 检查项 | 状态 | 备注 |
|---|---:|---|
| Schema drift | PASS | PR104 为 docs-only，未引入 schema drift |
| Policy single source | PASS | `configs/outcome_scoring_policy.yaml` 未被修改 |
| Registry consistency | PASS | `module-registry.yaml` 未被修改 |
| Metric dictionary consistency | PASS | 本 PR 未改动 metric dictionary，需结合 B/C 闭环确认最终一致性 |
| No runtime boundary violation | PASS | 未改 runtime / Gate / execution / final_action |
| PR 正式审查模板 v2.1 已执行 | PASS |  |

Reviewer: `A`
Date: `2026-04-30`
Decision: `REQUEST CHANGES`

结论摘要：
1. PR104 本身未引入 schema drift。
2. `outcome_scoring_policy.yaml` 未被修改，阈值单一真源未被破坏。
3. `module-registry.yaml` 未被修改，registry 一致性未被破坏。
4. metric_dictionary 未被本 PR 修改，但最终指标一致性需结合 B/C 输出闭环。
5. rule/test mapping 未被本 PR 回退。
6. PR104 范围为 docs-only，未改 runtime / Gate / execution / final_action。
7. 唯一阻断项是 `outcome_report.md` contract status 未闭环，默认 CLI 当前仍为 9/10。
8. 需要后续明确这是 engine 缺陷还是模板要求过高。

---

### 19.2 B Review — Attribution / Metrics

Status: `REQUEST CHANGES`

| 检查项 | 状态 | 备注 |
|---|---:|---|
| EXECUTE hit/miss rules | PASS | 16 条 EXECUTE records，标签仅为 hit / miss / neutral，LONG / SHORT 方向正确 |
| WATCH attribution | PASS | 3 条 WATCH records，标签仅为 correct_watch / missed_opportunity / neutral_watch |
| BLOCK attribution | PASS | 3 条 BLOCK records，标签仅为 correct_block / neutral_block / overblocked |
| Alpha / benchmark | PASS | `alpha_eligible_count=15`，`mean_alpha_t5=0.003`，`mean_benchmark_return_t5=0.005` |
| Failure reasons | FAIL | `failure_reason_coverage_rate=0.25`，低于 `>= 0.95` 阈值 |
| Primary/degraded/invalid/pending handling | PASS | `valid=15`、`degraded=4`、`invalid=4`、`pending=1`，且未污染 primary stats |
| Score monotonicity | PASS | `insufficient_sample`，`total_samples=15`，bucket `80_PLUS` 仅 3 samples |

Reviewer: `B`
Date: `2026-04-30`
Decision: `REQUEST CHANGES`

结论摘要：
1. EXECUTE 规则：PASS。
   - 16 条 EXECUTE records。
   - 标签只包含 `hit` / `miss` / `neutral`。
   - LONG / SHORT 样本方向正确。
2. WATCH 规则：PASS。
   - 3 条 WATCH records。
   - 标签只包含 `correct_watch` / `missed_opportunity` / `neutral_watch`。
3. BLOCK 规则：PASS。
   - 3 条 BLOCK records。
   - 标签只包含 `correct_block` / `neutral_block` / `overblocked`。
4. Primary stats 排除逻辑：PASS。
   - `valid=15`
   - `degraded=4`
   - `invalid=4`
   - `pending=1`
   - invalid / pending records 无 `outcome_label`
   - `PENDING_CONFIRM` / `UNKNOWN` `outcome_label=None`
   - `execute_outcome_coverage_rate=1.0`
   - `resolved_outcome_coverage_rate=1.0`
5. Failure reason coverage：FAIL。
   - `failure_reason_coverage_rate=0.25`
   - 阈值要求 `>= 0.95`
   - 这是 B Review 的主要 `REQUEST CHANGES` 原因。
6. Alpha / benchmark：PASS。
   - `alpha_eligible_count=15`
   - `mean_alpha_t5=0.003`
   - `mean_benchmark_return_t5=0.005`
   - 未发现 B 范围 blocker。
7. Score monotonicity：PASS as `insufficient_sample`。
   - `status=insufficient_sample`
   - `total_samples=15`，低于 minimum total 30
   - bucket `80_PLUS` 只有 3 samples，低于 minimum 10
8. Log trust / mapping attribution：PASS with note。
   - `total_records=24`
   - `join_key_valid_count=24`
   - `join_key_invalid_count=0`
   - `mapping_attribution` rows=24
   - 但 `failure_reason_distribution` 中出现 `join_key_missing=2`，而 `log_trust_report` 显示 `join_key_invalid_count=0`，需要后续解释统计口径。
9. Decision suggestions：PASS。
   - `decision_suggestions.json` 包含 `review_block_rules` / `review_watch_rules`
   - `requires_human_review=true`
   - 未进入生产执行链路。

---

### 19.3 C Review — Engine / Tests / Reports

Status: `REQUEST CHANGES`

| 检查项 | 状态 | 备注 |
|---|---:|---|
| Engine CLI | PASS | processed 24 opportunities |
| Fixtures | PASS | 现有 fixtures 驱动了完整 B/C 取证 |
| Reports generated | FAIL / PARTIAL | 默认 CLI 仅生成 9/10，缺少 `outcome_report.md` |
| Schema validation | PASS | 相关 pytest 通过 |
| Idempotency | PASS | `tests/test_outcome_idempotency.py` 通过 |
| Replay consistency | PASS | `tests/test_outcome_replay_consistency.py` 通过 |
| No runtime artifacts committed | PASS | `logs/system_health_daily_report.md` 已清理，未入仓 |

Reviewer: `C`
Date: `2026-04-30`
Decision: `REQUEST CHANGES`

结论摘要：
1. Engine CLI：PASS。
   - 默认 CLI 可运行。
   - `processed 24 opportunities`。
2. Generated files：FAIL / PARTIAL。
   - 默认 CLI 只生成 9 个文件。
   - 缺失 `outcome_report.md`。
   - 当前输出为 9/10。
3. Pytest：PASS。
   - `tests/test_opportunity_outcome_schema.py`：5 passed
   - `tests/test_stage6_metric_dictionary.py`：5 passed
   - `tests/test_outcome_attribution_engine.py`：34 passed
   - `tests/test_outcome_idempotency.py`：5 passed
   - `tests/test_outcome_replay_consistency.py`：7 passed
4. Healthcheck：PASS with note。
   - 当前 `python3 scripts/system_healthcheck.py --mode dev` 可完成。
   - Result: `OVERALL: GREEN`
   - project stage YELLOW 来自 canary/data replay-only 或 fallback evidence。
   - 不属于 Stage6 engine regression。
5. `outcome_report.md` root cause：
   - 根因是 implementation behavior。
   - `scripts/outcome_attribution_engine.py` 只有显式传入 `--emit-report` 才生成 `outcome_report.md`。
   - 默认 final validation CLI 路径只生成 9/10。
6. Runtime artifact cleanup：
   - `logs/system_health_daily_report.md` 曾作为本地 untracked runtime artifact 出现。
   - 已本地删除。
   - 未进入 PR104 scope。
7. Files changed scope：
   - PR104 changed file scope 仅 `docs/review/stage6_pr7_final_signoff.md`。
   - 未修改 engine / tests / schemas / configs / Gate / execution / final_action。

---

## 20. 最终裁决

```text
Final Decision: REQUEST CHANGES
```

### REQUEST CHANGES 结论

A/B/C Review 均为 `REQUEST CHANGES`。当前 PR104 不满足 Final PASS 条件，不能 Ready for Review，不能合并。后续应新开工程修复 PR 修复 Follow-up Fix List 中的 P0/P1 问题。修复 PR 合并后，回到 PR104 重新执行 A/B/C 复审。

### Follow-up Fix List for Stage6 Re-review

#### P0-1：默认 CLI 不生成 `outcome_report.md`

- 来源：A Review / C Review
- 当前状态：默认 CLI 只生成 9/10 输出文件
- 根因：`outcome_report.md` 只有在 `--emit-report` 显式传入时生成
- 修复目标：默认 final validation CLI 路径生成 `outcome_report.md`，输出达到 10/10
- 建议修复文件：
  - `scripts/outcome_attribution_engine.py`
  - `tests/test_outcome_attribution_engine.py`

#### P0-2：`failure_reason_coverage_rate` 不达标

- 来源：B Review
- 当前值：`0.25`
- 阈值要求：`>= 0.95`
- 修复目标：
  - degraded / invalid / pending / excluded records 必须具备 `failure_reasons`
  - `failure_reasons` 非空时必须具备 `primary_failure_reason`
  - `failure_reason_coverage_rate >= 0.95`
- 建议修复文件：
  - `scripts/outcome_attribution_engine.py`
  - `tests/test_outcome_attribution_engine.py`
  - `tests/fixtures/stage6/outcome_logs/*`

#### P1-1：`join_key_missing` 与 `join_key_valid_count` 口径需要解释

- 来源：B Review
- 当前现象：
  - `failure_reason_distribution.json` 中出现 `join_key_missing=2`
  - `log_trust_report` 显示 `join_key_valid_count=24`、`join_key_invalid_count=0`
- 修复目标：
  - 明确这是不同统计层级，或修正统计逻辑
  - 报告口径必须可解释、可审计
- 建议修复文件：
  - `scripts/outcome_attribution_engine.py`
  - `tests/test_outcome_attribution_engine.py`

---

## 21. Final Sign-off 记录

| 角色 | 姓名 | 决定 | 日期 | 备注 |
|---|---|---|---|---|
| A / Contract Reviewer | `A` | `REQUEST CHANGES` | `2026-04-30` | `outcome_report.md` contract status 未闭环 |
| B / Attribution Reviewer | `B` | `REQUEST CHANGES` | `2026-04-30` | `failure_reason_coverage_rate=0.25` |
| C / Engineering Reviewer | `C` | `REQUEST CHANGES` | `2026-04-30` | 默认 CLI 仅 9/10，缺少 `outcome_report.md` |
| Final Owner | `TBD` | `REQUEST CHANGES` | `2026-04-30` | 待后续修复后复审 |

---

## 22. 最终一句话

```text
PR-7 Final 通过后，Stage6 Outcome Attribution / Signal Quality 当前范围正式完成。
后续若需要 dashboard、生产监控、评分反馈、release hardening，应另开增强 PR，不再混入 PR-7 Final。
```
