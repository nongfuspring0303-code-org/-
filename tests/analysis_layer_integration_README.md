# 分析层集成测试交接说明

## 1. 目标

本文件面向成员C，用于执行 `T3.6 分析层集成测试`。  
当前成员B已完成以下交接资产：

- 正式 schema：`schemas/*.json` 中分析层 10 个文件
- 正式脚本：`scripts/lifecycle_manager.py`
- 正式脚本：`scripts/fatigue_calculator.py`
- 正式脚本：`scripts/conduction_mapper.py`
- 正式脚本：`scripts/market_validator.py`
- 正式脚本：`scripts/signal_scorer.py`
- 基线测试运行器：`tests/run_analysis_layer_tests.py`
- 集成输入包：`tests/analysis_layer_integration_inputs.yaml`

## 2. 当前可执行命令

在项目根目录运行：

```bash
python tests/run_analysis_layer_tests.py
```

当前基线结果应为：

```text
PASSED 22 checks
```

## 3. 交接范围

成员B已完成：

- 生命周期状态机首版实现
- 疲劳度计算首版实现
- 传导映射首版实现
- 市场验证首版实现
- 信号评分首版实现
- YAML 用例转可执行运行器
- 分析层最小链路验证

成员C需继续完成：

- 扩展分析层集成测试样例
- 输出分析层测试报告
- 识别边界回归和跨模块断链
- 为后续执行层提供稳定输入样例

## 4. 推荐执行顺序

1. 先运行基线测试：

```bash
python tests/run_analysis_layer_tests.py
```

2. 再按 `tests/analysis_layer_integration_inputs.yaml` 逐条执行集成链路：

- `AL-CHAIN-001`: 关税事件 happy path
- `AL-CHAIN-002`: 高疲劳 Watch 模式阻断
- `AL-CHAIN-003`: E4 + 相关性崩溃

3. 对每条链路记录：

- 输入是否完整
- 上游输出是否满足下游输入契约
- 链路是否中断
- 实际输出与期望是否一致
- 是否需要人工复核

## 5. 当前已知限制

- 当前环境中的 `pytest` 与 Python 3.13 不兼容，故暂不以 pytest 作为主运行入口。
- 当前 `ConductionMapper` 仍是规则版实现，不是完整知识库版本。
- 当前 `MarketValidator` 使用阈值规则，不是行情引擎直连版本。
- 当前 `SignalScorer` 使用项目当前阶段可执行口径，不代表最终参数校准版本。

## 6. 成员C新增用例规范

新增链路时请遵守以下规则：

- 不覆盖现有 `AL-CHAIN-001` 到 `AL-CHAIN-003`
- 新增链路统一追加到 `tests/analysis_layer_integration_inputs.yaml`
- 输入字段必须符合 `schemas/*.json`
- 若发现字段变更，必须同步更新：
  - `schemas/*.json`
  - `tests/*.yaml`
  - `module-registry.yaml`
  - `README.md` 或 `04-任务总计划.md`

## 7. 交付建议

成员C完成 `T3.6` 时，建议测试报告至少包含：

- 执行日期
- 执行环境
- 基线运行结果
- 新增链路清单
- 失败链路清单
- 阻塞点与责任人
- 是否满足进入执行层前置条件
