"""完整 Lightweight Charts 演示 - 使用原始 JS"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import json

st.set_page_config(layout="wide")

# 加载 lightweight-charts JS
LW_CHARTS_JS = """
<script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
"""

def render_chart_html(symbol, data, height=400):
    """渲染完整 lightweight chart"""
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
                "labelBackgroundColor": "#999999"
            },
            "horzLine": {
                "width": 1,
                "color": "#999999",
                "style": 2,
                "labelBackgroundColor": "#999999"
            }
        },
        "time_scale": {
            "timeVisible": True,
            "secondsVisible": False,
        },
        "right_price_scale": {
            "borderColor": "#cccccc",
        },
    }
    
    html = f"""
    {LW_CHARTS_JS}
    <div id="chart_{symbol}" style="height: {height}px;"></div>
    <script>
    (function() {{
        const container = document.getElementById('chart_{symbol}');
        const chart = LightweightCharts.createChart(container, {json.dumps(chart_config)});
        
        // 添加K线系列
        const candleSeries = chart.addCandlestickSeries({{
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderUpColor: '#26a69a',
            borderDownColor: '#ef5350',
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
        }});
        
        // 设置数据
        const chartData = {json.dumps(data)};
        candleSeries.setData(chartData);
        
        // 添加MA20线
        const lineSeries = chart.addLineSeries({{
            color: '#FF9800',
            lineWidth: 2,
            priceScaleId: 'right',
        }});
        
        // 计算MA20
        const closes = chartData.map(d => d.close);
        const ma20 = [];
        for (let i = 0; i < closes.length; i++) {{
            if (i >= 19) {{
                const sum = closes.slice(i - 19, i + 1).reduce((a, b) => a + b, 0);
                ma20.push({{
                    time: chartData[i].time,
                    value: sum / 20
                }});
            }}
        }}
        lineSeries.setData(ma20);
        
        // 自适应时间范围
        chart.timeScale().fitContent();
        
        // 监听时间范围变化
        chart.timeScale().subscribeVisibleLogicalRangeChange(range => {{
            console.log('Visible range:', range);
        }});
        
        // 监听十字光标变化获取数据
        chart.subscribeCrosshairMove(param => {{
            if (param.time) {{
                const data = param.seriesData.get(candleSeries);
                if (data) {{
                    // 可以在这里更新streamlit的session state
                    console.log('Crosshair:', data);
                }}
            }}
        }});
        
        // 暴露更新函数
        window.updateChart_{symbol} = function(newData) {{
            candleSeries.update(newData);
        }};
    }})();
    </script>
    """
    return html

# 生成示例数据
@st.cache_data
def generate_data(days=200):
    dates = pd.date_range('2024-01-01', periods=days, freq='D')
    np.random.seed(42)
    base = 100
    data = []
    for date in dates:
        open_p = base + np.random.randn()
        close_p = open_p + np.random.randn() * 2
        high_p = max(open_p, close_p) + abs(np.random.randn())
        low_p = min(open_p, close_p) - abs(np.random.randn())
        data.append({
            'time': date.strftime('%Y-%m-%d'),
            'open': round(open_p, 2),
            'high': round(high_p, 2),
            'low': round(low_p, 2),
            'close': round(close_p, 2)
        })
        base = close_p
    return data

st.title("📊 完整 Lightweight Charts 演示")

data = generate_data()
html = render_chart_html("demo", data, height=450)
components.html(html, height=470, scrolling=False)

st.markdown("---")
st.info("✅ 使用原始 lightweight-charts JS 实现，支持：缩放、拖拽、十字光标、实时数据更新、指标叠加等完整功能")
