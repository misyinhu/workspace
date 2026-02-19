"""
Z120 价差计算模块
基于 M5 图表，计算 120 个周期的 Z-Score
支持从配置文件读取阈值参数
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from datetime import datetime


class Z120Calculator:
    """Z120 价差计算器"""

    def __init__(self, window: int = 120):
        self.window = window
        self.spread_history: pd.Series = pd.Series(dtype=float)

    def update(self, spread_value: float) -> Dict[str, Any]:
        """更新价差数据并计算 Z120"""
        self.spread_history = pd.concat(
            [self.spread_history, pd.Series([spread_value])], ignore_index=True
        )

        if len(self.spread_history) < self.window:
            return {
                "zscore": None,
                "spread": spread_value,
                "mean": None,
                "std": None,
                "status": "WARMUP",
                "message": f"数据收集中 ({len(self.spread_history)}/{self.window})",
            }

        recent_spreads = self.spread_history.iloc[-self.window :]
        mean = recent_spreads.mean()
        std = recent_spreads.std()

        if std == 0 or np.isnan(std):
            return {
                "zscore": None,
                "spread": spread_value,
                "mean": mean,
                "std": std,
                "status": "INVALID",
                "message": "标准差为0或无效",
            }

        zscore = (spread_value - mean) / std

        return {
            "zscore": float(zscore),
            "spread": spread_value,
            "mean": float(mean),
            "std": float(std),
            "status": "ACTIVE",
            "message": "Z120 计算完成",
        }

    def calculate_zscore(self, spread_value: float) -> Optional[float]:
        """计算 Z120 值"""
        result = self.update(spread_value)
        zscore = result.get("zscore")
        if zscore is not None:
            return float(zscore)
        return None

    def get_signal(
        self, zscore: Optional[float], oversold: float = -6.0, overbought: float = 6.0
    ) -> Dict[str, Any]:
        """生成交易信号"""
        if zscore is None:
            return {"signal": "WAIT", "action": "HOLD", "reason": "Z120 数据不足"}

        if zscore <= oversold:
            return {
                "signal": "OVERSOLD",
                "action": "LONG_SPREAD",
                "reason": f"Z120={zscore:.2f} <= {oversold}，做多价差",
                "zscore": zscore,
            }
        elif zscore >= overbought:
            return {
                "signal": "OVERBOUGHT",
                "action": "SHORT_SPREAD",
                "reason": f"Z120={zscore:.2f} >= {overbought}，做空价差",
                "zscore": zscore,
            }
        else:
            return {
                "signal": "NEUTRAL",
                "action": "HOLD",
                "reason": f"Z120={zscore:.2f} 在阈值范围内",
                "zscore": zscore,
            }

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        if len(self.spread_history) < 2:
            return {
                "count": len(self.spread_history),
                "mean": None,
                "std": None,
                "min": None,
                "max": None,
            }

        mean_val = (
            float(self.spread_history.mean()) if len(self.spread_history) > 0 else None
        )
        std_val = (
            float(np.std(self.spread_history)) if len(self.spread_history) > 0 else None
        )
        min_val = (
            float(self.spread_history.min()) if len(self.spread_history) > 0 else None
        )
        max_val = (
            float(self.spread_history.max()) if len(self.spread_history) > 0 else None
        )
        return {
            "count": len(self.spread_history),
            "mean": mean_val,
            "std": std_val,
            "min": min_val,
            "max": max_val,
        }

    def reset(self):
        """重置历史数据"""
        self.spread_history = pd.Series(dtype=float)


class MultiPairZ120Monitor:
    """多品种 Z120 监控器"""

    def __init__(
        self, window: int = 120, oversold: float = -6.0, overbought: float = 6.0
    ):
        self.window = window
        self.oversold = oversold
        self.overbought = overbought
        self.calculators: Dict[str, Z120Calculator] = {}

    def add_pair(self, pair_name: str):
        """添加交易对"""
        if pair_name not in self.calculators:
            self.calculators[pair_name] = Z120Calculator(self.window)

    def update_pair(self, pair_name: str, spread_value: float) -> Dict[str, Any]:
        """更新交易对价差"""
        if pair_name not in self.calculators:
            self.add_pair(pair_name)

        calc = self.calculators[pair_name]
        result = calc.update(spread_value)
        zscore_val = result.get("zscore")
        signal = calc.get_signal(
            zscore_val if zscore_val is not None else None,
            self.oversold,
            self.overbought,
        )

        return {"pair": pair_name, **result, **signal}

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有交易对状态"""
        status = {}
        for name, calc in self.calculators.items():
            if len(calc.spread_history) >= calc.window:
                result = calc.update(float(calc.spread_history.iloc[-1]))
                status[name] = {
                    "zscore": result.get("zscore"),
                    "statistics": calc.get_statistics(),
                }
            else:
                status[name] = {
                    "zscore": None,
                    "statistics": calc.get_statistics(),
                }
        return status

    def get_signals(self) -> Dict[str, Dict[str, Any]]:
        """获取所有信号"""
        signals = {}
        for name, calc in self.calculators.items():
            if len(calc.spread_history) >= self.window:
                last_value = float(calc.spread_history.iloc[-1])
                zscore = calc.calculate_zscore(last_value)
                signals[name] = calc.get_signal(zscore, self.oversold, self.overbought)
        return signals
