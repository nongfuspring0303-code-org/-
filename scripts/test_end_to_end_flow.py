#!/usr/bin/env python3
"""
端到端流程测试脚本
实际运行每个模块，验证输入输出是否符合逻辑
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

# 添加项目根目录到路径
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from intel_modules import IntelPipeline
from ai_semantic_analyzer import SemanticAnalyzer
from lifecycle_manager import LifecycleManager
from fatigue_calculator import FatigueCalculator
from conduction_mapper import ConductionMapper
from market_validator import MarketValidator
from signal_scorer import SignalScorer
from state_store import EventStateStore


def print_section(title):
    """打印分隔线"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def print_json(data, title="输出"):
    """格式化打印 JSON"""
    print(f"\n{title}:")
    print(json.dumps(data, indent=2, ensure_ascii=False))


def test_e2e_flow():
    """端到端流程测试"""

    # 1. 准备测试输入 - 模拟真实事件
    print_section("步骤 1: 准备测试输入")

    input_payload = {
        "headline": "美联储宣布紧急降息 50 个基点，应对经济放缓",
        "source": "https://www.reuters.com/markets/us/fed-emergency-rate-cut",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_text": """
        美联储周三宣布紧急降息50个基点，将联邦基金利率目标区间下调至4.75%-5.00%。
        这是美联储自2020年以来的首次紧急降息，旨在应对经济增长放缓和通胀压力缓解。
        市场对此反应强烈，标普500指数期货上涨2.3%，纳斯达克100期货上涨3.1%。
        """,
        "category": "E",  # 货币政策事件
        "severity": "E3",  # 高严重性
        "is_official_confirmed": True,
        "market_validated": True,
        "has_material_update": True,
        "elapsed_hours": 1,
        "vix": 28,
        "vix_change_pct": -15,
        "spx_move_pct": 2.3,
        "sector_move_pct": 3.5,
        "policy_intervention": "STRONG",  # 强政策干预
    }

    print_json(input_payload, "输入事件")

    # 2. Intel 模块 - 事件标准化
    print_section("步骤 2: Intel 模块 - 事件标准化")

    intel = IntelPipeline()
    intel_output = intel.run(input_payload)

    print(f"捕获状态: {intel_output.get('capture', {}).get('captured', False)}")
    print_json(intel_output.get("event_object", {}), "标准化事件对象")
    print_json(intel_output.get("source_rank", {}), "来源评级")

    event_object = intel_output["event_object"]
    source_rank = intel_output["source_rank"]

    # 3. Semantic 模块 - 语义分析
    print_section("步骤 3: Semantic 模块 - 语义分析")

    semantic = SemanticAnalyzer()
    semantic_output = semantic.analyze(
        event_object.get("headline", ""),
        event_object.get("raw_text", "")
    )

    print_json(semantic_output, "语义分析结果")

    # 4. Lifecycle 模块 - 生命周期判断
    print_section("步骤 4: Lifecycle 模块 - 生命周期判断")

    lifecycle = LifecycleManager()
    lifecycle_output = lifecycle.run({
        "event_id": event_object["event_id"],
        "category": event_object["category"],
        "severity": event_object["severity"],
        "source_rank": event_object["source_rank"],
        "headline": event_object["headline"],
        "detected_at": event_object["detected_at"],
        "is_official_confirmed": input_payload["is_official_confirmed"],
        "market_validated": input_payload["market_validated"],
        "has_material_update": input_payload["has_material_update"],
        "elapsed_hours": input_payload["elapsed_hours"],
        "previous_lifecycle_state": None,
        "previous_internal_state": None,
        "retry_count": 0,
    })

    print(f"状态: {lifecycle_output.status.value}")
    print_json(lifecycle_output.data, "生命周期状态")

    # 5. Fatigue 模块 - 疲劳度计算
    print_section("步骤 5: Fatigue 模块 - 疲劳度计算")

    # 初始化状态存储（可选）
    state_store = EventStateStore()
    fatigue = FatigueCalculator(state_store=state_store)

    fatigue_output = fatigue.run({
        "event_id": event_object["event_id"],
        "category": event_object["category"],
        "lifecycle_state": lifecycle_output.data["lifecycle_state"],
        "narrative_tags": [semantic_output.get("event_type", "unknown")],
        "category_active_count": 2,  # 模拟当前有2个同类活跃事件
        "tag_active_counts": {semantic_output.get("event_type", "unknown"): 2},
        "days_since_last_dead": 10,
    })

    print(f"状态: {fatigue_output.status.value}")
    print_json(fatigue_output.data, "疲劳度计算结果")

    # 6. Conduction 模块 - 传导映射
    print_section("步骤 6: Conduction 模块 - 传导映射")

    conduction = ConductionMapper()
    conduction_output = conduction.run({
        "event_id": event_object["event_id"],
        "category": event_object["category"],
        "severity": event_object["severity"],
        "headline": event_object["headline"],
        "summary": event_object.get("raw_text", "")[:200],
        "lifecycle_state": lifecycle_output.data["lifecycle_state"],
        "narrative_tags": [semantic_output.get("event_type", "unknown")],
        "policy_intervention": "STRONG",  # 强政策干预
        "sector_data": [
            {"sector": "Technology", "industry": "Technology", "change_pct": 3.5},
            {"sector": "Financial Services", "industry": "Financial Services", "change_pct": 2.1},
            {"sector": "Real Estate", "industry": "Real Estate", "change_pct": 2.8},
        ],
    })

    print(f"状态: {conduction_output.status.value}")
    print_json(conduction_output.data.get("macro_factors", []), "宏观因子")
    print_json(conduction_output.data.get("sector_impacts", []), "板块影响")
    print_json(conduction_output.data.get("stock_candidates", [])[:3], "股票候选（前3）")
    print(f"传导路径: {conduction_output.data.get('conduction_path', [])}")
    print(f"置信度: {conduction_output.data.get('confidence', 0)}")

    # 7. Market Validator 模块 - 市场验证
    print_section("步骤 7: Market Validator 模块 - 市场验证")

    validator = MarketValidator()
    validator_output = validator.run({
        "event_id": event_object["event_id"],
        "conduction_output": {"conduction_path": conduction_output.data.get("conduction_path", [])},
        "price_changes": {"SPY": 2.3, "QQQ": 3.1},
        "volume_changes": {"SPY": 1.5, "QQQ": 1.8},
        "cross_asset_linkage": {"confirmed": True, "details": "股债同涨"},
        "persistence_minutes": 120,
        "winner_loser_dispersion": {"confirmed": True, "dispersion_score": 0.75},
        "market_timestamp": event_object.get("updated_at", datetime.now(timezone.utc).isoformat()),
    })

    print(f"状态: {validator_output.status.value}")
    print_json(validator_output.data, "市场验证结果")

    # 8. Signal Scorer 模块 - 信号评分
    print_section("步骤 8: Signal Scorer 模块 - 信号评分")

    scorer = SignalScorer()
    scorer_output = scorer.run({
        "event_id": event_object["event_id"],
        "severity": event_object["severity"],
        "A0": intel_output["severity"]["A0"],
        "A-1": 65,
        "A1": validator_output.data["A1"],
        "A1.5": 60,
        "A0.5": 0,
        "fatigue_final": fatigue_output.data["fatigue_final"],
        "a_minus_1_discount_factor": fatigue_output.data["a_minus_1_discount_factor"],
        "correlation": 0.65,
        "is_crowded": False,
        "narrative_mode": "Fact-Driven",
        "policy_intervention": "STRONG",
        "base_direction": "long",
        "watch_mode": fatigue_output.data["watch_mode"],
        "weights_version": "score_v1",
    })

    print(f"状态: {scorer_output.status.value}")
    print_json(scorer_output.data, "信号评分结果")

    # 9. 汇总分析
    print_section("步骤 9: 汇总分析")

    summary = {
        "事件": event_object["event_id"],
        "生命周期": lifecycle_output.data["lifecycle_state"],
        "疲劳度": fatigue_output.data["fatigue_final"],
        "看守模式": fatigue_output.data["watch_mode"],
        "传导路径": conduction_output.data.get("conduction_path", []),
        "市场验证": validator_output.data["A1"],
        "最终信号": scorer_output.data["score"],
        "交易方向": scorer_output.data.get("direction", "unknown"),
        "信号等级": scorer_output.data.get("score_tier", "unknown"),
    }

    print_json(summary, "流程汇总")

    # 10. 逻辑检查
    print_section("步骤 10: 逻辑检查")

    checks = []

    # 检查 1: 生命周期状态
    if lifecycle_output.data["lifecycle_state"] in ["Detected", "Verified", "Active"]:
        checks.append({"检查": "生命周期状态", "状态": "✅ 通过", "值": lifecycle_output.data["lifecycle_state"]})
    else:
        checks.append({"检查": "生命周期状态", "状态": "❌ 异常", "值": lifecycle_output.data["lifecycle_state"]})

    # 检查 2: 疲劳度范围
    fatigue_score = fatigue_output.data["fatigue_final"]
    if 0 <= fatigue_score <= 100:
        checks.append({"检查": "疲劳度范围", "状态": "✅ 通过", "值": fatigue_score})
    else:
        checks.append({"检查": "疲劳度范围", "状态": "❌ 异常", "值": fatigue_score})

    # 检查 3: 市场验证 A1 范围
    a1_score = validator_output.data["A1"]
    if 0 <= a1_score <= 100:
        checks.append({"检查": "市场验证 A1", "状态": "✅ 通过", "值": a1_score})
    else:
        checks.append({"检查": "市场验证 A1", "状态": "❌ 异常", "值": a1_score})

    # 检查 4: 信号评分范围
    signal_score = scorer_output.data["score"]
    if 0 <= signal_score <= 100:
        checks.append({"检查": "信号评分范围", "状态": "✅ 通过", "值": signal_score})
    else:
        checks.append({"检查": "信号评分范围", "状态": "❌ 异常", "值": signal_score})

    # 检查 5: 传导路径不为空
    conduction_path = conduction_output.data.get("conduction_path", [])
    if conduction_path:
        checks.append({"检查": "传导路径", "状态": "✅ 通过", "值": f"{len(conduction_path)} 步"})
    else:
        checks.append({"检查": "传导路径", "状态": "❌ 异常", "值": "空"})

    # 检查 6: 官方确认事件应快速激活
    if input_payload["is_official_confirmed"]:
        if lifecycle_output.data["lifecycle_state"] in ["Verified", "Active"]:
            checks.append({"检查": "官方确认激活", "状态": "✅ 通过", "值": lifecycle_output.data["lifecycle_state"]})
        else:
            checks.append({"检查": "官方确认激活", "状态": "⚠️ 偏慢", "值": lifecycle_output.data["lifecycle_state"]})

    # 检查 7: 强政策干预应提升流动性因子
    if input_payload["policy_intervention"] == "STRONG":
        macro_factors = conduction_output.data.get("macro_factors", [])
        liquidity_factor = next((f for f in macro_factors if f.get("factor") == "liquidity"), None)
        if liquidity_factor and liquidity_factor.get("direction") == "up":
            checks.append({"检查": "政策干预流动性", "状态": "✅ 通过", "值": liquidity_factor})
        else:
            checks.append({"检查": "政策干预流动性", "状态": "⚠️ 未生效", "值": liquidity_factor})

    print_json(checks, "逻辑检查结果")

    # 统计
    passed = sum(1 for c in checks if "✅" in c["状态"])
    total = len(checks)
    print(f"\n检查通过率: {passed}/{total} ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 所有逻辑检查通过！")
    else:
        print(f"\n⚠️ 发现 {total - passed} 个潜在问题")

    return summary


if __name__ == "__main__":
    try:
        result = test_e2e_flow()
        print(f"\n✅ 端到端测试完成")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
