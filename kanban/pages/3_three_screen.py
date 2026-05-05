"""Three Screen Scan Page - 三重滤网扫描"""

import streamlit as st
import pandas as pd
import requests
import time

from src.config import QUANT_CORE_URL, CLIENT_ID
from src.data import get_common_symbols

st.set_page_config(page_title="三重滤网", page_icon="🔱", layout="wide")

# 交易所选项
EXCHANGES = {
    "okx": "OKX (加密)",
    "sse": "上交所 (A股)",
    "szse": "深交所 (A股)",
    "ib": "IB (芝商所/外盘)",
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


def call_three_screen_api(
    use_common: bool,
    exchanges: list,
    bar_size_m30: str,
    bar_size_m5: str,
    bar_size_m1: str,
    num_bars: int,
) -> dict:
    headers = {"X-Client-ID": CLIENT_ID}

    # 获取常用品种
    symbols = get_common_symbols() if use_common else []

    payload = {
        "symbols": symbols,
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
            f"{QUANT_CORE_URL}/api/scan/three-screen",
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


def _create_result_df(results: list, trend_filter: str = None) -> pd.DataFrame:
    """创建结果 DataFrame，统一格式"""
    if not results:
        return pd.DataFrame()

    rows = []
    for r in results:
        if trend_filter and r.get("trend") != trend_filter:
            continue
        rows.append(
            {
                "品种": r.get("symbol", ""),
                "趋势": r.get("trend", "-"),
                "回调": "✓" if r.get("pullback") else "-",
                "回调原因": r.get("pullback_reason", "-") or "-",
                "M1信号": r.get("entry", "-"),
                "强度": r.get("strength", 0),
                "支撑": f"{r.get('support', 0):.2f}" if r.get("support") else "-",
                "压力": f"{r.get('resistance', 0):.2f}" if r.get("resistance") else "-",
                "入场价": f"{r.get('entry_price', 0):.4f}"
                if r.get("entry_price")
                else "-",
                "止损": f"{r.get('stop_loss', 0):.4f}" if r.get("stop_loss") else "-",
                "盈亏比": f"{r.get('risk_reward', 0):.2f}"
                if r.get("risk_reward")
                else "-",
            }
        )
    return pd.DataFrame(rows)


def _render_signal_table(df: pd.DataFrame, title: str):
    """渲染信号表格"""
    if df.empty:
        st.caption(f"暂无 {title}")
        return

    color = "📈" if "做多" in title else "📉" if "做空" in title else "📊"
    st.subheader(f"{color} {title} ({len(df)} 个)")

    col_config = {
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
        df, column_config=col_config, hide_index=True, use_container_width=True
    )


def render_results(result: dict):
    """渲染三滤网扫描结果 - 分类展示有信号和无信号品种"""
    bulls = result.get("bulls_with_pullback", [])
    bears = result.get("bears_with_pullback", [])
    all_results = result.get("all_results", [])

    if not all_results:
        st.warning("未发现符合条件的标的")
        return

    # === 有信号品种 ===
    st.markdown("## 📊 有信号品种")

    bull_df = _create_result_df(all_results, "bull")
    bear_df = _create_result_df(all_results, "bear")

    # 按强度排序
    if not bull_df.empty:
        bull_df = bull_df.sort_values("强度", ascending=False)
    if not bear_df.empty:
        bear_df = bear_df.sort_values("强度", ascending=False)

    col1, col2 = st.columns(2)
    with col1:
        _render_signal_table(bull_df, "做多机会 (M30多头+回调)")
    with col2:
        _render_signal_table(bear_df, "做空机会 (M30空头+回调)")

    # === 无信号品种 ===
    st.markdown("---")
    st.markdown("## 📋 无信号品种 (已扫描但无触发条件)")

    # 获取所有无信号的标的 - 排除 bulls 和 bears
    bull_symbols = {r["symbol"] for r in bulls}
    bear_symbols = {r["symbol"] for r in bears}

    no_signal = [
        r
        for r in all_results
        if r["symbol"] not in bull_symbols and r["symbol"] not in bear_symbols
    ]

    if no_signal:
        no_signal_df = pd.DataFrame(
            [
                {
                    "品种": r.get("symbol", ""),
                    "M30趋势": r.get("trend", "-"),
                    "M5回调": "✓" if r.get("pullback") else "-",
                    "M1信号": r.get("entry", "-"),
                    "强度": r.get("strength", 0),
                    "原因": r.get("pullback_reason", "-") or "-",
                }
                for r in no_signal
            ]
        )
        no_signal_df = no_signal_df.sort_values("M30趋势")

        col_config = {
            "品种": st.column_config.TextColumn("品种", width="small"),
            "M30趋势": st.column_config.TextColumn("M30趋势", width="small"),
            "M5回调": st.column_config.TextColumn("M5回调", width="small"),
            "M1信号": st.column_config.TextColumn("M1信号", width="small"),
            "强度": st.column_config.NumberColumn("强度", format="%d", width="small"),
            "原因": st.column_config.TextColumn("未触发原因", width="large"),
        }
        st.dataframe(
            no_signal_df,
            column_config=col_config,
            hide_index=True,
            use_container_width=True,
        )

        st.caption(f"共 {len(no_signal)} 个品种无信号 (M30趋势不符合或无回调)")
    else:
        st.info("所有扫描品种均有信号触发")


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
        use_common=use_common,
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
