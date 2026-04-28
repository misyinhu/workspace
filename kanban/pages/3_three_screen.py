"""Three Screen Scan Page - 三重滤网扫描"""

import streamlit as st
import pandas as pd
import requests
import time

from src.config import QUANT_CORE_URL, CLIENT_ID
from src.data import load_instruments_config

st.set_page_config(page_title="三重滤网", page_icon="🔱", layout="wide")

# 交易所选项
EXCHANGES = {
    "okx": "OKX (加密)",
    "sse": "上交所 (A股)",
    "szse": "深交所 (A股)",
}


def render_sidebar():
    with st.sidebar:
        st.title("🔱 三重滤网")

        st.subheader("选择市场")

        # 常用品种选项
        use_common = st.checkbox(
            "⭐ 常用品种", value=True, key="use_common_three_screen"
        )

        # 交易所选项
        selected_exchanges = []
        for key, label in EXCHANGES.items():
            if st.checkbox(label, value=False, key=f"exchange_ts_{key}"):
                selected_exchanges.append(key)

        st.subheader("周期参数")
        bar_size_m30 = st.selectbox(
            "M30周期", ["5m", "15m", "30m", "1h", "4h"], index=2
        )
        bar_size_m5 = st.selectbox("M5周期", ["5m", "15m", "30m"], index=0)
        bar_size_m1 = st.selectbox("M1周期", ["1m", "5m", "15m"], index=0)
        num_bars = st.slider("K线数量", 30, 120, 60, 10)

        scan_params = {
            "use_common": use_common,
            "exchanges": selected_exchanges,
            "bar_size_m30": bar_size_m30,
            "bar_size_m5": bar_size_m5,
            "bar_size_m1": bar_size_m1,
            "num_bars": num_bars,
        }

        scan_button = st.button("🚀 开始扫描", type="primary", use_container_width=True)

        st.markdown("---")
        st.caption(f"Quant Core: {QUANT_CORE_URL}")

        return scan_button, scan_params

    return None, None


def get_symbols_for_scan(use_common: bool, exchanges: list) -> list:
    """获取扫描品种列表"""
    symbols = []

    # 常用品种
    if use_common:
        instruments = load_instruments_config()
        for inst in instruments:
            symbol = inst.get("symbol", "")
            source = inst.get("source", "")
            exchange = inst.get("exchange", "").lower()

            # 转换 symbol 格式以匹配 OKX API
            if source == "okx":
                # OKX 格式: BTC-USDT-SWAP -> BTC-USDT
                if symbol.endswith("-SWAP"):
                    symbol = symbol.replace("-SWAP", "")
                # 如果已经是 BTC-USDT 格式，直接用
                if "-" in symbol:
                    symbols.append(symbol)
            elif source == "ib":
                # IB 品种需要转换格式
                if exchange == "nasdaq":
                    symbols.append(f"OKX:{symbol}USDT")
                elif exchange in ["cme", "nymex", "comex"]:
                    # 期货品种
                    tv_symbol = {
                        "MNQ": "MNQ",
                        "MYM": "MYM",
                        "RB": "RB",
                        "HO": "HO",
                        "MGC": "MGC",
                        "MHG": "MHG",
                    }.get(symbol, symbol)
                    # TradingView 格式
                    if exchange == "cme":
                        symbols.append(f"{tv_symbol}.cme")
                    elif exchange in ["nymex", "nyex"]:
                        symbols.append(f"{tv_symbol}.nyex")
                    elif exchange == "comex":
                        symbols.append(f"{tv_symbol}.comex")

    # 交易所品种 - 后端 load_symbols 加载，这里不硬编码
    for exchange in exchanges:
        pass  # 后端从 exchanges 加载完整列表

    return symbols


