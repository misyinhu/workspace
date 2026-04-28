"""Market Scanner Page - 市场扫描"""

import streamlit as st
import pandas as pd
import requests
import time

from src.config import QUANT_CORE_URL, CLIENT_ID
from src.data import load_instruments_config

st.set_page_config(page_title="市场扫描", page_icon="🔍", layout="wide")

SCANNER_TYPES = {
    "volume_breakout": "📊 交易量突破",
    "bollinger": "🎯 布林带分析",
    "trending": "📈 趋势分析",
    "consecutive": "🔥 连续K线",
    "multi_changes": "🔄 多周期变化",
}

# 交易所选项
EXCHANGES = {
    "okx": "OKX (加密)",
    "sse": "上交所 (A股)",
    "szse": "深交所 (A股)",
}


def render_sidebar():
    with st.sidebar:
        st.title("🔍 市场扫描")

        # 扫描类型单选
        st.subheader("选择扫描类型")
        selected_scanner = st.radio(
            "扫描类型",
            options=list(SCANNER_TYPES.keys()),
            format_func=lambda x: SCANNER_TYPES[x],
            index=0,
            horizontal=True,
        )

        st.subheader("选择市场")

        # 常用品种选项
        use_common = st.checkbox(
            "⭐ 常用品种", value=True, key="use_common_instruments"
        )

        # 交易所选项
        selected_exchanges = []
        for key, label in EXCHANGES.items():
            if st.checkbox(label, value=False, key=f"exchange_{key}"):
                selected_exchanges.append(key)

        # 根据扫描类型显示不同参数
        st.subheader("扫描参数")

        if selected_scanner == "volume_breakout":
            timeframe = st.selectbox(
                "时间周期", ["5m", "15m", "30m", "1h", "4h"], index=1
            )
            volume_multiplier = st.slider("放量倍数", 1.5, 5.0, 2.0, 0.5)
            price_change_min = st.slider("最小价格变化%", 1.0, 10.0, 3.0, 0.5)
            limit = st.slider("返回数量", 5, 50, 25, 5)

        elif selected_scanner == "bollinger":
            timeframe = st.selectbox(
                "时间周期", ["5m", "15m", "30m", "1h", "4h"], index=1
            )
            bb_period = st.slider("布林带周期", 10, 30, 20, 5)
            bb_std = st.slider("标准差倍数", 1.5, 3.0, 2.0, 0.5)
            limit = st.slider("返回数量", 5, 50, 25, 5)

        elif selected_scanner == "trending":
            timeframe = st.selectbox(
                "时间周期", ["5m", "15m", "30m", "1h", "4h"], index=1
            )
            ma_period = st.slider("MA周期", 10, 50, 20, 10)
            limit = st.slider("返回数量", 5, 50, 25, 5)

        elif selected_scanner == "consecutive":
            timeframe = st.selectbox(
                "时间周期", ["5m", "15m", "30m", "1h", "4h"], index=1
            )
            consecutive_count = st.slider("连续K线数", 3, 10, 3, 1)
            limit = st.slider("返回数量", 5, 50, 25, 5)

        elif selected_scanner == "multi_changes":
            timeframe = st.selectbox(
                "时间周期", ["5m", "15m", "30m", "1h", "4h"], index=1
            )
            change_threshold = st.slider("变化阈值%", 1.0, 10.0, 1.0, 0.5)
            limit = st.slider("返回数量", 5, 50, 25, 5)

        scan_params = {
            "scanners": [selected_scanner],  # 单选，包装为列表
            "exchanges": selected_exchanges,
            "use_common": use_common,
            "timeframe": timeframe,
            "limit": limit,
            # 根据类型添加特定参数
            "volume_multiplier": volume_multiplier
            if selected_scanner == "volume_breakout"
            else None,
            "price_change_min": price_change_min
            if selected_scanner == "volume_breakout"
            else None,
            "bb_period": bb_period if selected_scanner == "bollinger" else None,
            "bb_std": bb_std if selected_scanner == "bollinger" else None,
            "ma_period": ma_period if selected_scanner == "trending" else None,
            "consecutive_count": consecutive_count
            if selected_scanner == "consecutive"
            else None,
            "change_threshold": change_threshold
            if selected_scanner == "multi_changes"
            else None,
        }

        scan_button = st.button("🚀 开始扫描", type="primary", use_container_width=True)

        st.markdown("---")
        st.caption(f"Quant Core: {QUANT_CORE_URL}")

        return scan_button, scan_params

    return None, None


def get_common_symbols() -> list:
    """获取常用品种列表"""
    instruments = load_instruments_config()
    symbols = []
    for inst in instruments:
        symbol = inst.get("symbol", "")
        source = inst.get("source", "")

        if source == "okx":
            if symbol.endswith("-SWAP"):
                symbol = symbol.replace("-SWAP", "")
            if "-" in symbol:
                symbols.append(f"OKX:{symbol}")
        elif source == "ib":
            exchange = inst.get("exchange", "").lower()
            if exchange == "nasdaq":
                symbols.append(f"OKX:{symbol}USDT")
            elif exchange in ["cme", "nymex", "comex"]:
                tv_symbol_map = {
                    "MNQ": "MNQ",
                    "MYM": "MYM",
                    "RB": "RB",
                    "HO": "HO",
                    "MGC": "MGC",
                    "MHG": "MHG",
                }
                tv_symbol = tv_symbol_map.get(symbol, symbol)
                if exchange == "cme":
                    symbols.append(f"{tv_symbol}.cme")
                elif exchange in ["nymex", "nyex"]:
                    symbols.append(f"{tv_symbol}.nyex")
                elif exchange == "comex":
                    symbols.append(f"{tv_symbol}.comex")
    return symbols


