import sys
import os

sys.path.insert(0, "multi-timeframe-app")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import _load_shared_config


def test_read_spread_pairs():
    config = _load_shared_config()

    # Check if spread_pairs exists
    assert "spread_pairs" in config, "spread_pairs not in config"

    spread_pairs = config.get("spread_pairs", [])
    assert isinstance(spread_pairs, list), "spread_pairs must be a list"

    # Verify all required fields
    required_fields = ["name", "symbol1", "symbol2"]
    for i, pair in enumerate(spread_pairs, 1):
        print(f"Checking pair {i}: {pair.get('name')}")
        for field in required_fields:
            assert field in pair, f"Spread pair missing field: {field}"
            assert pair[field], f"Spread pair {field} cannot be empty"

    # Verify known pairs are present
    known_pairs = ["MNQ-MYM", "GC-MGC", "ES-MES"]
    found_names = [p["name"] for p in spread_pairs]

    for pair_name in known_pairs:
        assert pair_name in found_names, f"Expected pair '{pair_name}' not found"

    print(f"✅ Spread pairs: {found_names}")
    print(f"✅ Count: {len(spread_pairs)} pairs")
    print("✅ All tests passed!")


# ============ 套利计算测试 ============

import pytest
from src.analysis import (
    calculate_spread,
    calculate_ratio,
    calculate_correlation,
    calculate_zscore,
    generate_arbitrage_signal,
)


class TestSpreadCalculations:
    def test_calculate_spread(self):
        bars1 = [{"close": 100}, {"close": 101}, {"close": 102}]
        bars2 = [{"close": 50}, {"close": 51}, {"close": 52}]
        result = calculate_spread(bars1, bars2)
        assert result == [50, 50, 50]

    def test_calculate_spread_empty(self):
        assert calculate_spread([], []) == []

    def test_calculate_ratio(self):
        bars1 = [{"close": 100}, {"close": 102}, {"close": 104}]
        bars2 = [{"close": 50}, {"close": 51}, {"close": 52}]
        result = calculate_ratio(bars1, bars2)
        assert abs(result[0] - 2.0) < 0.01


class TestZScore:
    def test_calculate_zscore(self):
        spread = [10, 11, 10, 11, 10, 11, 20]  # 最后一个是异常值
        result = calculate_zscore(spread)
        assert "zscore" in result
        assert result["zscore"] > 1  # 异常值应该 zscore > 1

    def test_zscore_normal(self):
        spread = [10, 10, 10, 10, 10, 10, 10, 10, 10, 10]
        result = calculate_zscore(spread)
        assert abs(result["zscore"]) < 0.1  # 常数值 zscore 接近 0


class TestArbitrageSignal:
    def test_signal_trigger_zscore_long(self):
        result = generate_arbitrage_signal(
            zscore=3.5, correlation=0.9, rsi1=60, rsi2=50
        )
        assert result["signal"] == "SELL_SPREAD"

    def test_signal_trigger_zscore_short(self):
        result = generate_arbitrage_signal(
            zscore=-3.5, correlation=0.9, rsi1=60, rsi2=50
        )
        assert result["signal"] == "BUY_SPREAD"

    def test_signal_watch_low_correlation(self):
        result = generate_arbitrage_signal(
            zscore=3.5, correlation=0.5, rsi1=60, rsi2=50
        )
        assert result["signal"] == "WATCH"

    def test_signal_watch_low_zscore(self):
        result = generate_arbitrage_signal(
            zscore=1.0, correlation=0.9, rsi1=60, rsi2=50
        )
        assert result["signal"] == "WATCH"
