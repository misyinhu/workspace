"""
核心价差计算引擎
复用 MNQ-MYM 验证成功的策略逻辑到通用框架
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional


class SpreadEngine:
    """通用价差计算引擎"""

    def __init__(self, asset1_config: Dict[str, Any], asset2_config: Dict[str, Any]):
        self.asset1 = asset1_config
        self.asset2 = asset2_config

    def calculate_spread_value(self, price1: float, price2: float) -> float:
        """
        计算价差价值
        公式: asset1_value - ratio2 * asset2_value

        Args:
            price1: 第一个资产价格
            price2: 第二个资产价格

        Returns:
            价差价值
        """
        value1 = price1 * self.asset1["multiplier"] * self.asset1.get("ratio1", 1)
        value2 = price2 * self.asset2["multiplier"] * self.asset2.get("ratio2", 1)

        return value1 - value2

    def calculate_spread_ratio(self, price1: float, price2: float) -> float:
        """
        计算价差比率

        Args:
            price1: 第一个资产价格
            price2: 第二个资产价格

        Returns:
            价差比率
        """
        value1 = price1 * self.asset1["multiplier"] * self.asset1.get("ratio1", 1)
        value2 = price2 * self.asset2["multiplier"] * self.asset2.get("ratio2", 1)

        if value2 == 0:
            return 0.0

        return value1 / value2


class HistoricalDeviationDetector:
    """历史偏离检测器 - 复用 MNQ-MYM 验证成功的算法"""

    def __init__(self, threshold: float = 1000, lookback_days: int = 7):
        self.threshold = threshold
        self.lookback_days = lookback_days

    def detect_opportunity(self, spread_ratios: pd.Series) -> Dict[str, Any]:
        """
        检测价差机会
        直接复用 MNQ-MYM 验证成功的逻辑：
        - 7日内历史统计
        - 当前价差与历史极值的绝对差值
        - $1000 阈值触发

        Args:
            spread_ratios: 价差比率时间序列

        Returns:
            信号检测结果
        """
        if len(spread_ratios) < self.lookback_days:
            return {
                "signal_type": "NO_SIGNAL",
                "reason": f"数据不足，需要至少{self.lookback_days}天历史数据",
            }

        current_spread = float(spread_ratios.iloc[-1])

        # 7日内历史统计
        hist_max_series = spread_ratios.rolling(self.lookback_days).max()
        hist_min_series = spread_ratios.rolling(self.lookback_days).min()

        # 与历史极值的偏离度计算
        max_deviation = (
            abs(current_spread - float(hist_min_series.iloc[-1]))
            if not hist_min_series.empty
            else 0.0
        )  # 做多信号
        min_deviation = (
            abs(current_spread - float(hist_max_series.iloc[-1]))
            if not hist_max_series.empty
            else 0.0
        )  # 做空信号

        # 信号判断
        if max_deviation > self.threshold:
            return {
                "signal_type": "MAX_SIGNAL",
                "current_spread": current_spread,
                "max_deviation": max_deviation,
                "min_deviation": 0.0,
                "threshold_exceeded": True,
                "reason": f"价差偏离最小值 {max_deviation:.1f}，超过阈值{self.threshold}",
                "action": "LONG_ASSET1_SHORT_ASSET2",
            }
        elif min_deviation > self.threshold:
            return {
                "signal_type": "MIN_SIGNAL",
                "current_spread": current_spread,
                "max_deviation": 0.0,
                "min_deviation": min_deviation,
                "threshold_exceeded": True,
                "reason": f"价差偏离最大值 {min_deviation:.1f}，超过阈值{self.threshold}",
                "action": "SHORT_ASSET1_LONG_ASSET2",
            }
        else:
            return {
                "signal_type": "NO_SIGNAL",
                "current_spread": current_spread,
                "max_deviation": max_deviation,
                "min_deviation": min_deviation,
                "threshold_exceeded": False,
                "reason": f"价差正常 {current_spread:.3f}，无交易信号",
                "action": "HOLD",
            }

    def get_historical_stats(self, spread_ratios: pd.Series) -> Dict[str, float]:
        """
        获取历史统计信息

        Args:
            spread_ratios: 价差比率时间序列

        Returns:
            历史统计信息
        """
        if len(spread_ratios) < self.lookback_days:
            return {
                "current": 0.0,
                "max_7d": 0.0,
                "min_7d": 0.0,
                "mean_7d": 0.0,
                "std_7d": 0.0,
            }

        current = float(spread_ratios.iloc[-1])
        max_7d_series = spread_ratios.rolling(self.lookback_days).max()
        min_7d_series = spread_ratios.rolling(self.lookback_days).min()
        max_7d = float(max_7d_series.iloc[-1]) if not max_7d_series.empty else 0.0
        min_7d = float(min_7d_series.iloc[-1]) if not min_7d_series.empty else 0.0
        mean_series = spread_ratios.rolling(self.lookback_days).mean()
        std_series = spread_ratios.rolling(self.lookback_days).std()
        mean_7d = float(mean_series.iloc[-1]) if not mean_series.empty else 0.0
        std_7d = float(std_series.iloc[-1]) if not std_series.empty else 0.0

        return {
            "current": current,
            "max_7d": max_7d,
            "min_7d": min_7d,
            "mean_7d": mean_7d,
            "std_7d": std_7d,
        }


class UniversalSpreadStrategy:
    """通用价差策略类"""

    def __init__(
        self,
        asset1_config: Dict[str, Any],
        asset2_config: Dict[str, Any],
        strategy_params: Dict[str, Any],
    ):
        self.asset1_config = asset1_config
        self.asset2_config = asset2_config
        self.spread_engine = SpreadEngine(asset1_config, asset2_config)

        # 策略参数
        self.threshold = strategy_params.get("threshold", 1000)
        self.lookback_days = strategy_params.get("lookback_days", 7)

        # 历史偏离检测器
        self.deviation_detector = HistoricalDeviationDetector(
            threshold=self.threshold, lookback_days=self.lookback_days
        )

        # 策略状态
        self.current_position = None
        self.spread_history = pd.DataFrame()

    def analyze_spread_opportunity(
        self, price1: float, price2: float
    ) -> Dict[str, Any]:
        """
        分析价差机会

        Args:
            price1: 第一个资产价格
            price2: 第二个资产价格

        Returns:
            分析结果
        """
        # 计算价差比率
        spread_ratio = self.spread_engine.calculate_spread_ratio(price1, price2)

        # 添加到历史记录
        new_record = pd.DataFrame(
            {"spread_ratio": [spread_ratio], "timestamp": [pd.Timestamp.now()]}
        )
        self.spread_history = pd.concat(
            [self.spread_history, new_record], ignore_index=True
        )

        # 检测交易机会
        signal = self.deviation_detector.detect_opportunity(
            self.spread_history["spread_ratio"]
        )

        # 格式化分析结果
        analysis = {
            "price1": price1,
            "price2": price2,
            "spread_ratio": spread_ratio,
            "spread_value": self.spread_engine.calculate_spread_value(price1, price2),
            "signal": signal,
            "historical_stats": self.deviation_detector.get_historical_stats(
                self.spread_history["spread_ratio"]
            ),
        }

        return analysis

    def get_strategy_status(self) -> Dict[str, Any]:
        """
        获取当前策略状态

        Returns:
            策略状态信息
        """
        return {
            "asset1": self.asset1_config["symbol"],
            "asset2": self.asset2_config["symbol"],
            "threshold": self.threshold,
            "lookback_days": self.lookback_days,
            "current_position": self.current_position,
            "history_length": len(self.spread_history),
        }
