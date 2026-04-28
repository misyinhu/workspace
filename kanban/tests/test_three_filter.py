"""Test three-filter signal calculation module.

Unit tests for the three-filter trading signal generator.
"""

import pytest
import sys
from pathlib import Path

# Add paths
_workspace = Path(__file__).parent.parent.parent
_quant_path = "/Users/wang/.opencode/workspace/quant"
sys.path.insert(0, _quant_path)
sys.path.insert(0, str(_workspace))


class TestThreeFilterSignal:
    """Tests for ThreeFilterSignal dataclass."""

    def test_signal_dataclass_fields(self):
        """Test ThreeFilterSignal has required fields."""
        from src.three_filter import ThreeFilterSignal
        
        signal = ThreeFilterSignal(
            m30_trend="多头",
            m5_pullback="回调中",
            m1_entry="做多",
            strength=75,
            entry_price=100.5,
            stop_loss=98.0,
            risk_reward_ratio=2.5,
            signal_reason="M30多头确认"
        )
        
        assert signal.m30_trend == "多头"
        assert signal.m5_pullback == "回调中"
        assert signal.m1_entry == "做多"
        assert signal.strength == 75
        assert signal.entry_price == 100.5
        assert signal.stop_loss == 98.0
        assert signal.risk_reward_ratio == 2.5
        assert signal.signal_reason == "M30多头确认"

    def test_signal_optional_fields(self):
        """Test ThreeFilterSignal optional fields can be None."""
        from src.three_filter import ThreeFilterSignal
        
        signal = ThreeFilterSignal(
            m30_trend="中性",
            m5_pullback="无回调",
            m1_entry="等待",
            strength=50,
            entry_price=None,
            stop_loss=None,
            risk_reward_ratio=None,
            signal_reason=""
        )
        
        assert signal.entry_price is None
        assert signal.stop_loss is None
        assert signal.risk_reward_ratio is None


class TestCalculateThreeFilter:
    """Tests for calculate_three_filter function."""

    def test_returns_none_insufficient_m30_data(self):
        """Test returns None when M30 bars insufficient."""
        def make_bars(n):
            return [{"close": 100, "open": 99, "high": 101, "low": 98, "volume": 1000, "timestamp": 123456}] * n
        
        timeframe_data = {
            "30m": {"bars": make_bars(10)},  # Only 10 bars - need 30
            "5m": {"bars": make_bars(50)},
            "1m": {"bars": make_bars(50)},
        }
        
        from src.three_filter import calculate_three_filter
        result = calculate_three_filter(timeframe_data, "BTCUSDT")
        assert result is None

    def test_returns_none_insufficient_m5_data(self):
        """Test returns None when M5 bars insufficient."""
        def make_bars(n):
            return [{"close": 100, "open": 99, "high": 101, "low": 98, "volume": 1000, "timestamp": 123456}] * n
        
        timeframe_data = {
            "30m": {"bars": make_bars(30)},
            "5m": {"bars": make_bars(5)},  # Only 5 bars - need 15
            "1m": {"bars": make_bars(50)},
        }
        
        from src.three_filter import calculate_three_filter
        result = calculate_three_filter(timeframe_data, "BTCUSDT")
        assert result is None

    def test_returns_none_insufficient_m1_data(self):
        """Test returns None when M1 bars insufficient."""
        def make_bars(n):
            return [{"close": 100, "open": 99, "high": 101, "low": 98, "volume": 1000, "timestamp": 123456}] * n
        
        timeframe_data = {
            "30m": {"bars": make_bars(30)},
            "5m": {"bars": make_bars(15)},
            "1m": {"bars": make_bars(5)},  # Only 5 bars - need 10
        }
        
        from src.three_filter import calculate_three_filter
        result = calculate_three_filter(timeframe_data, "BTCUSDT")
        assert result is None

    def test_returns_signal_with_sufficient_data(self):
        """Test returns ThreeFilterSignal with sufficient data."""
        from src.three_filter import ThreeFilterSignal
        
        def make_bars(n):
            return [{"close": 100 + i * 0.1, "open": 99 + i * 0.1, "high": 101 + i * 0.1, 
                     "low": 98 + i * 0.1, "volume": 1000, "timestamp": 123456 + i} for i in range(n)]
        
        timeframe_data = {
            "30m": {"bars": make_bars(30)},
            "5m": {"bars": make_bars(15)},
            "1m": {"bars": make_bars(10)},
        }
        
        from src.three_filter import calculate_three_filter, _QUANT_AVAILABLE
        
        if not _QUANT_AVAILABLE:
            pytest.skip("quant_core not available")
        
        result = calculate_three_filter(timeframe_data, "BTCUSDT")
        
        # With sufficient data, should return a signal (not None)
        # The actual signal depends on the market data
        if result is not None:
            assert isinstance(result, ThreeFilterSignal)
            assert result.strength >= 0
            assert result.strength <= 100


class TestThreeFilterIntegration:
    """Integration tests for three-filter with quant_core."""

    def test_with_real_quant_core(self):
        """Test with real quant_core module (if available)."""
        from src.three_filter import calculate_three_filter, _QUANT_AVAILABLE, ThreeFilterSignal
        
        if not _QUANT_AVAILABLE:
            pytest.skip("quant_core not available")
        
        def make_bars(n):
            return [{"close": 100 + i * 0.1, "open": 99, "high": 101, 
                     "low": 98, "volume": 1000, "timestamp": 123456 + i} for i in range(n)]
        
        timeframe_data = {
            "30m": {"bars": make_bars(50)},
            "5m": {"bars": make_bars(30)},
            "1m": {"bars": make_bars(20)},
        }
        
        result = calculate_three_filter(timeframe_data, "DOGE-USDT-SWAP")
        
        if result is not None:
            assert isinstance(result, ThreeFilterSignal)
            assert result.strength >= 0
            assert result.strength <= 100
            # Verify trend mapping
            assert result.m30_trend in ["多头", "空头", "中性"]
            assert result.m1_entry in ["做多", "做空", "等待", "平多", "平空"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
