"""三滤网交易信号计算 - 封装 quant_core.factors"""

from typing import Dict, Optional
from dataclasses import dataclass

# 添加 quant 路径以导入 quant_core
import sys
import os
_quant_path = "/Users/wang/.opencode/workspace/quant"
if _quant_path not in sys.path:
    sys.path.insert(0, _quant_path)

try:
    from quant_core.factors import (
        MultiPeriodSignalGenerator,
        TrendDirection,
        EntrySignal,
    )
    from quant_core.models import Bar as QuantBar
    _QUANT_AVAILABLE = True
except ImportError:
    _QUANT_AVAILABLE = False


@dataclass
class ThreeFilterSignal:
    """三滤网信号封装"""
    m30_trend: str           # 多头/空头/中性
    m5_pullback: str         # 回调中/无回调
    m1_entry: str             # 做多/做空/等待
    strength: int            # 0-100
    entry_price: Optional[float]
    stop_loss: Optional[float]
    risk_reward_ratio: Optional[float]
    signal_reason: str


def calculate_three_filter(timeframe_data: Dict, symbol: str) -> Optional[ThreeFilterSignal]:
    """
    根据多周期数据计算三滤网信号
    
    Args:
        timeframe_data: fetch_multi_timeframe 返回的数据
        symbol: 品种代码
    
    Returns:
        ThreeFilterSignal 对象，或 None 如果数据不足
    """
    if not _QUANT_AVAILABLE:
        return None
    
    # 提取各周期 bars
    m30_bars = timeframe_data.get("30m", {}).get("bars", [])
    m5_bars = timeframe_data.get("5m", {}).get("bars", [])
    m1_bars = timeframe_data.get("1m", {}).get("bars", [])
    
    # 检查数据量 - 调整为实际获取的数据量 (fetch_from_history 返回最多 50 根)
    if len(m30_bars) < 30:
        return None
    if len(m5_bars) < 15:
        return None
    if len(m1_bars) < 10:
        return None
    
    # 转换为 Bar 对象
    def to_bars(raw_bars):
        return [
            QuantBar(
                timestamp=b.get("timestamp"),
                open=b.get("open", 0),
                high=b.get("high", 0),
                low=b.get("low", 0),
                close=b.get("close", 0),
                volume=b.get("volume", 0),
                symbol=symbol,
                source=""
            )
            for b in raw_bars
        ]
    
    m30 = to_bars(m30_bars)
    m5 = to_bars(m5_bars)
    m1 = to_bars(m1_bars)
    
    # 调用 quant_core 三滤网
    gen = MultiPeriodSignalGenerator()
    raw_signal = gen.generate(symbol, m30, m5, m1)
    
    # 映射趋势方向
    trend_map = {
        TrendDirection.BULL: "多头",
        TrendDirection.BEAR: "空头",
        TrendDirection.NEUTRAL: "中性"
    }
    
    # 映射入场信号
    entry_map = {
        EntrySignal.LONG: "做多",
        EntrySignal.SHORT: "做空",
        EntrySignal.EXIT_LONG: "平多",
        EntrySignal.EXIT_SHORT: "平空",
        EntrySignal.WAIT: "等待"
    }
    
    return ThreeFilterSignal(
        m30_trend=trend_map.get(raw_signal.m30_trend, "中性"),
        m5_pullback="回调中" if raw_signal.m5_pullback else "无回调",
        m1_entry=entry_map.get(raw_signal.m1_entry, "等待"),
        strength=raw_signal.strength,
        entry_price=raw_signal.entry_price,
        stop_loss=raw_signal.stop_loss,
        risk_reward_ratio=raw_signal.risk_reward_ratio,
        signal_reason=raw_signal.signal_reason or ""
    )