def call_three_screen_api(
    exchanges: list,
    bar_size_m30: str,
    bar_size_m5: str,
    bar_size_m1: str,
    num_bars: int,
) -> dict:
    headers = {"X-Client-ID": CLIENT_ID}

    # 根据交易所确定 data source
    if "okx" in exchanges:
        source = "okx"
    elif "sse" in exchanges or "szse" in exchanges:
        source = "tdxquant"
    else:
        source = "tdxquant"

    payload = {
        "symbols": [],
        "exchanges": exchanges,
        "bar_size_m30": bar_size_m30,
        "bar_size_m5": bar_size_m5,
        "bar_size_m1": bar_size_m1,
        "num_m30": num_bars,
        "num_m5": num_bars,
        "num_m1": num_bars,
    }

    try:
        response = requests.post(
            f"{QUANT_CORE_URL}/api/scan/three-screen?source={source}",
            json=payload,
            headers=headers,
            timeout=30,
            proxies={"http": None, "https": None},
        )
        submit_result = response.json()

        if "task_id" not in submit_result:
            return {
                "error": "提交失败: " + str(submit_result),
                "http_status": response.status_code,
            }

        task_id = submit_result["task_id"]

        progress_bar = st.progress(0)
        status_text = st.empty()
        elapsed = 0

        for _ in range(60):
            time.sleep(3)
            elapsed += 3
            try:
                status_response = requests.get(
                    f"{QUANT_CORE_URL}/api/scan/three-screen/{task_id}",
                    headers=headers,
                    timeout=30,
                    proxies={"http": None, "https": None},
                )
                status_result = status_response.json()

                if status_result.get("status") == "done":
                    progress_bar.progress(100)
                    status_text.text("扫描完成！")
                    return status_result
                elif status_result.get("status") == "error":
                    progress_bar.empty()
                    status_text.empty()
                    return {
                        "error": "扫描出错: " + str(status_result.get("message", "")),
                        "http_status": 500,
                    }
                else:
                    progress = min(90, int(elapsed / 180 * 100))
                    progress_bar.progress(progress)
                    status_text.text(f"扫描中... {elapsed}s")
            except Exception as e:
                continue

        progress_bar.empty()
        status_text.empty()
        return {"error": "扫描超时", "http_status": 408}

    except Exception as e:
        return {"error": str(e), "http_status": None}


