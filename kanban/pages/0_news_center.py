"""新闻事件中心 - 已禁用"""

import streamlit as st

st.markdown("### 📰 新闻事件中心")
st.info("🔧 此页面暂时禁用 due to tradingview_mcp import error")
st.caption("功能维护中，请稍后再试。")

# 预留未来功能
with st.expander("ℹ️ 功能说明"):
    st.write("""
    新闻事件中心将提供：
    - 实时财经新闻
    - 市场情绪分析
    - 社区热点追踪
    """)
