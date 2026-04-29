"""跨周期分析 - 多周期信号矩阵"""

import streamlit as st
import pandas as pd
from src.tv import get_all_tv_indicators


def extract_indicator_values(studies):
    result = {}
    for study in studies:
        name = study.get("name", "")
        if name == "Overlay":
            continue
        values = study.get("values", {})
        for k, v in values.items():
            result[k] = v
    return result


def parse_float(val, default=None):
    if val is None:
        return default
    try:
        return float(str(val).replace("−", "-").replace("−", "-"))
    except:
        return default


def evaluate_signal(symbol, tf_data_map):
    zscore_values = []
    corr_values = []

    for tf, data in tf_data_map.items():
        indicators = data.get("indicators", {})
        zscore = parse_float(indicators.get("Z-Score"))
        corr = parse_float(indicators.get("长期相关性"))

        if zscore is not None:
            zscore_values.append((tf, zscore))
        if corr is not None:
            corr_values.append((tf, corr))

    signal_score = 0
    reasons = []

    avg_corr = (
        sum(c for _, c in corr_values) / len(corr_values) if corr_values else None
    )
    has_corr_break = all(c < 0.3 for _, c in corr_values) if corr_values else False
    has_corr_red = all(c < -0.5 for _, c in corr_values) if corr_values else False

    zscore_red = all(abs(z) >= 3 for _, z in zscore_values) if zscore_values else False
    avg_zscore = None

    if zscore_values:
        avg_zscore = sum(z for _, z in zscore_values) / len(zscore_values)
        all_extreme = all(abs(z) >= 2 for _, z in zscore_values)
        all_same_sign = all(
            (z > 0) == (zscore_values[0][1] > 0) for _, z in zscore_values
        )

        if all_extreme and all_same_sign and has_corr_break:
            signal_score += 2
            reasons.append(
                f"多周期Z-Score共振({avg_zscore:.2f}) + 相关性破裂({avg_corr:.2f})"
            )
        elif all_extreme and all_same_sign and not has_corr_break:
            signal_score = 0
            reasons.append(f"Z-Score共振但无相关性破裂，信号无效")
        elif abs(avg_zscore) >= 2 and has_corr_break:
            signal_score += 1
            reasons.append(f"Z-Score偏离({avg_zscore:.2f}) + 相关性破裂")
        elif has_corr_break:
            signal_score += 1
            reasons.append(f"相关性破裂({avg_corr:.2f})")

    if signal_score >= 2 and zscore_red and has_corr_red:
        action = "🔥 强烈入场"
    elif signal_score >= 2:
        action = "🟢 买入" if (avg_zscore is not None and avg_zscore < 0) else "🔴 卖出"
    elif signal_score == 1:
        action = "🟡 关注"
    else:
        action = "⚪ 中性"

    return {
        "action": action,
        "score": signal_score,
        "reasons": reasons,
        "zscore": zscore_values,
        "corr": corr_values,
    }


