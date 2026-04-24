"""Analysis module (RSI, MA, 共振, 矛盾检测)."""

import numpy as np
import pandas as pd
from .config import TIMEFRAMES


def calculate_rsi_local(prices: list, period: int = 14) -> float:
    if not prices or len(prices) < period:
        return 50.0
    prices = np.array(prices)
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_ma_local(prices: list, period: int) -> float:
    if not prices or len(prices) < period:
        return 0.0
    return np.mean(prices[-period:])


def calculate_trend(ohlc_df: pd.DataFrame) -> dict:
    if ohlc_df.empty:
        return {"trend": "neutral", "rsi": 50}
    close = ohlc_df["close"].tolist()
    rsi = calculate_rsi_local(close)
    ma20 = calculate_ma_local(close, 20)
    ma60 = calculate_ma_local(close, 60) if len(close) >= 60 else ma20
    current = close[-1] if close else 0
    if current > ma20:
        trend = "up"
    elif current < ma20:
        trend = "down"
    else:
        trend = "neutral"
    return {"trend": trend, "rsi": rsi}


def calculate_resonance_en(directions: list) -> dict:
    if not directions:
        return {"score": 0, "level": "低", "distribution": {}}
    up = sum(1 for d in directions if d == "up")
    down = sum(1 for d in directions if d == "down")
    neutral = sum(1 for d in directions if d == "neutral")
    total = len(directions)
    score = int((max(up, down) / total * 100) if total > 0 else 0)
    if score >= 75:
        level = "高"
    elif score >= 50:
        level = "中"
    else:
        level = "低"
    return {
        "score": score,
        "level": level,
        "distribution": {"up": up, "down": down, "neutral": neutral},
    }


def detect_contradictions(timeframe_data: dict) -> dict:
    if not timeframe_data:
        return {"has_contradiction": False, "contradictions": [], "divergence_score": 0}
    directions = []
    tf_list = []
    for tf in TIMEFRAMES:
        if tf in timeframe_data:
            trend = timeframe_data[tf].get("trend", "neutral")
            directions.append(trend)
            tf_list.append((tf, trend))
    contradictions = []
    up_tfs = [tf for tf, d in tf_list if d == "up"]
    down_tfs = [tf for tf, d in tf_list if d == "down"]
    if up_tfs and down_tfs:
        short_up = any(tf in ["1m", "5m"] for tf in up_tfs)
        short_down = any(tf in ["1m", "5m"] for tf in down_tfs)
        long_up = any(tf in ["4h", "1D"] for tf in up_tfs)
        long_down = any(tf in ["4h", "1D"] for tf in down_tfs)
        if short_up and long_down:
            contradictions.append({"type": "短多长空", "risk": "high"})
        elif short_down and long_up:
            contradictions.append({"type": "短空长多", "risk": "high"})
    divergence_score = 0
    if up_tfs and down_tfs:
        divergence_score = int(
            abs(len(up_tfs) - len(down_tfs)) / max(len(directions), 1) * 100
        )
    return {
        "has_contradiction": bool(contradictions),
        "contradictions": contradictions,
        "divergence_score": divergence_score,
    }


# ============ 套利分析函数 ============


def calculate_spread(bars1: list, bars2: list) -> list:
    """计算价差序列"""
    if not bars1 or not bars2:
        return []
    closes1 = [b.get("close", 0) for b in bars1]
    closes2 = [b.get("close", 0) for b in bars2]
    min_len = min(len(closes1), len(closes2))
    return [closes1[i] - closes2[i] for i in range(min_len)]


def calculate_ratio(bars1: list, bars2: list) -> list:
    """计算比率序列"""
    if not bars1 or not bars2:
        return []
    closes1 = [b.get("close", 0) for b in bars1]
    closes2 = [b.get("close", 0) for b in bars2]
    min_len = min(len(closes1), len(closes2))
    return [closes1[i] / closes2[i] if closes2[i] != 0 else 0 for i in range(min_len)]


def calculate_correlation(bars1: list, bars2: list, window: int = 20) -> float:
    """计算皮尔逊相关系数"""
    if not bars1 or not bars2 or len(bars1) < window:
        return 0.0
    closes1 = np.array([b.get("close", 0) for b in bars1[-window:]])
    closes2 = np.array([b.get("close", 0) for b in bars2[-window:]])
    if np.std(closes1) == 0 or np.std(closes2) == 0:
        return 0.0
    return float(np.corrcoef(closes1, closes2)[0, 1])


def calculate_zscore(spread_series: list) -> dict:
    """计算 Z-Score"""
    if not spread_series or len(spread_series) < 2:
        return {"zscore": 0, "mean": 0, "std": 0}
    spread = np.array(spread_series)
    mean = float(np.mean(spread))
    std = float(np.std(spread))
    current = spread[-1]
    zscore = (current - mean) / std if std != 0 else 0
    return {"zscore": float(zscore), "mean": mean, "std": std}


def generate_arbitrage_signal(
    zscore: float, correlation: float, rsi1: float, rsi2: float
) -> dict:
    """多条件组合信号生成"""
    from .config import ARBITRAGE_DEFAULTS

    zscore_threshold = ARBITRAGE_DEFAULTS["zscore_threshold"]
    corr_threshold = ARBITRAGE_DEFAULTS["correlation_threshold"]
    rsi_div_threshold = ARBITRAGE_DEFAULTS["rsi_divergence_threshold"]

    signals = []

    # 条件1: Z-Score > 3σ
    if abs(zscore) > zscore_threshold:
        signal_type = "ZSCORE_LONG" if zscore > 0 else "ZSCORE_SHORT"
        signals.append((signal_type, zscore))

    # 条件2: 相关性 > 0.8
    if correlation > corr_threshold:
        signals.append(("CORRELATION_OK", correlation))

    # 条件3: RSI 背离
    if abs(rsi1 - rsi2) > rsi_div_threshold:
        signals.append(("RSI_DIVERGE", abs(rsi1 - rsi2)))

    # 综合判断
    has_zscore_long = any(s[0] == "ZSCORE_LONG" for s in signals)
    has_zscore_short = any(s[0] == "ZSCORE_SHORT" for s in signals)
    has_corr = any(s[0] == "CORRELATION_OK" for s in signals)

    if has_zscore_long and has_corr:
        return {
            "signal": "SELL_SPREAD",
            "emoji": "📉",
            "reason": f"价差偏高 Z={zscore:.2f}, 相关性={correlation:.2f}",
        }
    elif has_zscore_short and has_corr:
        return {
            "signal": "BUY_SPREAD",
            "emoji": "📈",
            "reason": f"价差偏低 Z={zscore:.2f}, 相关性={correlation:.2f}",
        }

    return {"signal": "WATCH", "emoji": "➡️", "reason": "条件未触发"}
