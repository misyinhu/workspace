"""Multi-timeframe Resonance Analysis Page."""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import streamlit.components.v1 as components
import json

from src.config import (
    TIMEFRAMES,
    TIMEFRAME_LABELS,
    TREND_EMOJI,
    TREND_CN,
    BIAS_CN,
    QUANT_CORE_URL,
)
from src.data import (
    fetch_multi_timeframe,
    get_source_for_symbol,
    load_instruments_config,
)
from src.analysis import calculate_resonance_en, detect_contradictions
from src.three_filter import calculate_three_filter, ThreeFilterSignal
import requests


# Lightweight Charts JS
LW_CHARTS_JS = """
<script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
"""


def render_lightweight_chart(symbol, bars_data, height=400):
    """使用原始 lightweight-charts 渲染图表"""
    if not bars_data or len(bars_data) == 0:
        st.info("图表数据加载中...")
        return

    # 转换数据格式 - 日内数据用完整时间戳，日线及以上用日期
    chart_data = []
    for bar in bars_data:
        ts = bar.get("timestamp", bar.get("time"))
        if isinstance(ts, str):
            if "T" in ts:
                # 已经是 ISO 格式，保留完整格式用于日内
                time_str = ts.replace("Z", "")[:19]
            else:
                time_str = ts[:10]
        else:
            dt = pd.to_datetime(ts, unit="ms")
            time_str = dt.strftime("%Y-%m-%dT%H:%M:%S")

        chart_data.append(
            {
                "time": time_str,
                "open": float(bar.get("open", 0)),
                "high": float(bar.get("high", 0)),
                "low": float(bar.get("low", 0)),
                "close": float(bar.get("close", 0)),
            }
        )

    # 计算MA20
    closes = [d["close"] for d in chart_data]
    ma20_data = []
    for i in range(19, len(closes)):
        avg = sum(closes[i - 19 : i + 1]) / 20
        ma20_data.append({"time": chart_data[i]["time"], "value": round(avg, 4)})

    chart_config = {
        "layout": {
            "background": {"type": "solid", "color": "#ffffff"},
            "textColor": "#333",
        },
        "grid": {
            "vertLines": {"color": "#e0e0e0"},
            "horzLines": {"color": "#e0e0e0"},
        },
        "crosshair": {
            "mode": 1,
            "vertLine": {
                "width": 1,
                "color": "#999999",
                "style": 2,
                "labelBackgroundColor": "#999999",
            },
            "horzLine": {
                "width": 1,
                "color": "#999999",
                "style": 2,
                "labelBackgroundColor": "#999999",
            },
        },
        "time_scale": {"timeVisible": True, "secondsVisible": False},
        "right_price_scale": {"borderColor": "#cccccc"},
        "height": height,
    }

    html = f"""
        {LW_CHARTS_JS}
        <div id="chart_{symbol}" style="height: {height}px; width: 100%;"></div>
        <script>
        (function() {{
            const container = document.getElementById('chart_{symbol}');
            const chart = LightweightCharts.createChart(container, {json.dumps(chart_config)});
            
            const candleSeries = chart.addCandlestickSeries({{
                upColor: '#26a69a',
                downColor: '#ef5350',
                borderUpColor: '#26a69a',
                borderDownColor: '#ef5350',
                wickUpColor: '#26a69a',
                wickDownColor: '#ef5350',
            }});
            candleSeries.setData({json.dumps(chart_data)});
            
            const lineSeries = chart.addLineSeries({{
                color: '#FF9800',
                lineWidth: 2,
            }});
            lineSeries.setData({json.dumps(ma20_data)});
            
            // 显示所有数据
            chart.timeScale().fitContent();
            
            window.addEventListener('resize', () => {{
                chart.applyOptions({{width: container.clientWidth}});
            }});
        }})();
        </script>
    """
    components.html(html, height=height + 20, scrolling=False)