def call_market_scan_api(params: dict) -> dict:
    """调用市场扫描 API"""
    headers = {"X-Client-ID": CLIENT_ID}

    # 根据交易所确定 data source
    exchanges = params.get("exchanges", [])
    if exchanges:
        if "okx" in exchanges:
            source = "okx"
        elif "sse" in exchanges or "szse" in exchanges:
            source = "tdxquant"
        else:
            source = "okx"
    else:
        source = "okx"

    # 如果选择常用品种，获取品种列表
    if params.get("use_common"):
        symbols = get_common_symbols()
        params["symbols"] = symbols

    # 清理 None 值和 use_common
    params = {k: v for k, v in params.items() if v is not None and k != "use_common"}

    try:
        response = requests.post(
            f"{QUANT_CORE_URL}/api/scan/market?source={source}",
            json=params,
            headers=headers,
            timeout=120,
            proxies={"http": None, "https": None},
        )
        result = response.json()
        result["http_status"] = response.status_code
        return result
    except Exception as e:
        return {"error": str(e), "results": [], "http_status": None}


def render_results(results: list):
    """渲染市场扫描结果"""
    if not results:
        st.warning("未发现符合条件的标的")
        return

    df = pd.DataFrame(
        [
            {
                "品种": r.get("symbol", ""),
                "交易所": r.get("exchange", ""),
                "方向": "🟢 做多" if r.get("breakout_type") == "bullish" else "🔴 做空",
                "signal_strength": r.get("signal_strength", 0),
                "volume_ratio": r.get("volume_ratio", 0),
                "change_percent": f"{r.get('change_percent', 0):.2f}%",
                "m30_trend": r.get("m30_trend", "-"),
                "m5_pullback": "✓" if r.get("m5_pullback") else "-",
                "m1_entry": r.get("m1_entry", "-"),
                "入场价": f"{r.get('entry_price', 0):.4f}"
                if r.get("entry_price")
                else "-",
                "止损": f"{r.get('stop_loss', 0):.4f}" if r.get("stop_loss") else "-",
                "盈亏比": f"{r.get('risk_reward_ratio', 0):.2f}"
                if r.get("risk_reward_ratio")
                else "-",
                "信号原因": r.get("signal_reason", "-"),
                "最终建议": r.get("final_recommendation", "-"),
            }
            for r in results
        ]
    )

    if "signal_strength" in df.columns:
        df = df.sort_values("signal_strength", ascending=False)

    st.subheader(f"发现 {len(df)} 个机会")

    col_config = {
        "品种": st.column_config.TextColumn("品种", width="medium"),
        "方向": st.column_config.TextColumn("方向", width="small"),
        "signal_strength": st.column_config.NumberColumn(
            "强度", format="%d", width="small"
        ),
        "volume_ratio": st.column_config.NumberColumn(
            "放量", format="%.1fx", width="small"
        ),
        "change_percent": st.column_config.TextColumn("涨跌", width="small"),
        "m30_trend": st.column_config.TextColumn("M30趋势", width="small"),
        "m5_pullback": st.column_config.TextColumn("回调", width="small"),
        "m1_entry": st.column_config.TextColumn("M1信号", width="small"),
        "入场价": st.column_config.TextColumn("入场", width="small"),
        "止损": st.column_config.TextColumn("止损", width="small"),
        "盈亏比": st.column_config.TextColumn("盈亏比", width="small"),
        "最终建议": st.column_config.TextColumn("建议", width="small"),
    }

    st.dataframe(
        df, column_config=col_config, hide_index=True, use_container_width=True
    )


def main():
    scan_button, scan_params = render_sidebar()

    has_scanner = scan_params and len(scan_params.get("scanners", [])) > 0
    has_exchanges = scan_params and len(scan_params.get("exchanges", [])) > 0
    use_common = scan_params and scan_params.get("use_common", False)

    # 需要选择市场或常用品种
    if not has_exchanges and not use_common:
        st.info("👈 请在侧边栏选择市场或勾选「常用品种」，然后点击「开始扫描」")
        return

    if not scan_button or not scan_params:
        return

    with st.spinner("正在扫描市场..."):
        start_time = time.time()
        result = call_market_scan_api(scan_params)
        elapsed = time.time() - start_time

    if result.get("error"):
        st.error(f"请求失败: {result['error']}")
        return

    results = result.get("results", [])

    col1, col2 = st.columns(2)
    col1.metric("发现机会", len(results))
    col2.metric("耗时", f"{elapsed:.2f}秒")

    st.markdown("---")

    if results:
        render_results(results)
    else:
        st.info("未发现符合条件的标的，尝试调整扫描参数")


if __name__ == "__main__":
    main()
