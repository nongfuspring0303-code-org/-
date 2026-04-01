# AI因子映射冻结文档 v1

## 目的

冻结 A 输出到 B 因子的映射口径，保证并行开发期间不漂移。

## 映射关系（v1）

- `evidence_score` -> `A0`
- `consistency_score` -> `A-1`
- `freshness_score` -> `A1`
- `confidence` -> `A1.5`
- `counter_signal_penalty` -> `A0.5`

## 版本字段

- `mapping_version`: `factor_map_v1`
- `schema_version`: `ai_factor_map_v1`

## 变更规则

1. 映射关系变更必须升级 `mapping_version`。
2. 变更必须同次更新：schema + tests/mocks + module-registry + 任务清单。