def render_results(result: dict):
    """渲染三滤网扫描结果"""
    bulls = result.get("bulls_with_pullback", [])
    bears = result.get("bears_with_pullback", [])
    all_results = result.get("all_results", [])

    if not all_results:
        st.warning("未发现符合条件的标的")
        return

    # 多头机会
    if bulls:
        st.subheader(f"🟢 做多机会 ({len(bulls)} 个)")

        bull_df = pd.DataFrame(
            [
                {
                    "品种": r.get("symbol", ""),
                    "趋势": r.get("trend", "-"),
                    "回调": "✓" if r.get("pullback") else "-",
                    "回调原因": r.get("pullback_reason", "-"),
                    "M1信号": r.get("entry", "-"),
                    "强度": r.get("strength", 0),
                    "支撑": f"{r.get('support', 0):.2f}" if r.get("support") else "-",
                    "压力": f"{r.get('resistance', 0):.2f}"
                    if r.get("resistance")
                    else "-",
                    "入场价": f"{r.get('entry_price', 0):.4f}"
                    if r.get("entry_price")
                    else "-",
                    "止损": f"{r.get('stop_loss', 0):.4f}"
                    if r.get("stop_loss")
                    else "-",
                    "盈亏比": f"{r.get('risk_reward', 0):.2f}"
                    if r.get("risk_reward")
                    else "-",
                }
                for r in bulls
            ]
        )
        bull_df = bull_df.sort_values("强度", ascending=False)

        bull_col_config = {
            "品种": st.column_config.TextColumn("品种", width="medium"),
            "趋势": st.column_config.TextColumn("趋势", width="small"),
            "回调": st.column_config.TextColumn("回调", width="small"),
            "回调原因": st.column_config.TextColumn("回调原因", width="large"),
            "M1信号": st.column_config.TextColumn("M1信号", width="small"),
            "强度": st.column_config.NumberColumn("强度", format="%d", width="small"),
            "支撑": st.column_config.TextColumn("支撑", width="small"),
            "压力": st.column_config.TextColumn("压力", width="small"),
            "入场价": st.column_config.TextColumn("入场", width="small"),
            "止损": st.column_config.TextColumn("止损", width="small"),
            "盈亏比": st.column_config.TextColumn("盈亏比", width="small"),
        }
        st.dataframe(
            bull_df,
            column_config=bull_col_config,
            hide_index=True,
            use_container_width=True,
        )

    # 空头机会
    if bears:
        st.subheader(f"🔴 做空机会 ({len(bears)} 个)")

        bear_df = pd.DataFrame(
            [
                {
                    "品种": r.get("symbol", ""),
                    "趋势": r.get("trend", "-"),
                    "回调": "✓" if r.get("pullback") else "-",
                    "回调原因": r.get("pullback_reason", "-"),
                    "M1信号": r.get("entry", "-"),
                    "强度": r.get("strength", 0),
                    "支撑": f"{r.get('support', 0):.2f}" if r.get("support") else "-",
                    "压力": f"{r.get('resistance', 0):.2f}"
                    if r.get("resistance")
                    else "-",
                    "入场价": f"{r.get('entry_price', 0):.4f}"
                    if r.get("entry_price")
                    else "-",
                    "止损": f"{r.get('stop_loss', 0):.4f}"
                    if r.get("stop_loss")
                    else "-",
                    "盈亏比": f"{r.get('risk_reward', 0):.2f}"
                    if r.get("risk_reward")
                    else "-",
                }
                for r in bears
            ]
        )
        bear_df = bear_df.sort_values("强度", ascending=False)

        bear_col_config = {
            "品种": st.column_config.TextColumn("品种", width="medium"),
            "趋势": st.column_config.TextColumn("趋势", width="small"),
            "回调": st.column_config.TextColumn("回调", width="small"),
            "回调原因": st.column_config.TextColumn("回调原因", width="large"),
            "M1信号": st.column_config.TextColumn("M1信号", width="small"),
            "强度": st.column_config.NumberColumn("强度", format="%d", width="small"),
            "支撑": st.column_config.TextColumn("支撑", width="small"),
            "压力": st.column_config.TextColumn("压力", width="small"),
            "入场价": st.column_config.TextColumn("入场", width="small"),
            "止损": st.column_config.TextColumn("止损", width="small"),
            "盈亏比": st.column_config.TextColumn("盈亏比", width="small"),
        }
        st.dataframe(
            bear_df,
            column_config=bear_col_config,
            hide_index=True,
            use_container_width=True,
        )


def main():
    scan_button, scan_params = render_sidebar()

    if not scan_params:
        return

    use_common = scan_params.get("use_common", False)
    exchanges = scan_params.get("exchanges", [])

    # 检查是否有选择
    if not use_common and not exchanges:
        st.info("👈 请勾选「常用品种」或选择交易所")
        return

    if not scan_button:
        return

    st.empty()

    result = call_three_screen_api(
        exchanges=exchanges,
        bar_size_m30=scan_params["bar_size_m30"],
        bar_size_m5=scan_params["bar_size_m5"],
        bar_size_m1=scan_params["bar_size_m1"],
        num_bars=scan_params["num_bars"],
    )

    if result.get("error"):
        st.error(f"请求失败: {result['error']}")
        return

    bulls = result.get("bulls_with_pullback", [])
    bears = result.get("bears_with_pullback", [])

    col1, col2, col3 = st.columns(3)
    col1.metric("扫描总数", result.get("total_scanned", 0))
    col2.metric("做多机会", len(bulls))
    col3.metric("做空机会", len(bears))

    st.markdown("---")
    render_results(result)


if __name__ == "__main__":
    main()
