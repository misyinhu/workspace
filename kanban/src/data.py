"""Data fetching module."""

import requests
from datetime import datetime, timedelta
from .config import QUANT_CORE_URL, CLIENT_ID, TIMEFRAMES


def get_tv_symbol_for_ib(symbol: str) -> str:
    """Map IB symbol to TradingView format."""
    tv_symbol_map = {
        "ES": "ES.cme",
        "GC": "GC.cme",
        "MNQ": "MNQ.cme",
        "MYM": "MYM.cme",
        "MGC": "MGC.cme",
        "MHG": "MHG.cme",
        "RB": "RB.nyex",
        "HO": "HO.nyex",
        "AAPL": "AAPL.nasdaq",
        "TSLA": "TSLA.nasdaq",
    }
    return tv_symbol_map.get(symbol, symbol)


def load_instruments_config() -> list:
    """Load instruments from shared config."""
    from .config import load_shared_config

    config = load_shared_config()
    return config.get("instruments", [])


def get_source_for_symbol(symbol: str) -> str:
    """Determine data source for symbol."""
    instruments = load_instruments_config()
    for inst in instruments:
        if inst["symbol"] == symbol:
            return inst.get("source", "okx")
    return "tradingview"


def _calculate_rsi(prices: list, period: int = 14) -> float:
    """Calculate RSI from price list."""
    if not prices or len(prices) < period:
        return 50.0
    deltas = []
    for i in range(1, len(prices)):
        deltas.append(prices[i] - prices[i - 1])
    gains = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]
    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _calculate_trend_from_prices(prices: list) -> str:
    """Calculate trend from price list using MA20."""
    if not prices or len(prices) < 20:
        return "neutral"
    ma20 = sum(prices[-20:]) / 20
    current = prices[-1]
    if current > ma20 * 1.01:
        return "up"
    elif current < ma20 * 0.99:
        return "down"
    return "neutral"


