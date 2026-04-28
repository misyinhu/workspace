"""Reusable UI components for Kanban."""

import streamlit as st
import yaml
from pathlib import Path


EXCHANGE_OPTIONS = {
    "okx": "OKX",
    "sse": "SSE",
    "szse": "SZSE",
    "nasdaq": "NASDAQ",
    "nyse": "NYSE",
    "hkex": "HKEX",
}


def load_all_symbols() -> dict:
    """从 quant_core/data/symbols/ 加载所有品种"""
    import sys
    quant_path = "/Users/wang/.opencode/workspace/quant"
    if quant_path not in sys.path:
        sys.path.insert(0, quant_path)
    
    try:
        from quant_core.data import load_symbols
        
        all_symbols = {}
        for exchange_id in EXCHANGE_OPTIONS.keys():
            symbols = load_symbols(exchange_id)
            if symbols:
                formatted = []
                for s in symbols:
                    if s.startswith("OKX:"):
                        s = s.replace("OKX:", "")
                    if s.startswith("NASDAQ:") or s.startswith("NYSE:"):
                        s = s.replace("NASDAQ:", "").replace("NYSE:", "")
                    if s.endswith("-SWAP"):
                        s = s.replace("-SWAP", "")
                    formatted.append(s)
                all_symbols[exchange_id] = list(set(formatted))[:50]
        return all_symbols
    except Exception:
        return {}


def add_to_instruments(symbol: str, exchange: str, name: str = "") -> bool:
    """添加品种到 instruments.yaml"""
    instruments_path = Path(__file__).parent.parent / "instruments.yaml"
    
    try:
        with open(instruments_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        instruments = data.get("instruments", [])
        
        for inst in instruments:
            if inst.get("symbol") == symbol:
                return False
        
        source_map = {
            "okx": "okx",
            "sse": "tdxquant",
            "szse": "tdxquant",
            "nasdaq": "ib",
            "nyse": "ib",
            "hkex": "ib",
        }
        
        instruments.append({
            "symbol": symbol,
            "name": name or symbol,
            "exchange": exchange.upper(),
            "source": source_map.get(exchange, "okx"),
        })
        
        data["instruments"] = instruments
        
        with open(instruments_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        
        return True
    except Exception:
        return False


def render_inline_symbol_search():
    """渲染品种搜索控件 - 点击按钮后展开品种列表"""
    
    # 初始化状态
    if "show_symbol_search" not in st.session_state:
        st.session_state.show_symbol_search = False
    
    # 正常状态：只显示一个添加按钮
    if not st.session_state.show_symbol_search:
        if st.button("➕ 添加品种", key="toggle_symbol_search"):
            st.session_state.show_symbol_search = True
            st.rerun()
        return
    
    # 点击后展开：显示交易所选择和品种列表
    col1, col2 = st.columns([1, 5])
    
    with col1:
        if st.button("关闭", key="close_symbol_search"):
            st.session_state.show_symbol_search = False
            st.rerun()
    
    with col2:
        exchange = st.selectbox(
            "选择交易所",
            options=list(EXCHANGE_OPTIONS.keys()),
            format_func=lambda x: EXCHANGE_OPTIONS[x],
            key="symbol_exchange_list",
        )
    
    # 加载并显示品种列表
    all_symbols = load_all_symbols()
    symbols = all_symbols.get(exchange, [])
    
    if symbols:
        # 分列显示品种（每行4个按钮）
        st.write(f"**{EXCHANGE_OPTIONS[exchange]} 品种清单：**")
        cols = st.columns(4)
        for i, sym in enumerate(symbols):
            with cols[i % 4]:
                if st.button(f"{sym}", key=f"add_{exchange}_{sym}", use_container_width=True):
                    if add_to_instruments(sym, exchange):
                        st.success(f"已添加 {sym}")
                    else:
                        st.info(f"{sym} 已在常用品种中")
    else:
        st.info("暂无可用品种")
