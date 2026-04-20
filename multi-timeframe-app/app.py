"""
Multi-Cycle Resonance Analysis System - Streamlit Application
MVP Version - quant-core API integration
"""
import os
import streamlit as st
import pandas as pd
import numpy as np
import yaml
from datetime import datetime, timedelta
import requests
import time

# ============================================================================
# Page Configuration
# ============================================================================
st.set_page_config(
    page_title="多周期共振分析系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# Configuration
# ============================================================================
TIMEFRAMES = ["1m", "5m", "30m", "4h", "1D"]
TIMEFRAME_LABELS = {
    "1m": "1分钟",
    "5m": "5分钟", 
    "30m": "30分钟",
    "4h": "4小时",
    "1D": "日线"
}

TREND_EMOJI = {"up": "📈", "down": "📉", "neutral": "➡️"}
TREND_CN = {"up": "上涨", "down": "下跌", "neutral": "震荡"}

# quant-core API 配置 (远程服务器)
QUANT_CORE_URL = "http://100.82.238.11:8005"
USE_MOCK_DATA = False  # 使用真实 quant-core API

# 常用品种配置文件路径
INSTRUMENTS_CONFIG_FILE = "instruments.yaml"

# ============================================================================
# API Functions
# ============================================================================
def load_instruments_config() -> list:
    """从配置文件加载常用品种"""
    try:
        import yaml
        config_path = os.path.join(os.path.dirname(__file__), INSTRUMENTS_CONFIG_FILE)
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                return config.get("instruments", [])
    except Exception as e:
        pass
    return []


def fetch_instruments(keyword: str = "") -> list:
    """获取品种列表"""
    config_instruments = load_instruments_config()
    if config_instruments:
        if keyword:
            return [i for i in config_instruments if keyword.lower() in i["symbol"].lower() 
                   or keyword.lower() in i.get("name", "").lower()]
        return config_instruments
    return mock_instruments(keyword)


def get_source_for_symbol(symbol: str) -> str:
    """根据品种获取对应的数据源"""
    config_instruments = load_instruments_config()
    if config_instruments:
        for inst in config_instruments:
            if inst["symbol"] == symbol:
                return inst.get("source", "okx")
    # 默认使用 tradingview 为未配置的品种
    return "tradingview"


def fetch_multi_timeframe(symbol: str) -> dict:
    # 3兜底和4回退已移除，严格按照：主数据源优先，主源无数据再回退到 TradingView
    # 不使用 Mock 数据作为兜底方案
    # 1) 主数据源优先
    primary_source = get_source_for_symbol(symbol)  # e.g. "ib", "okx", "tradingview"（默认）
    intervals = ",".join(TIMEFRAMES)

    if primary_source and primary_source != "tradingview":
        primary_data = fetch_from_history(symbol, primary_source)
        tf_data = primary_data.get("timeframes", {})
        has_valid = any(v.get("close", 0) > 0 for v in tf_data.values())
        if has_valid:
            return primary_data

    # 2) TradingView 回退（如果主源不可用或数据无效）
    try:
        response = requests.get(
            f"{QUANT_CORE_URL}/api/tv/multi-timeframe",
            params={
                "symbol": symbol,
                "intervals": intervals
            },
            timeout=15
        )
        if response.status_code == 200:
            data = response.json()
            return convert_tv_to_app_format(data)
    except Exception:
        pass
    # 3) 未取得数据，告知前端
    return {"symbol": symbol, "timeframes": {}, "resonance": {}, "error": "no_data"}


def convert_tv_to_app_format(tv_data: dict) -> dict:
    result = {"symbol": tv_data.get("symbol", ""), "timeframes": {}, "resonance": {}}
    directions = []
    
    tf_map = {"1m": "1", "5m": "5", "30m": "30", "4h": "240", "1D": "1D", "1W": "1W"}
    
    for tf, tv_tf in tf_map.items():
        if tv_tf in tv_data.get("timeframes", {}):
            tf_data = tv_data["timeframes"][tv_tf]
            
            ma_rec = tf_data.get("ma_recommendation", "NEUTRAL")
            osc_rec = tf_data.get("oscillator_recommendation", "NEUTRAL")
            
            if ma_rec in ["STRONG_BUY", "BUY"] or osc_rec in ["STRONG_BUY", "BUY"]:
                direction_en = "up"
            elif ma_rec in ["STRONG_SELL", "SELL"] or osc_rec in ["STRONG_SELL", "SELL"]:
                direction_en = "down"
            else:
                direction_en = "neutral"
            
            directions.append(direction_en)
            
            close = tf_data.get("close", 0)
            rsi = tf_data.get("rsi", 0)
            
            result["timeframes"][tf] = {
                "trend": direction_en,
                "close": close,
                "change_pct": 0,
                "rsi": round(rsi, 1) if rsi else 0,
                "ma_rec": ma_rec,
                "osc_rec": osc_rec
            }
    
    if directions:
        result["resonance"] = calculate_resonance_en(directions)
    
    return result


def fetch_from_history(symbol: str, source: str) -> dict:
    """从历史数据获取并自己计算分析"""
    result = {"symbol": symbol, "timeframes": {}, "resonance": {}}
    directions = []
    
    # OKX 需要的格式转换
    symbol_map = {
        "DOGEUSDT": "DOGE-USDT",
        "ETHUSDT": "ETH-USDT",
        "BTCUSDT": "BTC-USDT"
    }
    okx_symbol = symbol_map.get(symbol, symbol)
    
    if source == "okx":
        # 使用本地 quant_core OKX 数据源
        import sys
        quant_root = "/Users/wang/.opencode/workspace/quant"
        if quant_root not in sys.path:
            sys.path.insert(0, quant_root)
        
        try:
            from quant_core.sources import create_datasource
            
            okx = create_datasource("okx")
            
            bar_map = {
                "1m": "1m", "5m": "5m", "30m": "30m", 
                "4h": "4H", "1D": "1D", "1W": "1W"
            }
            
            for tf in TIMEFRAMES:
                try:
                    bar_param = bar_map.get(tf, "1H")
                    bars = okx.get_history(okx_symbol, bar_size=bar_param, num=100)
                    
                    if bars and len(bars) > 0:
                        closes = [b.close for b in bars]
                        current_price = closes[-1]
                        
                        rsi = calculate_rsi_local(closes)
                        
                        ma20 = calculate_ma_local(closes, 20) if len(closes) >= 20 else None
                        if ma20 and current_price > ma20:
                            ma_signal = "BUY"
                            direction_en = "up"
                        elif ma20 and current_price < ma20:
                            ma_signal = "SELL"
                            direction_en = "down"
                        else:
                            ma_signal = "NEUTRAL"
                            direction_en = "neutral"
                        
                        if rsi < 30:
                            osc_signal = "BUY"
                        elif rsi > 70:
                            osc_signal = "SELL"
                        else:
                            osc_signal = "NEUTRAL"
                        
                        directions.append(direction_en)
                        
                        result["timeframes"][tf] = {
                            "trend": direction_en,
                            "close": current_price,
                            "change_pct": round((closes[-1] - closes[-2]) / closes[-2] * 100, 2) if len(closes) > 1 else 0,
                            "rsi": round(rsi, 1),
                            "ma_rec": ma_signal,
                            "osc_rec": osc_signal,
                            "ma20": round(ma20, 4) if ma20 else 0
                        }
                        continue
                except Exception as e:
                    pass
                
                directions.append("neutral")
                result["timeframes"][tf] = {
                    "trend": "neutral",
                    "close": 0,
                    "change_pct": 0,
                    "rsi": 50,
                    "ma_rec": "NEUTRAL",
                    "osc_rec": "NEUTRAL",
                    "ma20": 0
                }
        except Exception as e:
            pass
    else:
        # IB 数据源 - 使用 quant-core API
        for tf in TIMEFRAMES:
            try:
                response = requests.get(
                    f"{QUANT_CORE_URL}/api/history",
                    params={
                        "symbol": symbol,
                        "source": source,
                        "bar": tf,
                        "num": 300
                    },
                    timeout=15
                )
                
                if response.status_code == 200:
                    bars = response.json()
                    if bars and len(bars) > 0:
                        df = pd.DataFrame(bars)
                        trend = calculate_trend(df)
                        
                        direction_en = "up" if trend["direction"] == "上涨" else "down" if trend["direction"] == "下跌" else "neutral"
                        directions.append(direction_en)
                        
                        latest = df.iloc[-1]
                        prev = df.iloc[-2] if len(df) > 1 else latest
                        change_pct = ((latest['close'] - prev['close']) / prev['close'] * 100) if prev['close'] else 0
                        
                        result["timeframes"][tf] = {
                            "trend": direction_en,
                            "close": latest['close'],
                            "change_pct": round(change_pct, 2),
                            "rsi": 50,
                            "ma_rec": "NEUTRAL",
                            "osc_rec": "NEUTRAL",
                            "ma20": round(df['close'].iloc[-20:].mean(), 2) if len(df) >= 20 else latest['close']
                        }
                        continue
            except Exception as e:
                pass
            
            directions.append("neutral")
            result["timeframes"][tf] = {
                "trend": "neutral",
                "close": 0,
                "change_pct": 0,
                "rsi": 50,
                "ma_rec": "NEUTRAL",
                "osc_rec": "NEUTRAL",
                "ma20": 0
            }
    
    if directions:
        result["resonance"] = calculate_resonance_en(directions)
    
    return result


def calculate_rsi_local(prices: list, period: int = 14) -> float:
    """本地计算 RSI"""
    if len(prices) < period + 1:
        return 50.0
    
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_ma_local(prices: list, period: int) -> float:
    """本地计算 MA"""
    if len(prices) < period:
        return 0.0
    return sum(prices[-period:]) / period


# ============================================================================
# Mock Data Functions
# ============================================================================
def format_price(price: float) -> str:
    """根据价格大小智能格式化显示"""
    if price >= 1000:
        return f"{price:.2f}"
    elif price >= 1:
        return f"{price:.4f}"
    else:
        return f"{price:.6f}"


def mock_instruments(keyword: str = "") -> list:
    instruments = [
        {"symbol": "DOGEUSDT", "name": "DOGE永续", "exchange": "OKX", "source": "okx"},
        {"symbol": "ETHUSDT", "name": "ETH永续", "exchange": "OKX", "source": "okx"},
        {"symbol": "BTCUSDT", "name": "BTC永续", "exchange": "OKX", "source": "okx"},
        {"symbol": "AAPL", "name": "Apple", "exchange": "NASDAQ", "source": "tradingview"},
        {"symbol": "TSLA", "name": "Tesla", "exchange": "NASDAQ", "source": "tradingview"},
        {"symbol": "ES", "name": "E-mini S&P 500", "exchange": "CME", "source": "tradingview"},
    ]
    if keyword:
        instruments = [i for i in instruments if keyword.lower() in i["symbol"].lower() 
                       or keyword.lower() in i["name"].lower()]
    return instruments


def generate_mock_ohlc(symbol: str, timeframe: str, periods: int = 100) -> pd.DataFrame:
    """Generate mock OHLC data for demonstration."""
    np.random.seed(hash(f"{symbol}{timeframe}") % 2**32)
    
    base_prices = {"ES": 5800, "NQ": 19800, "YM": 42000, "GC": 2350, "SI": 28, "CL": 75, "HG": 450, "ZN": 108}
    base = base_prices.get(symbol, 100)
    
    volatility = {"1m": 0.001, "5m": 0.003, "30m": 0.008, "4h": 0.02}
    vol = volatility.get(timeframe, 0.01)
    
    returns = np.random.normal(0, vol, periods)
    prices = base * np.exp(np.cumsum(returns))
    
    data = []
    now = datetime.now()
    
    deltas = {"1m": timedelta(minutes=1), "5m": timedelta(minutes=5), "30m": timedelta(minutes=30), "4h": timedelta(hours=4)}
    delta = deltas.get(timeframe, timedelta(minutes=1))
    
    for i in range(periods):
        close = prices[i]
        open_price = close * (1 + np.random.uniform(-0.002, 0.002))
        high = max(open_price, close) * (1 + np.random.uniform(0, 0.005))
        low = min(open_price, close) * (1 - np.random.uniform(0, 0.005))
        volume = int(np.random.uniform(1000, 10000))
        
        data.append({
            "timestamp": now - delta * (periods - i),
            "open": round(open_price, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(close, 2),
            "volume": volume
        })
    
    return pd.DataFrame(data)


def mock_multi_timeframe(symbol: str) -> dict:
    result = {"symbol": symbol, "timeframes": {}, "resonance": {}}
    directions = []
    
    for tf in TIMEFRAMES:
        ohlc = generate_mock_ohlc(symbol, tf)
        trend = calculate_trend(ohlc)
        
        direction_en = "up" if trend["direction"] == "上涨" else "down" if trend["direction"] == "下跌" else "neutral"
        directions.append(direction_en)
        
        closes = ohlc["close"].values
        latest_close = closes[-1]
        prev_close = closes[-2] if len(closes) > 1 else latest_close
        change_pct = ((latest_close - prev_close) / prev_close * 100) if prev_close else 0
        
        result["timeframes"][tf] = {
            "trend": direction_en,
            "close": latest_close,
            "change_pct": round(change_pct, 2),
            "ma20": round(np.mean(closes[-20:]), 2) if len(closes) >= 20 else 0
        }
    
    resonance = calculate_resonance_en(directions)
    result["resonance"] = resonance
    
    return result


def calculate_trend(ohlc_df: pd.DataFrame) -> dict:
    if len(ohlc_df) < 20:
        return {"direction": "震荡", "strength": 50}
    
    closes = ohlc_df["close"].values
    n = len(closes)
    
    sma_short = np.mean(closes[-10:])
    sma_medium = np.mean(closes[-30:]) if n >= 30 else np.mean(closes[-n:])
    sma_long = np.mean(closes[-60:]) if n >= 60 else sma_medium
    
    if sma_short > sma_medium > sma_long:
        direction = "上涨"
    elif sma_short < sma_medium < sma_long:
        direction = "下跌"
    else:
        direction = "震荡"
    
    recent_len = min(30, n)
    price_range = np.max(closes[-recent_len:]) - np.min(closes[-recent_len:])
    recent_change = (closes[-1] - closes[-recent_len]) / closes[-recent_len] * 100 if price_range > 0 else 0
    
    strength = min(100, max(0, 50 + recent_change * 10))
    
    return {"direction": direction, "strength": int(strength)}


def calculate_resonance_en(directions: list) -> dict:
    up_count = directions.count("up")
    down_count = directions.count("down")
    neutral_count = directions.count("neutral")
    
    if up_count >= 3 or down_count >= 3:
        score = 70 + (max(up_count, down_count) - 3) * 10
        level = "high"
    elif up_count + down_count >= 3:
        score = 50 + (up_count + down_count - 3) * 5
        level = "medium"
    elif directions:
        score = 30 + neutral_count * 5
        level = "low"
    else:
        score = 0
        level = "low"
    
    score = min(100, max(0, score))
    
    return {
        "score": score,
        "level": level,
        "distribution": {
            "up": up_count,
            "down": down_count,
            "neutral": neutral_count
        }
    }


# ============================================================================
# UI Components
# ============================================================================
def render_sidebar():
    """Render sidebar with instrument selection and settings."""
    st.sidebar.title("🔍 品种选择")
    
    # 常用品种下拉选择
    st.sidebar.subheader("常用品种")
    instruments = fetch_instruments()
    
    if instruments:
        instrument_options = [""] + [f"{inst['symbol']} - {inst['name']}" for inst in instruments]
        selected = st.sidebar.selectbox(
            "选择品种",
            instrument_options,
            index=0,
            key="instrument_select"
        )
        preset_symbol = selected.split(" - ")[0] if selected else ""
    else:
        preset_symbol = ""
    
    # 自定义品种输入
    st.sidebar.subheader("或输入品种")
    custom_symbol = st.sidebar.text_input(
        "输入品种代码",
        placeholder="如: TSLA, AAPL, DOGEUSDT...",
        key="custom_symbol_input"
    ).strip().upper()
    
    # 确定最终选择的品种
    if custom_symbol:
        symbol = custom_symbol
        source = "tradingview"  # 自定义品种走 tradingview
    elif preset_symbol:
        symbol = preset_symbol
        source = get_source_for_symbol(symbol)
    else:
        symbol = "DOGEUSDT"
        source = "okx"
    
    # 显示品种详细信息
    st.sidebar.markdown("---")
    if custom_symbol:
        st.sidebar.info(f"**自定义品种**: {symbol}\n\n**数据源**: TradingView")
    elif preset_symbol:
        inst_info = next((i for i in instruments if i["symbol"] == symbol), None)
        if inst_info:
            st.sidebar.markdown(f"**{inst_info.get('name', symbol)}**")
            st.sidebar.markdown(f"- 代码: {inst_info['symbol']}")
            st.sidebar.markdown(f"- 交易所: {inst_info['exchange']}")
            st.sidebar.markdown(f"- 数据源: {inst_info['source']}")
    
    # 设置选项
    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ 设置")
    
    auto_refresh = st.sidebar.toggle("自动刷新", value=False, key="auto_refresh")
    refresh_interval = 10
    if auto_refresh:
        refresh_interval = st.sidebar.slider("刷新间隔(秒)", 5, 60, 10, key="refresh_interval")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**时间周期**: 1m, 5m, 30m, 4h (固定)")
    st.sidebar.markdown(f"**数据模式**: {'Mock (模拟)' if USE_MOCK_DATA else 'API'}")
    
    return symbol, auto_refresh, refresh_interval


def render_timeframe_cards(timeframe_data: dict):
    if not timeframe_data:
        st.warning("暂无数据，请选择品种")
        return
    
    cols = st.columns(4)
    col_idx = 0
    
    for tf in TIMEFRAMES:
        if tf not in timeframe_data:
            continue
        if col_idx >= 4:
            break
            
        data = timeframe_data[tf]
        trend = data.get("trend", "neutral")
        close = data.get("close", 0)
        
        emoji = TREND_EMOJI.get(trend, "➡️")
        trend_cn = TREND_CN.get(trend, "震荡")
        
        with cols[col_idx]:
            with st.container(border=True):
                st.markdown(f"**{TIMEFRAME_LABELS[tf]}**")
                st.markdown(f":{emoji} {trend_cn}")
                st.markdown(f"**{format_price(close)}**")
                
                rsi = data.get("rsi", 0)
                if rsi:
                    st.caption(f"RSI: {rsi}")
                
                ma_rec = data.get("ma_rec", "")
                osc_rec = data.get("osc_rec", "")
                if ma_rec:
                    st.caption(f"MA: {ma_rec}")
        
        col_idx += 1


def render_resonance_gauge(resonance_data: dict):
    if not resonance_data:
        return
    
    score = resonance_data.get("score", 0)
    level = resonance_data.get("level", "low")
    distribution = resonance_data.get("distribution", {})
    
    level_text = "强共振" if level == "high" else "中等共振" if level == "medium" else "分歧"
    level_emoji = "🟢" if level == "high" else "🟡" if level == "medium" else "🔴"
    
    with st.container(border=True):
        st.markdown("### 🎯 共振评分")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric("综合得分", f"{score}", f"{level_emoji} {level_text}")
        with col2:
            st.progress(score / 100)
        
        st.divider()
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("上涨周期", f"{distribution.get('up', 0)}", "📈")
        with col_b:
            st.metric("震荡周期", f"{distribution.get('neutral', 0)}", "➡️")
        with col_c:
            st.metric("下跌周期", f"{distribution.get('down', 0)}", "📉")


# ============================================================================
# Main Application
# ============================================================================
def main():
    """Main application entry point."""
    st.title("📈 多周期共振分析系统")
    st.markdown("**MVP版本**")
    
    # 侧边栏
    selected_symbol, auto_refresh, refresh_interval = render_sidebar()
    
    st.markdown("---")
    
    # 自动刷新
    if auto_refresh:
        placeholder = st.empty()
        while auto_refresh:
            with placeholder.container():
                # 获取数据
                data = fetch_multi_timeframe(selected_symbol)
                timeframe_data = data.get("timeframes", {})
                resonance_data = data.get("resonance", {})
                
                # 显示内容
                render_main_content(timeframe_data, resonance_data, selected_symbol)
            
            time.sleep(refresh_interval)
    else:
        # 单次加载
        with st.spinner("加载数据中..."):
            data = fetch_multi_timeframe(selected_symbol)
            timeframe_data = data.get("timeframes", {})
            resonance_data = data.get("resonance", {})
        
        if not timeframe_data:
            st.error("无法获取数据，请稍后重试")
            return
        render_main_content(timeframe_data, resonance_data, selected_symbol)


def render_main_content(timeframe_data: dict, resonance_data: dict, symbol: str):
    """渲染主内容区域"""
    # 周期卡片 (4列横向)
    st.markdown("### 📊 各周期趋势")
    render_timeframe_cards(timeframe_data)
    
    st.markdown("---")
    
    # 右侧：共振分数 + 汇总
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.markdown("### 🎯 共振分数")
        render_resonance_gauge(resonance_data)
    
    with col_right:
        st.markdown("### 📋 多周期汇总")
        
        # 汇总表格
        summary_data = []
        for tf in TIMEFRAMES:
            if tf in timeframe_data:
                tf_data = timeframe_data[tf]
                trend = tf_data.get("trend", "neutral")
                summary_data.append({
                    "周期": TIMEFRAME_LABELS.get(tf, tf),
                    "方向": TREND_CN.get(trend, "震荡"),
                    "价格": f"{tf_data.get('close', 0):.2f}"
                })
        
        if summary_data:
            st.table(pd.DataFrame(summary_data))
        
        # 综合判断
        distribution = resonance_data.get("distribution", {})
        up = distribution.get("up", 0)
        down = distribution.get("down", 0)
        
        if up >= 3:
            overall = "🟢 整体看涨"
        elif down >= 3:
            overall = "🔴 整体看跌"
        else:
            overall = "🟡 震荡整理"
        
        st.markdown(f"**综合判断**: {overall}")
        
        # 数据信息
        st.markdown("---")
        st.markdown("### ℹ️ 数据信息")
        st.markdown(f"**更新时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        st.markdown(f"**数据源**: {'模拟数据 (Mock)' if USE_MOCK_DATA else 'quant-core API'}")
        st.markdown(f"**服务器**: {'未连接' if USE_MOCK_DATA else QUANT_CORE_URL}")


if __name__ == "__main__":
    main()
