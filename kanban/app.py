"""Kanban - Multi-page Streamlit App Controller.

Re-exports functions from src modules for easy importing by pages and tests.
"""

import streamlit as st

# Re-export from src modules
from src.data import (
    fetch_multi_timeframe,
    fetch_from_history,
    load_instruments_config,
    get_source_for_symbol,
    get_tv_symbol_for_ib,
)
from src.analysis import (
    calculate_resonance_en,
    detect_contradictions,
    calculate_rsi_local,
    calculate_ma_local,
    calculate_trend,
)

# Streamlit page config
st.set_page_config(
    page_title="Kanban",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Navigation in sidebar
st.sidebar.title("📊 Kanban")
st.sidebar.markdown("---")
st.sidebar.markdown("**页面导航:**")
st.sidebar.page_link("pages/0_news_center.py", label="📰 新闻事件中心")
st.sidebar.page_link("pages/1_alerts.py", label="🚨 警报中心")
st.sidebar.page_link("pages/2_market_scan.py", label="🔍 市场扫描")
st.sidebar.page_link("pages/3_three_screen.py", label="🔱 三重滤网")
st.sidebar.page_link("pages/4_resonance.py", label="📈 多周期共振")
st.sidebar.page_link("pages/5_cross_timeframe.py", label="🔄 跨周期分析")
st.sidebar.markdown("---")
st.sidebar.caption("Kanban v1.0")

# Default to resonance page
st.switch_page("pages/4_resonance.py")