def render_sidebar():
    """渲染侧边栏 - 完整版"""

    # 常用品种
    st.sidebar.subheader("选择分析品种")
    instruments = load_instruments_config()
    if instruments:
        options = [f"{i['symbol']} - {i['name']}" for i in instruments]
        selected = st.sidebar.selectbox(
            "常用品种", options, index=0, key="instrument_select"
        )
        symbol = selected.split(" - ")[0]
    else:
        symbol = "DOGE-USDT-SWAP"

    # 自定义输入
    custom = st.sidebar.text_input(
        "输入品种代码",
        placeholder="如: TSLA, AAPL, DOGEUSDT...",
        key="custom_symbol_input",
    )
    if custom:
        symbol = custom.strip().upper()
        # HK stocks and custom symbols use IB source
        source = "ib"
    else:
        source = get_source_for_symbol(symbol)

    # 跨品种套利
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔗 跨品种套利")
    enable_spread = st.sidebar.toggle(
        "启用双品种模式", value=False, key="enable_spread"
    )

    symbol2 = ""
    source2 = "ib"

    if enable_spread:
        # 品种2选择器
        if instruments:
            options2 = [f"{i['symbol']} - {i['name']}" for i in instruments]
            selected2 = st.sidebar.selectbox(
                "品种 2",
                options2,
                index=1 if len(options2) > 1 else 0,
                key="instrument_select2",
            )
            symbol2 = selected2.split(" - ")[0]
        else:
            symbol2 = st.sidebar.text_input(
                "品种 2 代码", placeholder="如: ETH-USDT-SWAP", key="symbol2_input"
            )

        if symbol2:
            source2 = "ib"

    # 设置
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ 设置")

    auto_refresh = st.sidebar.toggle("自动刷新", value=False, key="auto_refresh")
    refresh_interval = 10
    if auto_refresh:
        refresh_interval = st.sidebar.slider(
            "刷新间隔(秒)", 5, 60, 10, key="refresh_interval"
        )

    return (
        symbol,
        symbol2,
        enable_spread,
        source,
        source2,
        auto_refresh,
        refresh_interval,
    )


def render_timeframe_cards(timeframe_data: dict):
    """渲染时间周期卡片 - 精简版"""
    if not timeframe_data:
        st.warning("暂无数据，请选择品种")
        return

    # 使用 5 列布局
    cols = st.columns(len(TIMEFRAMES))
    for i, tf in enumerate(TIMEFRAMES):
        with cols[i]:
            data = timeframe_data.get(tf, {})
            trend = data.get("trend", "neutral")
            emoji = TREND_EMOJI.get(trend, "➡️")
            close = data.get("close", 0)
            rsi = data.get("rsi", 0)
            bias = data.get("bias", "NEUTRAL")
            bias_cn = BIAS_CN.get(bias, "中性")
            ema20 = data.get("ema20", 0)
            change_pct = data.get("change_pct", 0)

            # 卡片容器 - 精简布局
            with st.container(border=True):
                # 周期名 + 方向
                st.markdown(f"**{TIMEFRAME_LABELS.get(tf, tf)} {emoji}**")

                # 偏多/偏空/中性 + 涨跌幅
                bias_color = (
                    "#26a69a"
                    if "上涨" in bias_cn
                    else "#ef5350"
                    if "下跌" in bias_cn
                    else "#888"
                )
                change_color = (
                    "#26a69a"
                    if change_pct > 0
                    else "#ef5350"
                    if change_pct < 0
                    else "#888"
                )
                st.markdown(
                    f"<span style='color:{bias_color};font-size:13px'>{bias_cn}</span> <span style='color:{change_color};font-size:12px'>{change_pct:+.2f}%</span>",
                    unsafe_allow_html=True,
                )

                # RSI + EMA20 位置
                if rsi > 0 and ema20 > 0:
                    # 判断价格与 EMA20 的关系
                    if close > ema20:
                        ma_status = "↑"
                    elif close < ema20:
                        ma_status = "↓"
                    else:
                        ma_status = "-"
                    st.caption(f"RSI {rsi:.0f} | MA20{ma_status}")


