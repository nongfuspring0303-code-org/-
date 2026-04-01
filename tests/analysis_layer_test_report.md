# 分析层测试报告

## 1. 基本信息

- 测试阶段：T3.6 分析层集成测试
- 执行日期：2026-03-31
- 执行人：成员B
- 测试范围：
  - LifecycleManager
  - FatigueCalculator
  - ConductionMapper
  - MarketValidator
  - SignalScorer

## 2. 执行环境

- Python：3.13
- 运行入口：
  - `python tests/run_analysis_layer_tests.py`
  - `python tests/run_analysis_layer_integration.py`

## 3. 执行结果

### 3.1 基线模块测试

- 执行命令：`python tests/run_analysis_layer_tests.py`
- 结果：`PASSED 39 checks`

覆盖内容：

- 5 个分析层模块 YAML 用例执行
- 正常用例
- 异常用例
- 边界用例
- 最小链路验证

### 3.2 集成链路测试

- 执行命令：`python tests/run_analysis_layer_integration.py`
- 结果：`PASSED 3 integration chains`

通过链路：

- `AL-CHAIN-001`：关税事件 happy path
- `AL-CHAIN-002`：高疲劳 Watch 模式阻断
- `AL-CHAIN-003`：E4 + 相关性崩溃

## 4. 关键验证结论

- 生命周期模块能够区分 `Detected / Active / Exhaustion / Dead`
- 疲劳度模块能够输出 `Fatigue_Final = max(Fatigue_Category, Fatigue_Tag)`
- 传导映射模块能够输出宏观→板块→个股路径，并在信息不足时抑制直接个股映射
- 市场验证模块能够输出 `A1` 与五项分项得分
- 信号评分模块能够处理：
  - `watch_mode_block`
  - `E4_weight_adjustment`
  - `correlation_breakdown_A1.5_discount`
  - `policy_intervention_direction_flip`

## 5. 当前已知限制

- 当前环境中的 `pytest` 与 Python 3.13 不兼容，故本轮测试使用标准库运行器替代 pytest 主入口。
- `ConductionMapper` 当前仍为规则版实现，尚未接入完整知识库或外部宏观数据源。
- `MarketValidator` 当前使用静态阈值规则，尚未接入真实行情引擎。
- `SignalScorer` 当前为项目阶段版参数口径，后续仍可根据回测与评审继续校准。
- coverage 使用标准库 `trace` 近似统计，当前结果为 `80.9%`。

## 6. 结论

- T3.1 至 T3.5 已具备可执行、可验证、可交接状态。
- T3.6 分析层集成测试已完成首轮执行。
- 当前结果满足进入下一阶段联调与执行层开发的前置条件。
- 二次合格性验收已通过。
