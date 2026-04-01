# 事件驱动交易系统 (EDT) - OpenClaw 工作流框架

## 1. 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         EDT 工作流 - 端到端流程                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │  Input      │───▶│  Monitor   │───▶│  Analyst   │───▶│   Risk     │      │
│  │  Layer      │    │  Agent     │    │  Agent     │    │  Agent     │      │
│  │  (情报层)   │    │  (L0-L3)   │    │  (L4-L7)   │    │  (L8)      │      │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘      │
│        │                   │                   │                   │            │
│        ▼                   ▼                   ▼                   ▼            │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        决策优先级树 (Gates)                              │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │   │
│  │  │ G1:流动  │→│ G2:生命  │→│ G3:疲劳  │→│ G4:相关  │→│ G5:评分  │       │   │
│  │  │ 性黑洞   │  │ 周期     │  │ 度       │  │ 性崩溃   │  │ 执行     │       │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘       │   │
│  │     ↓            ↓            ↓            ↓            ↓                 │   │
│  │   禁止        强制平仓      禁止新开     A1.5折减     仓位分级            │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 2. 模块详解

### 2.1 Monitor Agent (L0-L3 情报层)

```
┌────────────────────────────────────────────────────────────────┐
│                    Monitor Agent - 事件对象构建                  │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  输入: 实时新闻流 / API / 手动录入                              │
│                                                                 │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐        │
│  │ 1.事件  │──▶│ 2.来源  │──▶│ 3.分类  │──▶│ 4.严重  │        │
│  │ 截获    │   │ 裁决    │   │ (A-G)   │   │ 度判定  │        │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘        │
│       │             │             │             │              │
│       ▼             ▼             ▼             ▼              │
│  VIX异动检测   A/B/C分级     七大类分类    E0-E4分级          │
│  关键词触发    升源验证      唯一ID分配    VIX/波动率锚点     │
│                                                                 │
│  输出: Event Object                                            │
│  {                                                             │
│    event_id: "ME-C-20260330-001.V1.0",                         │
│    source_rank: "A",                                           │
│    category: "C",  // 关税/贸易战                              │
│    severity: "E3",                                              │
│    detected_at: "2026-03-30T09:30:00Z",                        │
│    confidence: 85                                                │
│  }                                                             │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### 2.2 Analyst Agent (L4-L7 策略层)

```
┌────────────────────────────────────────────────────────────────┐
│                    Analyst Agent - 传导与评分                   │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  输入: Event Object + 宏观数据                                  │
│                                                                 │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐          │
│  │ 1.生命周期  │──▶│ 2.传导映射  │──▶│ 3.市场验证  │          │
│  │ 管理        │   │ (宏观→板块  │   │ (价格/量能  │          │
│  │             │   │  →个股)     │   │  联动)      │          │
│  └─────────────┘   └─────────────┘   └─────────────┘          │
│       │                   │                   │                │
│       ▼                   ▼                   ▼                │
│  Detected/Verified   7大宏观因子       A1评分(0-100)          │
│  Active/Continuation 资产/板块映射    联动性验证              │
│  Exhaustion/Dead    Narrative/Fact                                                │
│                     驱动模式                                                 │
│                                                                 │
│  ┌─────────────┐   ┌─────────────┐                            │
│  │ 4.预期差   │──▶│ 5.Score     │                            │
│  │ 计算       │   │ 量化评分    │                            │
│  └─────────────┘   └─────────────┘                            │
│       │                   │                                    │
│       ▼                   ▼                                    │
│  Gap=Reality-         Score = 0.25×A0                          │
│  Consensus           + 0.20×A-1                               │
│  (无共识用隐含预期)  + 0.25×A1                                │
│                       + 0.20×A1.5                             │
│                       - 0.10×A0.5                            │
│                                                                 │
│  输出: Strategy Signal                                         │
│  {                                                             │
│    lifecycle_state: "Active",                                  │
│    catalyst_state: "first_impulse",                            │
│    conduction: {macro: "...", sector: "...", stock: "..."},   │
│    A0: 30, A-1: 70, A1: 78, A1.5: 60, A0.5: 0,              │
│    fatigue_index: 45,                                          │
│    score: 72,                                                  │
│    direction: "long",                                          │
│    position_tier: "G2-标准执行"                                │
│  }                                                             │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### 2.3 Risk Agent (L8 执行层)