def render_three_filter_signal(signal: ThreeFilterSignal, symbol: str):
    """渲染三滤网入场信号"""
    if not signal:
        st.info("三滤网信号：数据不足")
        return

    with st.container(border=True):
        st.markdown("### 🎯 三滤网入场信号")

        # 三滤网状态 - 横向排列
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            # Filter 1: M30 趋势
            trend_color = (
                "#26a69a"
                if "多头" in signal.m30_trend
                else "#ef5350"
                if "空头" in signal.m30_trend
                else "#888"
            )
            st.markdown(f"**M30 趋势**")
            st.markdown(
                f"<span style='color:{trend_color};font-size:14px'>{signal.m30_trend}</span>",
                unsafe_allow_html=True,
            )

        with col2:
            # Filter 2: M5 回调
            pullback_color = "#FFA500" if "回调" in signal.m5_pullback else "#26a69a"
            st.markdown(f"**M5 回调**")
            st.markdown(
                f"<span style='color:{pullback_color};font-size:14px'>{signal.m5_pullback}</span>",
                unsafe_allow_html=True,
            )

        with col3:
            # Filter 3: M1 入场
            entry_color = (
                "#26a69a"
                if "做多" in signal.m1_entry
                else "#ef5350"
                if "做空" in signal.m1_entry
                else "#888"
            )
            st.markdown(f"**M1 入场**")
            st.markdown(
                f"<span style='color:{entry_color};font-size:14px'>{signal.m1_entry}</span>",
                unsafe_allow_html=True,
            )

        with col4:
            # 信号强度
            strength_color = (
                "#26a69a"
                if signal.strength >= 70
                else "#FFA500"
                if signal.strength >= 40
                else "#ef5350"
            )
            st.markdown(f"**信号强度**")
            st.markdown(
                f"<span style='color:{strength_color};font-size:14px'>{signal.strength}</span>",
                unsafe_allow_html=True,
            )
            st.progress(signal.strength / 100)

        # 信号原因
        if signal.signal_reason:
            st.caption(f"信号逻辑：{signal.signal_reason}")

        # 入场价格和止损
        if signal.entry_price and signal.stop_loss:
            col_price, col_sl, col_rr = st.columns(3)
            with col_price:
                st.metric("入场价格", f"{signal.entry_price:.4f}")
            with col_sl:
                st.metric("止损价格", f"{signal.stop_loss:.4f}")
            with col_rr:
                rr = signal.risk_reward_ratio or 0
                rr_color = "green" if rr >= 2 else "orange" if rr >= 1 else "red"
                st.markdown(f"**盈亏比** :{rr_color}[{rr:.2f}]")


def render_contradiction_alert(contradiction_data: dict):
    """渲染矛盾警报 - 完整版"""
    if not contradiction_data.get("has_contradiction"):
        st.info("✅ 各周期趋势一致，无明显矛盾")
        return

    contradictions = contradiction_data.get("contradictions", [])
    divergence_score = contradiction_data.get("divergence_score", 0)

    with st.container(border=True):
        st.markdown("### ⚠️ 周期矛盾警告")

        col1, col2 = st.columns([1, 2])
        with col1:
            risk_text = (
                "高风险"
                if divergence_score > 50
                else "中风险"
                if divergence_score > 25
                else "低风险"
            )
            st.metric("分歧系数", f"{divergence_score}", risk_text)
        with col2:
            st.progress(divergence_score / 100, text=f"分歧程度: {risk_text}")

        st.divider()

        for i, c in enumerate(contradictions, 1):
            c_type = c.get("type", "未知")
            st.warning(f"**{i}. {c_type}**")


def generate_trading_recommendation(
    resonance_data: dict, contradiction_data: dict
) -> dict:
    """生成交易建议"""
    score = resonance_data.get("score", 0)
    level = resonance_data.get("level", "低")
    distribution = resonance_data.get("distribution", {})
    up = distribution.get("up", 0)
    down = distribution.get("down", 0)

    # 根据共振和矛盾生成建议
    if contradiction_data.get("has_contradiction"):
        return {
            "recommendation": "观望",
            "action": None,
            "confidence": "低",
            "reason": "周期矛盾严重，建议等待方向明确",
            "emoji": "➡️",
        }

    if score >= 75:
        if up > down:
            return {
                "recommendation": "强烈买入",
                "action": "BUY",
                "confidence": "高",
                "reason": f"多周期共振向上 ({up}/{up + down})",
                "emoji": "📈",
            }
        else:
            return {
                "recommendation": "强烈卖出",
                "action": "SELL",
                "confidence": "高",
                "reason": f"多周期共振向下 ({down}/{up + down})",
                "emoji": "📉",
            }
    elif score >= 50:
        if up > down:
            return {
                "recommendation": "买入",
                "action": "BUY",
                "confidence": "中",
                "reason": f"趋势上涨 ({up}/{up + down})",
                "emoji": "📈",
            }
        else:
            return {
                "recommendation": "卖出",
                "action": "SELL",
                "confidence": "中",
                "reason": f"趋势下跌 ({down}/{up + down})",
                "emoji": "📉",
            }
    else:
        return {
            "recommendation": "观望",
            "action": None,
            "confidence": "低",
            "reason": "共振较弱，建议观望",
            "emoji": "➡️",
        }