def fetch_from_tv_api(symbol: str) -> dict:
    """Fetch data via TradingView /api/tv/multi-timeframe endpoint."""
    result = {"symbol": symbol, "timeframes": {}, "resonance": {}}

    # Timeframe mapping: frontend keys -> TV API intervals
    tf_map = {
        "1m": "1m",
        "5m": "5m",
        "30m": "30m",
        "4h": "4h",
        "1D": "1D",
    }

    intervals = ",".join(tf_map.values())

    try:
        params = {"symbol": symbol, "intervals": intervals}
        response = requests.get(
            f"{QUANT_CORE_URL}/api/tv/multi-timeframe", params=params, timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            tf_data = data.get("timeframes", {})

            # Map TV intervals back to frontend timeframe keys
            reverse_map = {v: k for k, v in tf_map.items()}

            # Count trends for resonance
            up_count = 0
            down_count = 0
            neutral_count = 0

            for tv_interval, tf_info in tf_data.items():
                if "error" in tf_info:
                    continue

                frontend_key = reverse_map.get(tv_interval, tv_interval)
                close = tf_info.get("close", 0)
                rsi = tf_info.get("rsi", 50)

                # Determine trend from MA recommendation
                ma_rec = tf_info.get("ma_recommendation", "").upper()
                if ma_rec in ("STRONG_BUY", "BUY"):
                    trend = "up"
                    up_count += 1
                elif ma_rec in ("STRONG_SELL", "SELL"):
                    trend = "down"
                    down_count += 1
                else:
                    trend = "neutral"
                    neutral_count += 1

                result["timeframes"][frontend_key] = {
                    "close": close,
                    "rsi": rsi,
                    "trend": trend,
                }

            # Calculate resonance score
            total = up_count + down_count + neutral_count
            if total > 0:
                score = int(max(up_count, down_count) / total * 100)
                result["resonance"] = {
                    "score": score,
                    "level": "高" if score >= 75 else "中" if score >= 50 else "低",
                    "distribution": {
                        "up": up_count,
                        "down": down_count,
                        "neutral": neutral_count,
                    },
                }
    except Exception:
        pass

    return result


def fetch_from_history(symbol: str, source: str) -> dict:
    """Fetch historical data and calculate indicators."""
    # Use TradingView API for tradingview source
    if source == "tradingview":
        return fetch_from_tv_api(symbol)

    # Map symbol for different sources
    if source == "okx":
        symbol_map = {
            "DOGE-USDT-SWAP": "DOGE-USDT",
            "ETH-USDT-SWAP": "ETH-USDT",
            "BTC-USDT-SWAP": "BTC-USDT",
        }
        api_symbol = symbol_map.get(symbol, symbol)
    elif source == "ib":
        # Don't convert - IB source expects raw IB symbols like "MNQ", not "MNQ.cme"
        api_symbol = symbol
    else:
        api_symbol = symbol

    headers = {"X-Client-ID": CLIENT_ID}
    result = {"symbol": symbol, "timeframes": {}, "resonance": {}}

    # Timeframe to bar mapping
    bar_map = {
        "1m": "1m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1H",
        "4h": "4H",
        "1D": "1D",
        "1W": "1W",
    }

    for tf in TIMEFRAMES:
        bar = bar_map.get(tf, "1D")
        try:
            # Try with num parameter first (latest N bars)
            params = {
                "symbol": api_symbol,
                "source": source,
                "bar": bar,
                "num": 100,  # Get 100 bars for RSI calculation
            }
            response = requests.get(
                f"{QUANT_CORE_URL}/api/history",
                params=params,
                headers=headers,
                timeout=30,
            )
            if response.status_code == 200:
                bars = response.json()
                if bars and isinstance(bars, list) and len(bars) > 0:
                    closes = [b.get("close", 0) for b in bars if b.get("close")]
                    if closes:
                        latest = bars[-1]
                        rsi = _calculate_rsi(closes)
                        trend = _calculate_trend_from_prices(closes)
                        result["timeframes"][tf] = {
                            "close": latest.get("close", 0),
                            "open": latest.get("open", 0),
                            "high": latest.get("high", 0),
                            "low": latest.get("low", 0),
                            "volume": latest.get("volume", 0),
                            "rsi": rsi,
                            "trend": trend,
                        }
        except Exception:
            pass

    # Calculate resonance from trends
    trends = [
        tf_data.get("trend", "neutral") for tf_data in result["timeframes"].values()
    ]
    if trends:
        up = sum(1 for t in trends if t == "up")
        down = sum(1 for t in trends if t == "down")
        neutral = sum(1 for t in trends if t == "neutral")
        total = len(trends)
        score = int(max(up, down) / total * 100) if total > 0 else 0
        result["resonance"] = {
            "score": score,
            "level": "高" if score >= 75 else "中" if score >= 50 else "低",
            "distribution": {"up": up, "down": down, "neutral": neutral},
        }

    return result


def fetch_multi_timeframe(symbol: str) -> dict:
    """Fetch multi-timeframe data for a symbol."""
    source = get_source_for_symbol(symbol)
    return fetch_from_history(symbol, source)


def fetch_pair_data(
    symbol1: str, symbol2: str, bar: str = "1D", num: int = 100
) -> dict:
    """获取双品种数据用于套利分析"""
    source1 = get_source_for_symbol(symbol1)
    source2 = get_source_for_symbol(symbol2)

    headers = {"X-Client-ID": CLIENT_ID}

    # 获取品种1历史数据
    bars1 = []
    try:
        params1 = {"symbol": symbol1, "source": source1, "bar": bar, "num": num}
        r1 = requests.get(
            f"{QUANT_CORE_URL}/api/history", params=params1, headers=headers, timeout=30
        )
        if r1.status_code == 200:
            bars1 = r1.json()
    except Exception:
        pass

    # 获取品种2历史数据
    bars2 = []
    try:
        params2 = {"symbol": symbol2, "source": source2, "bar": bar, "num": num}
        r2 = requests.get(
            f"{QUANT_CORE_URL}/api/history", params=params2, headers=headers, timeout=30
        )
        if r2.status_code == 200:
            bars2 = r2.json()
    except Exception:
        pass

    return {
        "symbol1": symbol1,
        "symbol2": symbol2,
        "source1": source1,
        "source2": source2,
        "bars1": bars1,
        "bars2": bars2,
    }