```
┌────────────────────────────────────────────────────────────────┐
│                    Risk Agent - 风控与执行                      │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  输入: Strategy Signal + 实时盘口                              │
│                                                                 │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐          │
│  │ 1.流动性   │──▶│ 2.决策闸门  │──▶│ 3.交易执行  │          │
│  │ 环境检测   │   │ 执行       │   │ (下单/风控) │          │
│  └─────────────┘   └─────────────┘   └─────────────┘          │
│       │                   │                   │                │
│       ▼                   ▼                   ▼                │
│  Green/Yellow/Red    G1-G6逐级检查    分批建仓/减仓            │
│  VIX/TED/FRA-OIS   一票否决逻辑     硬性/追踪/时间止损       │
│  相关性监控        超时自动降级      退出策略                │
│                                                                 │
│  输出: Execution Order                                         │
│  {                                                             │
│    action: "OPEN_LONG",                                        │
│    symbol: "XLF",  // 金融板块ETF                               │
│    quantity: 500,                                              │
│    entry_price: 42.50,                                          │
│    stop_loss: 41.00,  // -2R                                    │
│    take_profit: [44.00, 45.50, 47.00], // 1R/2R/3R           │
│    execution_mode: "STANDARD",                                 │
│    risk_level: "MEDIUM"                                         │
│  }                                                             │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

## 3. 决策优先级树 (核心)

```
输入事件
    │
    ├── G1: 流动性黑洞? ──────────────────────────▶ [禁止执行]
    │                                             
    ├── G2: Red状态? ────────────────────────────▶ [禁止新开仓]
    │                                             
    ├── G3: Dead事件? ──────────────────────────▶ [强制平仓]
    │                                             
    ├── G4: Fatigue > 85? ──────────────────────▶ [禁止新开仓]
    │                                             
    ├── G5: Correlation > 0.8? ──────────────────▶ [A1.5危机模式]
    │   (E4: 折减保底, 非E4: 归零)              
    │                                             
    ├── 计算Score = 0.25×A0 + 0.20×A-1 + 0.25×A1 
    │                      + 0.20×A1.5 - 0.10×A0.5
    │                                             
    ├── 拥挤度折价: High级 → Score -30%          
    │                                             
    ├── Narrative模式? ──────────────────────────▶ [降仓50%]
    │                                             
    └── 政策干预反转? (强干预 + A1≥60) ──────────▶ [方向翻转]
                                                        │
                                                        ▼
                                              最终仓位建议
                                              ┌───────────────┐
                                              │ >80: 重仓(80%)│
                                              │ 60-80: 标准仓 │
                                              │ 40-60: 试探   │
                                              │ <40: 禁止交易 │
                                              └───────────────┘
```

## 4. 闸门表 (Gates)

| 闸门 | 触发条件 | 执行动作 | 超时处理 |
|------|----------|----------|----------|
| **G1: 流动性** | Spread>5倍 / Red状态 | 禁止新开仓 | 退出全部风险资产 |
| **G2: 生命周期** | Dead/Archived状态 | 强制平仓/归档 | 1个交易日内清仓 |
| **G3: 疲劳度** | Fatigue_Final >85 | 禁止新开仓 | 降为Watch模式 |
| **G4: 相关性** | Corr >0.8 | 非E4归零/E4折减 | 启用对冲模式 |
| **G5: 评分** | Score区间 | 仓位分级 | 超时降仓50% |
| **G6: 政策** | 强干预+A1≥60 | 方向翻转 | 记录审计日志 |

## 5. 时间控制矩阵

| 阶段 | E4事件 | E3事件 | E2事件 | E1事件 |
|------|--------|--------|--------|--------|
| 事件发现 | <2min | <3min | <5min | <8min |
| 严重度判定 | <3min | <5min | <8min | <10min |
| 传导映射 | <5min | <8min | <15min | <20min |
| 市场验证 | <5min | <8min | <10min | <15min |
| Score计算 | <2min | <2min | <2min | <2min |
| 执行下单 | <3min | <5min | <8min | <10min |

**超时处理**: 单步超时3次 → 触发人工审核

## 6. 数据流规范

```
输入 (新闻/快讯)
    │
    ▼