def render_trading_recommendation(rec: dict, symbol: str, source: str):
    """渲染交易建议 - 完整版"""
    if not rec:
        st.info("当前无明确交易信号，建议观望")
        return

    emoji = rec.get("emoji", "➡️")
    rec_text = rec.get("recommendation", "观望")
    action = rec.get("action")
    reason = rec.get("reason", "")
    confidence = rec.get("confidence", "低")

    confidence_color = (
        "green" if confidence == "高" else "orange" if confidence == "中" else "gray"
    )

    with st.container(border=True):
        st.markdown(f"### 💡 交易建议 {emoji}")

        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown(f"**建议方向**: `{rec_text}`")
            st.markdown(f"**置信度**: :{confidence_color}[{confidence}]")
        with col2:
            st.markdown(f"**原因**: {reason}")

        if action:
            st.markdown("---")
            col_btn1, col_btn2 = st.columns([1, 1])
            with col_btn1:
                if st.button(
                    f"📈 买入 {symbol}",
                    key="btn_buy",
                    type="primary",
                    use_container_width=True,
                ):
                    st.success(f"买入 {symbol} 请求已提交")
            with col_btn2:
                if st.button(
                    f"📉 卖出 {symbol}",
                    key="btn_sell",
                    type="secondary",
                    use_container_width=True,
                ):
                    st.success(f"卖出 {symbol} 请求已提交")


def render_resonance_gauge(resonance_data: dict):
    """渲染共振仪表 - 完整版"""
    score = resonance_data.get("score", 0)
    level = resonance_data.get("level", "低")
    distribution = resonance_data.get("distribution", {})

    st.markdown("### 🎯 共振分数")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.progress(score / 100, text=f"{score} 分 ({level}共振)")
    with col2:
        up = distribution.get("up", 0)
        down = distribution.get("down", 0)
        neutral = distribution.get("neutral", 0)
        st.markdown(f"📈 上涨: {up}  📉 下跌: {down}  ➡️ 震荡: {neutral}")


def render_pair_analysis(
    symbol1: str, symbol2: str, source1: str, source2: str, bar: str = "1D"
):
    """渲染双品种套利分析"""
    from src.data import fetch_pair_data
    from src.analysis import (
        calculate_spread,
        calculate_ratio,
        calculate_correlation,
        calculate_zscore,
        generate_arbitrage_signal,
    )

    st.markdown("### 🔗 双品种套利分析")

    # 获取双品种数据
    with st.spinner("加载双品种数据..."):
        pair_data = fetch_pair_data(
            symbol1, symbol2, bar=bar, source1=source1, source2=source2
        )

    bars1 = pair_data.get("bars1", [])
    bars2 = pair_data.get("bars2", [])

    if not bars1 or not bars2:
        st.warning("数据加载中... 请稍后重试")
        return

    # 计算指标
    spread_data = calculate_spread(bars1, bars2)
    ratio_data = calculate_ratio(bars1, bars2)
    correlation = calculate_correlation(bars1, bars2)
    zscore_info = calculate_zscore(spread_data)
    zscore = zscore_info.get("zscore", 0)

    # 获取实时价格计算 RSI (简化版用 close 变化)
    if bars1 and bars2:
        closes1 = [b.get("close", 0) for b in bars1]
        closes2 = [b.get("close", 0) for b in bars2]
        rsi1 = _calculate_rsi_local(closes1) if closes1 else 50
        rsi2 = _calculate_rsi_local(closes2) if closes2 else 50
    else:
        rsi1, rsi2 = 50, 50

    # 生成信号
    signal_info = generate_arbitrage_signal(zscore, correlation, rsi1, rsi2)

    # Tab 视图
    tab_spread, tab_ratio, tab_corr = st.tabs(
        ["📊 价差视图", "📈 比率视图", "🔗 相关性视图"]
    )

    with tab_spread:
        if spread_data and bars1:
            # 从 bars1 获取真实日期
            dates = [
                b.get("timestamp", f"Day {i + 1}")
                for i, b in enumerate(bars1[: len(spread_data)])
            ]
            df_spread = pd.DataFrame(
                {
                    "日期": dates,
                    "价差": spread_data,
                }
            )
            st.line_chart(df_spread.set_index("日期"))
            st.caption(
                f"当前价差: {spread_data[-1]:.4f}" if spread_data else "暂无数据"
            )
        else:
            st.info("暂无价差数据")

    with tab_ratio:
        if ratio_data and bars1:
            dates = [
                b.get("timestamp", f"Day {i + 1}")
                for i, b in enumerate(bars1[: len(ratio_data)])
            ]
            df_ratio = pd.DataFrame(
                {
                    "日期": dates,
                    "比率": ratio_data,
                }
            )
            st.line_chart(df_ratio.set_index("日期"))
            st.caption(f"当前比率: {ratio_data[-1]:.4f}" if ratio_data else "暂无数据")
        else:
            st.info("暂无比率数据")

    with tab_corr:
        st.metric("相关性 (20日)", f"{correlation:.3f}")
        if correlation > 0.8:
            st.success("高相关性，适合套利")
        elif correlation > 0.5:
            st.warning("中等相关性")
        else:
            st.error("低相关性，不建议套利")

    # 信号面板
    st.markdown("### 📋 信号面板")
    col_z, col_corr, col_rsi, col_sig = st.columns(4)
    with col_z:
        st.metric("Z-Score", f"{zscore:.2f}")
    with col_corr:
        st.metric("相关性", f"{correlation:.2f}")
    with col_rsi:
        st.metric("RSI", f"{rsi1:.0f} / {rsi2:.0f}")
    with col_sig:
        sig_color = (
            "green"
            if signal_info["signal"] == "BUY_SPREAD"
            else "red"
            if signal_info["signal"] == "SELL_SPREAD"
            else "gray"
        )
        st.metric("信号", signal_info["signal"], signal_info.get("reason", ""))

    # 底部详情
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            f"品种1 ({symbol1})", f"{bars1[-1].get('close', 0):.4f}" if bars1 else "N/A"
        )
    with col2:
        st.metric(
            f"品种2 ({symbol2})", f"{bars2[-1].get('close', 0):.4f}" if bars2 else "N/A"
        )


