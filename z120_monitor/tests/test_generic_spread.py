#!/usr/bin/env python3
"""
通用价差查询模块测试
验证核心功能
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.generic_spread import SpreadEngine, SignalGenerator


def test_spread_engine():
    """测试价差计算引擎"""
    print("=" * 60)
    print("测试 1: 价差计算引擎")
    print("=" * 60)

    asset1 = {"symbol": "MNQ", "multiplier": 2.0, "ratio": 1}
    asset2 = {"symbol": "MYM", "multiplier": 0.5, "ratio": 2}

    engine = SpreadEngine(asset1, asset2)

    price1 = 25246.0
    price2 = 12500.0

    spread_value = engine.calculate_spread_value(price1, price2)
    spread_ratio = engine.calculate_spread_ratio(price1, price2)

    print(f"资产1: {asset1['symbol']} = {price1}")
    print(f"资产2: {asset2['symbol']} = {price2}")
    print(f"价值价差: {spread_value:,.2f}")
    print(f"价差比率: {spread_ratio:.4f}")

    expected_value = price1 * 2.0 * 1 - price2 * 0.5 * 2
    expected_ratio = (price1 * 2.0 * 1) / (price2 * 0.5 * 2)

    assert abs(spread_value - expected_value) < 0.01, (
        f"价值价差计算错误: {spread_value} != {expected_value}"
    )
    assert abs(spread_ratio - expected_ratio) < 0.0001, (
        f"价差比率计算错误: {spread_ratio} != {expected_ratio}"
    )

    print("✓ 价差计算引擎测试通过\n")


def test_signal_generator():
    """测试信号生成器"""
    print("=" * 60)
    print("测试 2: 信号生成器")
    print("=" * 60)

    generator = SignalGenerator(threshold=1000)

    signal1 = generator.generate_signal("value", 500.0, 0.04)
    print(f"价差 500 (阈值1000): {signal1['signal_type']} - {signal1['action']}")
    assert signal1["signal_type"] == "NO_SIGNAL"

    signal2 = generator.generate_signal("value", 1500.0, 0.12)
    print(f"价差 1500 (阈值1000): {signal2['signal_type']} - {signal2['action']}")
    assert signal2["signal_type"] == "LONG"

    signal3 = generator.generate_signal("value", -1500.0, -0.12)
    print(f"价差 -1500 (阈值1000): {signal3['signal_type']} - {signal3['action']}")
    assert signal3["signal_type"] == "SHORT"

    print("✓ 信号生成器测试通过\n")


def test_config_loading():
    """测试配置加载"""
    print("=" * 60)
    print("测试 3: 配置加载")
    print("=" * 60)

    from core.generic_spread import GenericSpreadMonitor

    monitor = GenericSpreadMonitor()
    pairs = monitor.list_pairs()

    print(f"启用的交易对: {pairs}")
    assert len(pairs) > 0, "没有启用的交易对"

    config = monitor.get_pair_config("MNQ_MYM")
    assert config is not None, "MNQ_MYM 配置不存在"
    print(f"MNQ_MYM 配置: {config}")

    print("✓ 配置加载测试通过\n")


def test_text_report():
    """测试文本报告渲染"""
    print("=" * 60)
    print("测试 4: 文本报告渲染")
    print("=" * 60)

    from core.generic_spread import GenericSpreadMonitor

    monitor = GenericSpreadMonitor()

    result = {
        "pair": "MNQ_MYM",
        "mode": "value",
        "timestamp": "2026-02-09T12:00:00",
        "prices": {"MNQ": 25246.0, "MYM": 12500.0},
        "spread": {"value": 37992.0, "ratio": 4.039},
        "threshold": 1000,
        "signal": {
            "signal_type": "NO_SIGNAL",
            "action": "HOLD",
            "reason": "价差未达到阈值",
        },
        "calculation": {
            "formula": "spread_value(price1, price2)",
            "details": "MNQ × 2.0 × 1 - MYM × 0.5 × 2",
        },
    }

    report = monitor.render_text_report(result)
    print(report)

    assert "MNQ_MYM" in report
    assert "价值价差" in report or "value" in report
    assert "NO_SIGNAL" in report

    print("\n✓ 文本报告渲染测试通过\n")


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("通用价差查询模块测试")
    print("=" * 60 + "\n")

    test_spread_engine()
    test_signal_generator()
    test_config_loading()
    test_text_report()

    print("=" * 60)
    print("所有测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    main()