def render_cross_timeframe():
    st.markdown("### 📊 跨周期分析")
    st.caption("自动获取 H1 / M15 / M3 指标，评估多周期共振信号")

    legend_markdown = """
    **🎯 评分标准**
    | 评分 | 条件 | 信号 |
    |:---:|------|------|
    | **+2** | Z全部同向(≥2) + 相关性破裂(<0.3) | 🟢买入/🔴卖出 |
    | **+1** | Z偏离(≥2) + 相关性破裂 | 🟡关注 |
    | **+1** | 相关性破裂但Z未极端 | 🟡关注 |
    | **0** | Z共振但无相关性破裂 | ⚪无效 |

    **🔥 强烈入场**: 评分≥2 + Z全部≥3 + 相关性全部<-0.5  
    **关键**: 相关性破裂(<0.3)是买入卖出信号的必要条件

    **🎨 单元格颜色**
    | Z-Score | 颜色 | 相关性 | 颜色 |
    |:---:|:---:|------|:---:|
    | &#124;Z&#124; ≥ 3 | 🔴红底白字 | corr < -0.5 | 🔴红底白字 |
    | &#124;Z&#124; ≥ 2 | 🟡黄底黑字 | corr < 0 | 🟡黄底黑字 |
    评分≥2的行：淡红背景高亮
    """

    st.markdown("#### 📋 图例说明")
    st.markdown(legend_markdown)

    if st.button("🔄 开始跨周期扫描", type="primary"):
        st.rerun()

    with st.spinner("正在获取 H1 数据..."):
        data_h1 = get_all_tv_indicators(timeframe="1h")
    with st.spinner("正在获取 M15 数据..."):
        data_m15 = get_all_tv_indicators(timeframe="15m")
    with st.spinner("正在获取 M3 数据..."):
        data_m3 = get_all_tv_indicators(timeframe="3m")

    if not data_h1 or not data_m15 or not data_m3:
        st.error("❌ 无法获取数据，请检查 TradingView CDP 连接")
        return

    tabs_h1 = data_h1.get("tabs", [])
    tabs_m15 = data_m15.get("tabs", [])
    tabs_m3 = data_m3.get("tabs", [])

    symbol_map = {}
    for tabs, tf in [(tabs_h1, "1h"), (tabs_m15, "15m"), (tabs_m3, "3m")]:
        for tab in tabs:
            symbol = tab.get("symbol", "N/A")
            if symbol not in symbol_map:
                symbol_map[symbol] = {
                    "description": tab.get("description", ""),
                    "exchange": tab.get("exchange", ""),
                }
            symbol_map[symbol][tf] = {
                "quote": tab.get("quote", {}),
                "indicators": extract_indicator_values(tab.get("studies", [])),
            }

    if not symbol_map:
        st.warning("⚠️ 未扫描到任何图表")
        return
    st.markdown("---")

    st.markdown(f"#### 📈 多周期信号矩阵 ({len(symbol_map)} 个品种)")

    rows = []
    for symbol, data in symbol_map.items():
        h1_ind = data.get("1h", {}).get("indicators", {})
        h1_quote = data.get("1h", {}).get("quote", {})
        m15_ind = data.get("15m", {}).get("indicators", {})
        m15_quote = data.get("15m", {}).get("quote", {})
        m3_ind = data.get("3m", {}).get("indicators", {})
        m3_quote = data.get("3m", {}).get("quote", {})

        price = h1_quote.get("close") or m15_quote.get("close") or m3_quote.get("close")

        tf_data = {
            "1h": {"indicators": h1_ind},
            "15m": {"indicators": m15_ind},
            "3m": {"indicators": m3_ind},
        }
        signal = evaluate_signal(symbol, tf_data)

        rows.append(
            {
                "品种": symbol,
                "价格": f"{price:.4f}" if price else "N/A",
                "H1 Z": h1_ind.get("Z-Score"),
                "H1相关": h1_ind.get("长期相关性"),
                "M15 Z": m15_ind.get("Z-Score"),
                "M15相关": m15_ind.get("长期相关性"),
                "M3 Z": m3_ind.get("Z-Score"),
                "M3相关": m3_ind.get("长期相关性"),
                "信号": signal["action"],
                "评分": signal["score"],
                "依据": "; ".join(signal["reasons"])
                if signal["reasons"]
                else "无明显信号",
            }
        )

    df = pd.DataFrame(rows)

    def parse_formatted(val):
        if val is None:
            return None
        try:
            s = str(val).strip().replace("−", "-").replace("−", "-")
            digits = ""
            for i, c in enumerate(s):
                if c in "0123456789.-":
                    digits += c
                elif digits:
                    break
            return float(digits) if digits else None
        except:
            return None

    def style_zscore_raw(val):
        z = parse_formatted(val)
        if z is None:
            return ""
        if abs(z) >= 3:
            return "background-color: #ff4444; color: white; font-weight: bold"
        elif abs(z) >= 2:
            return "background-color: #ffeb3b; color: black; font-weight: bold"
        return ""

    def style_corr_raw(val):
        c = parse_formatted(val)
        if c is None:
            return ""
        if c < -0.5:
            return "background-color: #ff4444; color: white; font-weight: bold"
        elif c < 0:
            return "background-color: #ffeb3b; color: black"
        return ""

    # 格式化函数（应用于显示）
    def format_zscore(val):
        z = parse_float(val)
        if z is None:
            return "N/A"
        label = ""
        if abs(z) >= 3:
            label = "超买" if z > 0 else "超卖"
        elif abs(z) >= 2:
            label = "超买" if z > 0 else "超卖"
        if label:
            return f"{z:.2f} {label}"
        return f"{z:.2f}"

    def format_corr(val):
        c = parse_float(val)
        if c is None:
            return "N/A"
        return f"{c:.2f}"

    df_display = df.copy()
    for col in ["H1 Z", "M15 Z", "M3 Z"]:
        df_display[col] = df_display[col].apply(format_zscore)
    for col in ["H1相关", "M15相关", "M3相关"]:
        df_display[col] = df_display[col].apply(format_corr)

    display_cols = [
        "品种",
        "价格",
        "H1 Z",
        "H1相关",
        "M15 Z",
        "M15相关",
        "M3 Z",
        "M3相关",
        "信号",
        "评分",
        "依据",
    ]

    display_df = df_display[display_cols].copy()

    zscore_cols = ["H1 Z", "M15 Z", "M3 Z"]
    corr_cols = ["H1相关", "M15相关", "M3相关"]

    def style_cell(row):
        row_idx = row.name
        score = df.iloc[row_idx]["评分"]
        is_high_score = score >= 2
        styles = ["" for _ in row]
        for col in zscore_cols:
            val = df.iloc[row_idx][col]
            styles[display_cols.index(col)] = style_zscore_raw(val)
        for col in corr_cols:
            val = df.iloc[row_idx][col]
            styles[display_cols.index(col)] = style_corr_raw(val)
        if is_high_score:
            for i in range(len(row)):
                if not styles[i]:
                    styles[i] = "background-color: #ffe0e0"
                elif "background-color" not in styles[i]:
                    styles[i] += "; background-color: #ffe0e0"
        return styles

    styled = display_df.style.apply(style_cell, axis=1)

    st.dataframe(styled, use_container_width=True, hide_index=True)

    st.markdown("---")

    if st.button("🔄 重新扫描"):
        st.rerun()


if __name__ == "__main__":
    render_cross_timeframe()
