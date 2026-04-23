# 阶段 3B：A 侧契约与 Gate 收口签字稿
**版本**：v1.0  
**日期**：2026-04-23  
**角色**：A（收口主责） / B（3B 主修） / C（日志与联动配合）  
**适用阶段**：阶段 3B（sector / ticker / 伪兜底修复）

## 1. 目的与口径

本文件用于闭环阶段 3B 的 A 侧职责（见阶段矩阵 8.3 / 8.6 / 8.7）：

1. 确认 `sector / ticker / theme_tags` 字段契约边界。
2. 确认 fallback 不再伪装为正式输出。
3. 确认进入 Gate 前结构完整且可判定。
4. 给出 A 侧可执行测试锚点，作为签字依据。

本文件是阶段 3B 的 A-side sign-off 依据，不替代 B 主责实现文档。

## 2. A 侧冻结契约边界

### 2.1 sector 真源边界

- `sectors[]` / `sector_impacts[].sector` 最终输出必须来自白名单真源：
  - `configs/sector_impact_mapping.yaml`
- 非白名单值不得进入正式输出层；可进入观测或手工复核路径，但不得伪装为正式可交易结论。

### 2.2 ticker 真源边界

- `stock_candidates[].symbol` 与机会层输出 ticker 必须可追溯到真源池：
  - `configs/premium_stock_pool.yaml`
- 不允许 `unknown -> 任意 ticker` 自动补全。
- 不允许回退路径伪造 `JPM` / `SPY` 作为“默认正式候选”。

### 2.3 theme_tags 契约边界

- `theme_tags` 可作为解释与映射辅助输入，但不得绕过 `sector/ticker` 真源边界。
- 任何仅由 `theme_tags` 推导出的候选，若缺少真源映射依据，必须降级到 `needs_manual_review=true`。

### 2.4 fallback 与正式输出边界

- fallback、template collapse、兜底路径均属于“非正式路径”。
- 非正式路径必须满足：
  - `needs_manual_review=true`
  - 不输出伪装成正式交易建议的 `sector_impacts` / `stock_candidates`
  - 不得与正式路径使用同一语义标签。

## 3. Gate 前结构完整性要求

进入 Gate 之前，至少满足以下结构完整性：

1. `mapping_source` 明确可追溯（模板/规则/其他）；
2. `sector_impacts` 与 `stock_candidates` 的来源可追溯到真源；
3. 当真源不足时，必须显式落到人工复核路径；
4. 任何“看起来合理”的默认值不得直接越级为 EXECUTE 可用输入。

## 4. 规则到测试锚点（A 侧签字依据）

| Rule ID | Rule Statement | Test ID | Test Anchor |
| --- | --- | --- | --- |
| R-A-S3B-001 | `sectors[]` 最终输出必须白名单闭环。 | T-A-S3B-001 | `tests/test_member_b_stage3b_sector_ticker_integrity.py::test_stage3b_sectors_final_output_whitelist_only` |
| R-A-S3B-002 | `ticker_pool` 结果必须可追溯真源池，无依据时返回空机会。 | T-A-S3B-002 | `tests/test_member_b_stage3b_sector_ticker_integrity.py::test_stage3b_ticker_pool_requires_truth_source` |
| R-A-S3B-003 | 金融/JPM 伪兜底必须删除，失败路径不得伪装正式结果。 | T-A-S3B-003 | `tests/test_member_b_stage3b_sector_ticker_integrity.py::test_stage3b_financial_jpm_fallback_removed` |
| R-A-S3B-004 | template collapse 不得污染正式输出，必须进入人工复核。 | T-A-S3B-004 | `tests/test_member_b_stage3b_sector_ticker_integrity.py::test_stage3b_template_collapse_does_not_promote_failure_path` |
| R-A-S3B-005 | Stage3B 变更不得破坏 trace/join 审计链完整性。 | T-A-S3B-005 | `tests/test_member_c_stage3b_joint_review_evidence.py::test_stage3b_c_joint_review_trace_join_not_broken` |

## 5. A 侧签字条件

以下条件全部满足时，A 可对阶段 3B 签字：

- [ ] 范围纯度通过（PR 不混入与 3B 无关改动）
- [ ] `sectors[]` 非白名单占比 = 0
- [ ] ticker 候选全部可追溯真源池
- [ ] fallback 不伪装为正式输出
- [ ] Gate 前结构完整性可验证
- [ ] 规则-测试锚点可复跑且通过

## 6. 签字结论模板

> A-side sign-off: PASS / FAIL  
> 结论日期：YYYY-MM-DD  
> 对应 PR：#<number>  
> 证据：规则-测试锚点列表 + 关键日志/产物链接
