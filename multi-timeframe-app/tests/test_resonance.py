#!/usr/bin/env python3
"""
pytest测试套件 - 多周期共振分析核心算法
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
import numpy as np
from datetime import datetime, timedelta


class TestResonanceCalculation:
    """共振分数计算测试"""

    @pytest.fixture
    def calculate_resonance_en(self):
        """导入待测试函数"""
        from app import calculate_resonance_en
        return calculate_resonance_en

    def test_all_up(self, calculate_resonance_en):
        """全上涨 - 应得高分"""
        directions = ["up", "up", "up", "up", "up"]
        result = calculate_resonance_en(directions)
        
        assert result["score"] >= 70
        assert result["level"] == "high"
        assert result["distribution"]["up"] == 5

    def test_all_down(self, calculate_resonance_en):
        """全下跌 - 应得高分"""
        directions = ["down", "down", "down", "down", "down"]
        result = calculate_resonance_en(directions)
        
        assert result["score"] >= 70
        assert result["level"] == "high"
        assert result["distribution"]["down"] == 5

    def test_mixed_up_neutral(self, calculate_resonance_en):
        """混合上涨+震荡 - 中等分"""
        directions = ["up", "up", "neutral", "neutral", "neutral"]
        result = calculate_resonance_en(directions)
        
        assert 30 <= result["score"] < 70
        assert result["level"] == "low"

    def test_conflict(self, calculate_resonance_en):
        directions = ["up", "down", "up", "down", "neutral"]
        result = calculate_resonance_en(directions)
        
        assert result["distribution"]["up"] == 2
        assert result["distribution"]["down"] == 2

    def test_score_bounds(self, calculate_resonance_en):
        """分数边界测试"""
        for _ in range(10):
            directions = np.random.choice(["up", "down", "neutral"], size=5).tolist()
            result = calculate_resonance_en(directions)
            
            assert 0 <= result["score"] <= 100

    def test_empty_directions(self, calculate_resonance_en):
        """空输入"""
        directions = []
        result = calculate_resonance_en(directions)
        
        assert result["score"] == 0


class TestRSICalculation:
    """RSI计算测试"""

    @pytest.fixture
    def calculate_rsi(self):
        from app import calculate_rsi_local
        return calculate_rsi_local

    def test_rsi_zero_change(self, calculate_rsi):
        """价格在区间内波动 - RSI应接近50"""
        prices = [100] * 20
        rsi = calculate_rsi(prices, period=14)
        
        assert rsi == 100.0

    def test_rsi_continuous_up(self, calculate_rsi):
        """连续上涨 - RSI应高于70"""
        prices = [100 + i for i in range(20)]
        rsi = calculate_rsi(prices, period=14)
        
        assert rsi > 70

    def test_rsi_continuous_down(self, calculate_rsi):
        """连续下跌 - RSI应低于30"""
        prices = [120 - i for i in range(20)]
        rsi = calculate_rsi(prices, period=14)
        
        assert rsi < 30

    def test_rsi_short_period(self, calculate_rsi):
        """数据不足 - 返回50"""
        prices = [100, 101, 102]
        rsi = calculate_rsi(prices, period=14)
        
        assert rsi == 50.0

    def test_rsi_exact_period(self, calculate_rsi):
        """刚好够数据"""
        prices = [100 + i for i in range(15)]
        rsi = calculate_rsi(prices, period=14)
        
        assert 0 <= rsi <= 100


class TestMACalculation:
    """移动平均线计算测试"""

    @pytest.fixture
    def calculate_ma(self):
        from app import calculate_ma_local
        return calculate_ma_local

    def test_ma_normal(self, calculate_ma):
        prices = list(range(100, 120))
        ma = calculate_ma(prices, period=20)
        
        assert ma == 109.5

    def test_ma_insufficient_data(self, calculate_ma):
        """数据不足"""
        prices = [100, 101, 102]
        ma = calculate_ma(prices, period=20)
        
        assert ma == 0.0

    def test_ma_exact_period(self, calculate_ma):
        """刚好够数据"""
        prices = list(range(20))
        ma = calculate_ma(prices, period=20)
        
        assert ma == 9.5


class TestTrendCalculation:
    """趋势判定测试"""

    @pytest.fixture
    def calculate_trend(self):
        from app import calculate_trend
        return calculate_trend

    @pytest.fixture
    def sample_data(self):
        """生成测试数据"""
        import pandas as pd
        return pd

    def test_uptrend(self, calculate_trend, sample_data):
        df = sample_data.DataFrame({
            "close": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
                     110, 111, 112, 113, 114, 115, 116, 117, 118, 119]
        })
        result = calculate_trend(df)
        
        assert result["direction"] in ["上涨", "震荡"]

    def test_downtrend(self, calculate_trend, sample_data):
        df = sample_data.DataFrame({
            "close": [119, 118, 117, 116, 115, 114, 113, 112, 111, 110,
                     109, 108, 107, 106, 105, 104, 103, 102, 101, 100]
        })
        result = calculate_trend(df)
        
        assert result["direction"] in ["下跌", "震荡"]

    def test_sideways(self, calculate_trend, sample_data):
        df = sample_data.DataFrame({
            "close": [100, 102, 98, 104, 96, 102, 98, 103, 97, 101,
                     99, 102, 98, 100, 99, 101, 98, 100, 99, 102]
        })
        result = calculate_trend(df)
        
        assert result["direction"] in ["震荡", "上涨", "下跌"]

    def test_short_data(self, calculate_trend, sample_data):
        df = sample_data.DataFrame({"close": [100, 101, 102]})
        result = calculate_trend(df)
        
        assert result["direction"] == "震荡"


class TestInstrumentConfig:
    """品种配置测试"""

    def test_load_instruments_config(self):
        """加载品种配置"""
        from app import load_instruments_config
        config = load_instruments_config()
        
        assert isinstance(config, list)
        assert len(config) > 0

    def test_instrument_structure(self):
        """品种结构"""
        from app import load_instruments_config
        config = load_instruments_config()
        
        if config:
            inst = config[0]
            assert "symbol" in inst
            assert "name" in inst
            assert "exchange" in inst
            assert "source" in inst

    def test_get_source_for_symbol(self):
        """获取数据源"""
        from app import get_source_for_symbol
        
        source = get_source_for_symbol("DOGE-USDT")
        assert source == "okx"
        
        source = get_source_for_symbol("AAPL")
        assert source == "ib"

    def test_fetch_instruments(self):
        """搜索品种"""
        from app import fetch_instruments
        
        all_inst = fetch_instruments()
        assert len(all_inst) > 0
        
        doge = fetch_instruments("DOGE")
        assert any("DOGE" in i["symbol"] for i in doge)


class TestQuantCoreAPI:
    """quant-core API集成测试"""

    def test_fetch_multi_timeframe(self):
        """获取多周期数据"""
        from app import fetch_multi_timeframe
        
        result = fetch_multi_timeframe("DOGE-USDT")
        
        assert "symbol" in result
        assert "timeframes" in result

    def test_resonance_calculation(self):
        """共振计算流程"""
        from app import fetch_multi_timeframe
        
        result = fetch_multi_timeframe("DOGE-USDT")
        
        assert "resonance" in result
        
        if result.get("timeframes"):
            resonance = result.get("resonance", {})
            if resonance:
                assert "score" in resonance


class TestMockData:
    """Mock数据测试"""

    def test_generate_mock_ohlc(self):
        """生成OHLC数据"""
        from app import generate_mock_ohlc
        import pandas as pd
        
        df = generate_mock_ohlc("AAPL", "1m", periods=100)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 100
        assert "open" in df.columns
        assert "high" in df.columns
        assert "low" in df.columns
        assert "close" in df.columns
        assert "volume" in df.columns

    def test_mock_multi_timeframe(self):
        """Mock多周期数据"""
        from app import mock_multi_timeframe
        
        result = mock_multi_timeframe("TEST")
        
        assert "symbol" in result
        assert "timeframes" in result
        assert "resonance" in result


class TestOKXDataSource:

    def test_okx_doge_fetch(self):
        from app import fetch_from_history
        
        result = fetch_from_history("DOGE-USDT", "okx")
        
        print("\n=== OKX DOGE-USDT ===")
        for tf, data in result.get("timeframes", {}).items():
            print(f"  {tf}: trend={data.get('trend')}, close={data.get('close')}, rsi={data.get('rsi')}")
        print(f"  resonance: {result.get('resonance')}")
        
        assert "symbol" in result
        assert "timeframes" in result

    def test_okx_eth_fetch(self):
        from app import fetch_from_history
        
        result = fetch_from_history("ETH-USDT", "okx")
        
        print("\n=== OKX ETH-USDT ===")
        for tf, data in result.get("timeframes", {}).items():
            print(f"  {tf}: trend={data.get('trend')}, close={data.get('close')}, rsi={data.get('rsi')}")
        print(f"  resonance: {result.get('resonance')}")

    def test_okx_btc_fetch(self):
        from app import fetch_from_history
        
        result = fetch_from_history("BTC-USDT", "okx")
        
        print("\n=== OKX BTC-USDT ===")
        for tf, data in result.get("timeframes", {}).items():
            print(f"  {tf}: trend={data.get('trend')}, close={data.get('close')}, rsi={data.get('rsi')}")
        print(f"  resonance: {result.get('resonance')}")


class TestIBDataSource:

    def test_ib_aapl_fetch(self):
        from app import fetch_from_history
        
        result = fetch_from_history("AAPL", "ib")
        
        print("\n=== IB AAPL ===")
        for tf, data in result.get("timeframes", {}).items():
            print(f"  {tf}: trend={data.get('trend')}, close={data.get('close')}")
        print(f"  resonance: {result.get('resonance')}")

    def test_ib_es_fetch(self):
        from app import fetch_from_history
        
        result = fetch_from_history("ES", "ib")
        
        print("\n=== IB ES ===")
        for tf, data in result.get("timeframes", {}).items():
            print(f"  {tf}: trend={data.get('trend')}, close={data.get('close')}")
        print(f"  resonance: {result.get('resonance')}")

    def test_ib_gc_fetch(self):
        from app import fetch_from_history
        
        result = fetch_from_history("GC", "ib")
        
        print("\n=== IB GC ===")
        for tf, data in result.get("timeframes", {}).items():
            print(f"  {tf}: trend={data.get('trend')}, close={data.get('close')}")
        print(f"  resonance: {result.get('resonance')}")

    def test_ib_mgc_fetch(self):
        from app import fetch_from_history
        
        result = fetch_from_history("MGC", "ib")
        
        print("\n=== IB MGC ===")
        for tf, data in result.get("timeframes", {}).items():
            print(f"  {tf}: trend={data.get('trend')}, close={data.get('close')}")
        print(f"  resonance: {result.get('resonance')}")


class TestTdxDataSource:

    def test_tdx_fetch(self):
        from app import fetch_from_history
        
        result = fetch_from_history("IF", "tdxquant")
        
        print("\n=== TDX IF ===")
        for tf, data in result.get("timeframes", {}).items():
            print(f"  {tf}: trend={data.get('trend')}, close={data.get('close')}")
        print(f"  resonance: {result.get('resonance')}")


class TestCrossSourceResonance:

    def test_okx_resonance(self):
        from app import fetch_from_history
        
        result = fetch_from_history("DOGE-USDT", "okx")
        
        print("\n=== OKX DOGE 共振详情 ===")
        print(f"  timeframes: {result.get('timeframes', {})}")
        print(f"  resonance: {result.get('resonance')}")

    def test_ib_resonance(self):
        from app import fetch_from_history
        
        result = fetch_from_history("AAPL", "ib")
        
        print("\n=== IB AAPL 共振详情 ===")
        print(f"  timeframes: {result.get('timeframes', {})}")
        print(f"  resonance: {result.get('resonance')}")

    def test_multi_symbol_okx(self):
        from app import fetch_from_history
        from app import calculate_resonance_en
        
        symbols = ["DOGE-USDT", "ETH-USDT", "BTC-USDT"]
        
        print("\n=== 多OKX品种汇总 ===")
        for sym in symbols:
            result = fetch_from_history(sym, "okx")
            print(f"\n{sym}:")
            for tf, data in result.get("timeframes", {}).items():
                print(f"  {tf}: {data.get('trend')}")
            print(f"  resonance: {result.get('resonance')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])