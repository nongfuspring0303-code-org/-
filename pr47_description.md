## 概述

本 PR 实现了事件驱动交易系统的状态持久化功能，让同一事件能够随时间推进生命周期状态，并增强 FatigueCalculator 以支持 SQLite 集成和配置化阈值。

## 核心功能

### 1. SQLite 状态存储模块 (Commit 40bd872)

**新增文件：**
- `scripts/state_store.py` - SQLite 持久化状态存储
- `tests/test_state_store.py` - 7 个测试用例

**修改文件：**
- `scripts/full_workflow_runner.py` - 集成状态读写
- `.gitignore` - 忽略 `data/*.db` 数据库文件

**功能特性：**
- 存储/检索事件生命周期状态（Detected → Verified → Active → Exhaustion）
- 支持 retry_count 计数
- 元数据 JSON 序列化
- upsert 操作（插入或更新）

**解决了什么问题：**
之前每次运行都从头计算生命周期状态，同一事件无论间隔多久都会返回相同状态。现在实现了真正的有状态推进：

```
运行 1: 新事件 → Detected → 已存储
运行 2: 同一事件 (6小时后) → Verified → 已存储
运行 3: 同一事件 (30小时后) → Active → 已存储
运行 4: 同一事件 (50小时后) → Exhaustion → 已存储
```

### 2. FatigueCalculator 增强 (Commit 6aeb243)

**新增文件：**
- `configs/fatigue_config.yaml` - 疲劳度配置文件

**修改文件：**
- `scripts/fatigue_calculator.py` - SQLite 集成 + 配置化阈值
- `scripts/full_workflow_runner.py` - 传递 state_store 实例

**修复的问题：**

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 🔴 tag_active_counts 默认值不反映真实活跃度 | 硬编码默认值 | 从 SQLite 查询实际活跃事件数 |
| 🟡 _score_from_count 阈值硬编码 | 硬编码 2→0, 3→20, 4→40... | 移至 `fatigue_config.yaml` 配置文件 |
| 🟡 Dead 事件重置天数固定 | 硬编码 30 天 | 配置化 `dead_event_reset_days` |

**新增功能：**
- SQLite 集成：查询 `event_states` 表获取真实活跃事件数
- 配置化所有阈值：折扣阈值、看守模式阈值、重置天数
- 向后兼容：无配置时使用默认值

**配置项示例：**
```yaml
count_to_fatigue_score:
  2: 0
  3: 20
  4: 40
  5: 60
  6: 80
  7: 100

fatigue_discount_threshold: 70
fatigue_discount_factor: 0.5
watch_mode_threshold: 85
dead_event_reset_days: 30
take_profit_penalty_factor: 0.5
```

## 测试验证

✅ **所有测试通过：**
- `tests/test_state_store.py` - 7 个测试全通过
- `tests/test_analysis_modules.py` - 5 个测试全通过
- `tests/test_full_workflow.py` - 1 个测试全通过
- 总计 42 个 fatigue/workflow/state 相关测试全通过

✅ **Standalone 模式验证：**
```bash
python3 scripts/fatigue_calculator.py
# 输出: fatigue_final=100, watch_mode=True, rule_version=fatigue_v2
```

✅ **端到端验证：**
```bash
python3 scripts/full_workflow_runner.py
# 成功运行，状态持久化
```

## 文件变更统计

```
Commit 40bd872:
 .gitignore                      |   3 +
 scripts/full_workflow_runner.py |  24 ++++++-
 scripts/state_store.py          | 121 +++++++++++++++++++++++++++++++
 tests/test_state_store.py       | 153 ++++++++++++++++++++++++++++++++++++++++
 4 files changed, 299 insertions(+), 2 deletions(-)

Commit 6aeb243:
 configs/fatigue_config.yaml     |  32 ++++++++++
 scripts/fatigue_calculator.py   | 128 +++++++++++++++++++++++++++++++++-------
 scripts/full_workflow_runner.py |  13 +++-
 3 files changed, 150 insertions(+), 23 deletions(-)

总计: 7 files changed, 449 insertions(+), 25 deletions(-)
```

## 后续改进建议

1. 添加状态过期清理机制（自动删除 >90 天的状态）
2. 考虑添加状态迁移脚本（当 schema 变更时）
3. 监控数据库大小，添加健康检查
4. 为 fatigue_config.yaml 添加热重载支持

🤖 Generated with [Qoder](https://qoder.com)