# 分析层 coverage 统计

## 1. 统计方式

- 执行入口：`python tests/run_analysis_layer_coverage.py`
- 统计工具：Python 标准库 `trace`
- 说明：当前环境无可用 `coverage` 包，因此本报告为近似 coverage

## 2. 统计结果

- `conduction_mapper.py`: 29/38 (76.3%)
- `fatigue_calculator.py`: 37/46 (80.4%)
- `lifecycle_manager.py`: 52/67 (77.6%)
- `market_validator.py`: 42/49 (85.7%)
- `signal_scorer.py`: 60/72 (83.3%)
- 总计：220/272 (80.9%)

## 3. 结论

- 当前分析层功能性验证已通过
- 当前近似 coverage **已达到** 项目目标 `>= 80%`
- 当前结论：分析层测试覆盖达到阶段验收门槛

## 4. 建议优先补测方向

- LifecycleManager：仍可继续补充 Archived 等后续状态分支
- ConductionMapper：仍可继续补充更多类别的规则映射
- 统一超时/重试中间层需继续在真实外部依赖场景中压测
