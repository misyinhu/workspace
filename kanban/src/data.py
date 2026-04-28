"""Data fetching module."""

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    """Load instruments from instruments.yaml."""
    from pathlib import Path
    import yaml

    # instruments.yaml 在 kanban 目录下，不在 src/ 下
    instruments_path = Path(__file__).parent.parent / "instruments.yaml"
    try:
        if instruments_path.exists():
            with open(instruments_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data.get("instruments", [])
    except Exception:
        pass
    return []


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


def _calculate_ema(prices: list, period: int = 20) -> float:
    """Calculate EMA from price list."""
    if not prices or len(prices) < period:
        return sum(prices) / len(prices) if prices else 0
    ema = prices[0]
    multiplier = 2 / (period + 1)
    for price in prices[1:]:
        ema = (price - ema) * multiplier + ema
    return ema


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


def _calculate_bias_reason(
    prices: list, rsi: float, ema20: float, ema50: float, ema200: float | None = None
) -> list:
    """Calculate bias reasons based on indicators."""
    reasons = []
    if not prices or len(prices) < 2:
        return reasons

    current = prices[-1]
    prev = prices[-2]

    if ema200:
        if current > ema200:
            reasons.append(f"价格 ({current:.0f}) > 200 EMA ({ema200:.0f})")
        else:
            reasons.append(f"价格 ({current:.0f}) < 200 EMA ({ema200:.0f})")

    if current > ema20 > ema50:
        reasons.append("价格 > EMA20 > EMA50 (多头排列)")
    elif current < ema20 < ema50:
        reasons.append("价格 < EMA20 < EMA50 (空头排列)")

    if rsi > 70:
        reasons.append(f"RSI {rsi:.1f} 超买")
    elif rsi < 30:
        reasons.append(f"RSI {rsi:.1f} 超卖")
    elif rsi > 50:
        reasons.append(f"RSI {rsi:.1f} 偏多")
    else:
        reasons.append(f"RSI {rsi:.1f} 偏空")

    if current > prev:
        reasons.append(f"上涨 +{((current - prev) / prev * 100):.2f}%")
    elif current < prev:
        reasons.append(f"下跌 {((current - prev) / prev * 100):.2f}%")

    return reasons


def _calculate_momentum(prices: list, rsi: float) -> str:
    """Calculate momentum direction."""
    if not prices or len(prices) < 5:
        return "neutral"
    recent = prices[-5:]
    if recent[-1] > recent[0]:
        return "Rising"
    elif recent[-1] < recent[0]:
        return "Falling"
    return "neutral"


def _calculate_rsi_info(prices: list, period: int = 14) -> dict:
    """Calculate detailed RSI info."""
    if not prices or len(prices) < period + 1:
        return {"value": 50, "signal": "Neutral", "direction": "neutral"}

    current_rsi = _calculate_rsi(prices, period)
    prev_prices = prices[:-period]
    prev_rsi = _calculate_rsi(prev_prices, period) if len(prev_prices) >= period else 50

    if current_rsi > 60:
        signal = "Bullish"
    elif current_rsi < 40:
        signal = "Bearish"
    else:
        signal = "Neutral"

    if current_rsi > prev_rsi:
        direction = "Rising"
    elif current_rsi < prev_rsi:
        direction = "Falling"
    else:
        direction = "Neutral"

    return {
        "value": round(current_rsi, 2),
        "signal": signal,
        "direction": direction,
        "previous": round(prev_rsi, 2),
    }


def fetch_from_tv_api(symbol: str) -> dict:
    """Fetch data via TradingView /api/tv/multi-timeframe endpoint."""
    result = {"symbol": symbol, "timeframes": {}, "resonance": {}}

    # Timeframe mapping: frontend keys -> TV API intervals
    tf_map = {
        "1m": "1m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1h",
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
    result = {"symbol": symbol, "timeframes": {}, "resonance": {}, "error": None}

    # Timeframe to bar mapping (IB uses lowercase: 1h, 4h, not 1H, 4H)
    bar_map = {
        "1m": "1m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1h",
        "4h": "4h",
        "1D": "1D",
        "1W": "1W",
    }

    def _fetch_single_timeframe(tf: str) -> tuple:
        """Fetch and process a single timeframe."""
        bar = bar_map.get(tf, "1D")
        try:
            timeout = (15, 60) if source == "ib" else (10, 30)
            params = {
                "symbol": api_symbol,
                "source": source,
                "bar": bar,
                "num": 500,
            }
            response = requests.get(
                f"{QUANT_CORE_URL}/api/history",
                params=params,
                headers=headers,
                timeout=timeout,
            )
            if response.status_code == 200:
                bars = response.json()
                if bars and isinstance(bars, list) and len(bars) > 0:
                    closes = [b.get("close", 0) for b in bars if b.get("close")]
                    if closes:
                        latest = bars[-1]
                        rsi = _calculate_rsi(closes)
                        ema20 = _calculate_ema(closes, 20)
                        ema50 = _calculate_ema(closes, 50)
                        ema200 = _calculate_ema(closes, 200) if len(closes) >= 200 else None
                        trend = _calculate_trend_from_prices(closes)
                        bias_reasons = _calculate_bias_reason(closes, rsi, ema20, ema50, ema200)
                        rsi_info = _calculate_rsi_info(closes)
                        momentum = _calculate_momentum(closes, rsi)
                        change_pct = ((closes[-1] - closes[len(closes) // 2]) / closes[len(closes) // 2] * 100) if len(closes) >= 2 else 0

                        return tf, {
                            "close": latest.get("close", 0),
                            "open": latest.get("open", 0),
                            "high": latest.get("high", 0),
                            "low": latest.get("low", 0),
                            "volume": latest.get("volume", 0),
                            "rsi": rsi,
                            "trend": trend,
                            "bias": trend.upper(),
                            "bias_reasons": bias_reasons,
                            "rsi_info": rsi_info,
                            "momentum": momentum,
                            "ema20": round(ema20, 2),
                            "ema50": round(ema50, 2),
                            "ema200": round(ema200, 2) if ema200 else None,
                            "change_pct": round(change_pct, 3),
                            "key_indicators": ["EMA20", "EMA50", "RSI(14)", "MACD"],
                            "bars": bars[-200:] if len(bars) > 200 else bars,
                        }
            elif response.status_code != 204:
                try:
                    error_data = response.json()
                    return tf, {"error": error_data.get("error", response.text)}
                except Exception:
                    return tf, {"error": f"HTTP {response.status_code}: {response.text[:200]}"}
        except requests.exceptions.RequestException as e:
            return tf, {"error": f"请求错误: {str(e)}"}
        except Exception as e:
            return tf, {"error": f"数据获取失败: {str(e)}"}
        return tf, None

    # Parallel fetch all timeframes
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_fetch_single_timeframe, tf): tf for tf in TIMEFRAMES}
        for future in as_completed(futures):
            tf, tf_data = future.result()
            if tf_data:
                if "error" in tf_data:
                    result["error"] = tf_data["error"]
                else:
                    result["timeframes"][tf] = tf_data

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


def fetch_multi_timeframe(symbol: str, source: str = "ib") -> dict:
    """Fetch multi-timeframe data for a symbol.
    
    Args:
        symbol: Trading symbol (e.g., "2513.HK", "TSLA")
        source: Data source - "ib" for Interactive Brokers (default), "okx" for OKX
    """
    return fetch_from_history(symbol, source)


def fetch_pair_data(
    symbol1: str, symbol2: str, bar: str = "1D", num: int = 100,
    source1: str = "ib", source2: str = "ib"
) -> dict:
    """获取双品种数据用于套利分析
    
    Args:
        symbol1: First trading symbol
        symbol2: Second trading symbol  
        bar: Timeframe (e.g., "1D", "5m")
        num: Number of bars to fetch
        source1: Data source for symbol1 (default "ib")
        source2: Data source for symbol2 (default "ib")
    """
    # source1 and source2 are now passed directly, no lookup needed

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
