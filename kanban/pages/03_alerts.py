"""Alert Center - TradingView 指标监控."""

import streamlit as st
from src.tv import get_all_tv_indicators


def render_alert_center():
    st.markdown("### 🚨 警报中心")
    st.caption("遍历所有 TradingView 布局实时监控指标")
    tv_data = get_all_tv_indicators()
    if not tv_data:
        st.warning("⚠️ 无法连接到 TradingView，请确保 CDP 已开启 (127.0.0.1:9222)")
        return
    tabs = tv_data.get("tabs", [])
    if not tabs:
        st.warning("⚠️ 未扫描到任何图表，请在 TradingView 中打开布局")
        return
    st.markdown(f"#### 📊 已扫描 {tv_data.get('tab_count', len(tabs))} 个布局")
    with st.expander("查看扫描的布局"):
        for t in tabs:
            st.write(f"- **{t['symbol']}** ({t.get('description', 'Unnamed')})")
    all_alerts = []
    for tab_info in tabs:
        symbol = tab_info.get("symbol", "N/A")
        tab_idx = tab_info.get("tab_index", 0)
        for study in tab_info.get("studies", []):
            study_name = study.get("name", "")
            if study_name == "Overlay":
                continue
            values = study.get("values", {})
            # Z-Score 检查
            if "Z-Score" in values:
                try:
                    zscore = float(
                        values["Z-Score"].replace("−", "-").replace("−", "-")
                    )
                    if abs(zscore) >= 3:
                        all_alerts.append(
                            {
                                "level": "🔴" if abs(zscore) >= 4 else "🟡",
                                "tab": f"Tab {tab_idx} ({symbol})",
                                "indicator": study_name,
                                "metric": "Z-Score",
                                "value": zscore,
                                "message": f"Z-Score 达到 {zscore:.2f}",
                            }
                        )
                except:
                    pass
            # 相关性检查
            if "短期相关性" in values:
                try:
                    corr = float(values["短期相关性"].replace("−", "-"))
                    if corr < 0.5:
                        all_alerts.append(
                            {
                                "level": "🟡",
                                "tab": f"Tab {tab_idx} ({symbol})",
                                "indicator": study_name,
                                "metric": "短期相关性",
                                "value": corr,
                                "message": f"相关性降至 {corr:.2f}",
                            }
                        )
                except:
                    pass
    # 显示指标
    for tab_info in tabs:
        symbol = tab_info.get("symbol", "N/A")
        tab_idx = tab_info.get("tab_index", 0)
        quote = tab_info.get("quote", {})
        with st.expander(f"📑 Tab {tab_idx} - {symbol}"):
            if quote and quote.get("close"):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("最新价", f"{quote.get('close', 0):.2f}")
                c2.metric("开盘", f"{quote.get('open', 'N/A')}")
                c3.metric("最高", f"{quote.get('high', 'N/A')}")
                c4.metric("最低", f"{quote.get('low', 'N/A')}")
            st.markdown("**指标:**")
            for study in tab_info.get("studies", []):
                name = study.get("name", "")
                vals = study.get("values", {})
                if name != "Overlay" and vals:
                    st.markdown(f"📈 **{name}**")
                    cols = st.columns(len(vals))
                    for i, (k, v) in enumerate(vals.items()):
                        cols[i].metric(k, v)
    # 警报显示
    st.markdown("---")
    st.markdown("#### 🔔 活跃警报")
    if all_alerts:
        for alert in all_alerts:
            st.error(f"**{alert['level']}** | {alert['tab']} | {alert['message']}")
    else:
        st.success("✅ 所有 Tab 指标正常，无警报")
    if st.button("🔄 立即刷新"):
        st.rerun()


if __name__ == "__main__":
    render_alert_center()