Event Object (JSON)
{
  event_id: string,      // ME-[类别]-[日期]-[序号].V[版本]
  source_rank: "A"|"B"|"C",
  category: "A"|"B"|"C"|"D"|"E"|"F"|"G",
  severity: "E0"|"E1"|"E2"|"E3"|"E4",
  headline: string,
  source_url: string,
  detected_at: timestamp
}
    │
    ▼
Strategy Signal (JSON)
{
  event_id: string,
  lifecycle_state: "Detected"|"Verified"|"Active"|"Continuation"|"Exhaustion"|"Dead",
  catalyst_state: "first_impulse"|"continuation"|"exhaustion"|"dead",
  fatigue_index: number,
  scores: { A0, A-1, A1, A1.5, A0.5 },
  score: number,
  direction: "long"|"short"|"neutral",
  position_tier: "G1"|"G2"|"G3"|"G4"|"G5",
  conduction: { macro: [], sector: [], stock: [] }
}
    │
    ▼
Execution Order (JSON)
{
  action: "OPEN_LONG"|"OPEN_SHORT"|"CLOSE"|"HOLD",
  symbol: string,
  quantity: number,
  entry_price: number,
  stop_loss: number,
  take_profit_levels: number[],
  execution_mode: "FAST"|"STANDARD"|"CAREFUL",
  expiration: timestamp
}
```

## 7. 模块复用设计

### 可复用组件

| 组件 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `EventObjectifier` | 新闻→事件对象 | raw_text | Event Object |
| `SourceRanker` | 来源分级 | source_url | A/B/C |
| `SeverityEstimator` | 严重度判定 | event_data | E0-E4 |
| `FatigueCalculator` | 疲劳度计算 | event_history | 0-100 |
| `ConductionMapper` | 传导映射 | event_type | macro/sector/stock |
| `MarketValidator` | 市场验证 | asset_prices | A1 score |
| `SignalScorer` | Score计算 | {A0,A-1,A1,A1.5,A0.5} | final_score |
| `RiskGatekeeper` | 闸门检查 | signal + market | pass/block |

### 配置化参数

```yaml
# edt_config.yaml
weights:
  A0: 0.25
  A-1: 0.20
  A1: 0.25
  A1.5: 0.20
  A0.5: 0.10

thresholds:
  fatigue_block: 85
  score_heavy: 80
  score_standard: 60
  score_light: 40

timeouts:
  severity_judgment: 300  # seconds
  conduction_mapping: 600
  market_validation: 300

e4_adjustments:
  A-1: -0.10
  A1: +0.10
  A0.5: +0.10
```

## 8. 实施路线图

### Phase 1: 核心逻辑 (Week 1-2)
- [ ] 实现 EventObjectifier 模块
- [ ] 实现 SeverityEstimator + SourceRanker
- [ ] 实现 FatigueCalculator
- [ ] 集成决策优先级树

### Phase 2: 分析层 (Week 3-4)
- [ ] 实现 ConductionMapper
- [ ] 实现 MarketValidator
- [ ] 实现 SignalScorer
- [ ] 完成 Score 公式 + E4权重调整

### Phase 3: 执行层 (Week 5-6)
- [ ] 实现 RiskGatekeeper (G1-G6)
- [ ] 实现流动性检测 (Green/Yellow/Red)
- [ ] 实现分批建仓/减仓逻辑
- [ ] 实现退出策略 (止损/止盈)

### Phase 4: 优化 (Week 7-8)
- [ ] 时间控制矩阵 + 超时处理
- [ ] 多事件并发处理
- [ ] 回测 + 参数优化
- [ ] 人工确认节点配置

---

**一句话口径**: 
> 将新闻通过生命周期过滤和传导映射，最终转化为可执行的交易信号。