def _calculate_rsi_local(prices: list, period: int = 14) -> float:
    """本地计算 RSI"""
    if not prices or len(prices) < period:
        return 50.0
    import numpy as np

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


def render_main_content(
    timeframe_data: dict, resonance_data: dict, symbol: str, source: str
):
    """渲染主内容区域 - 完整版"""
    # 矛盾识别
    contradiction_data = detect_contradictions(timeframe_data)

    # 生成交易建议
    recommendation = generate_trading_recommendation(resonance_data, contradiction_data)

    # 三滤网信号计算
    three_filter_signal = calculate_three_filter(timeframe_data, symbol)

    st.markdown("---")

    # 三滤网入场信号
    render_three_filter_signal(three_filter_signal, symbol)

    st.markdown("---")

    # 周期卡片
    st.markdown("### 📊 各周期趋势")
    render_timeframe_cards(timeframe_data)

    st.markdown("---")

    # 共振分数
    render_resonance_gauge(resonance_data)

    # 交易建议（移至共振分数下方）
    render_trading_recommendation(recommendation, symbol, source)


def main():
    """主函数 - 完整版"""
    st.subheader("📈 多周期共振分析")

    # 侧边栏
    (
        symbol,
        symbol2,
        enable_spread,
        source,
        source2,
        auto_refresh,
        refresh_interval,
    ) = render_sidebar()

    st.markdown("---")

    # 双品种模式
    if enable_spread and symbol2:
        # 周期导航条
        bar_options = ["1m", "5m", "15m", "30m", "1h", "4h", "1D", "1W"]
        selected_bar = st.radio(
            "选择周期",
            bar_options,
            index=bar_options.index("1D"),
            horizontal=True,
            format_func=lambda x: x,
        )
        render_pair_analysis(symbol, symbol2, source, source2, selected_bar)
        return

    # 自动刷新逻辑
    if auto_refresh:
        placeholder = st.empty()
        while auto_refresh:
            with placeholder.container():
                with st.spinner("加载数据中..."):
                    data = fetch_multi_timeframe(symbol, source)
                timeframe_data = data.get("timeframes", {})
                resonance_data = calculate_resonance_en(
                    [v.get("trend", "neutral") for v in timeframe_data.values()]
                )

                if timeframe_data:
                    render_main_content(timeframe_data, resonance_data, symbol, source)
                else:
                    error_msg = data.get("error")
                    if error_msg:
                        st.error(f"数据获取失败: {error_msg}")
                    else:
                        st.error("无法获取数据，请稍后重试")

            time.sleep(refresh_interval)
    else:
        # 单次加载
        with st.spinner("加载数据中..."):
            data = fetch_multi_timeframe(symbol, source)

        timeframe_data = data.get("timeframes", {})

        if not timeframe_data:
            error_msg = data.get("error")
            if error_msg:
                st.error(f"数据获取失败: {error_msg}")
            else:
                st.error("无法获取数据，请稍后重试")
            return

        resonance_data = calculate_resonance_en(
            [v.get("trend", "neutral") for v in timeframe_data.values()]
        )
        render_main_content(timeframe_data, resonance_data, symbol, source)


if __name__ == "__main__":
    main()
