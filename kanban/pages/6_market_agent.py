import os
import streamlit as st
from datetime import date
import requests
import json
from concurrent.futures import ThreadPoolExecutor

# 加载 .env
from pathlib import Path

env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().strip().split("\n"):
        if "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from tradingview_mcp.server import financial_news, market_sentiment, combined_analysis

# ─────────────────────────────────────────────
# 常量 & 配置
# ─────────────────────────────────────────────
MINIMAX_BASE_URL = "https://api.minimax.chat/v1"
DEFAULT_MODEL = "MiniMax-M2.1"

SYSTEM_PROMPT = """你是一个专业的市场分析交易员。用户会描述他们观察到的市场现象（如'纳指涨道指跌，油价暴涨'）。你会根据以下搜索到的数据，给出一段简洁的分析结论，格式如下：

## 📊 分析结论
[主要原因推断，100字以内]
置信度：🟢高 / 🟡中 / 🔴低

## 🔍 证据
- 新闻面：[1-2句关键信息]
- 情绪面：[纳指/道指的情绪方向和分数]
- 技术面：[纳指/道指的趋势]

请直接输出一段话，不要列出步骤。"""

INDEX_MAP = {
    "纳指": ("QQQ", "NASDAQ"),
    "nasdaq": ("QQQ", "NASDAQ"),
    "qqq": ("QQQ", "NASDAQ"),
    "道指": ("DIA", "NYSE"),
    "dow": ("DIA", "NYSE"),
    "dia": ("DIA", "NYSE"),
    "标普": ("SPY", "NYSE"),
    "spy": ("SPY", "NYSE"),
}


# ─────────────────────────────────────────────
# LLM 调用
# ─────────────────────────────────────────────
def call_minimax(prompt: str, system: str = "") -> str:
    api_key = os.environ.get("MINIMAX_API_KEY", "")
    if not api_key:
        return "⚠️ 请设置 MINIMAX_API_KEY 环境变量"

    url = f"{MINIMAX_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": DEFAULT_MODEL,
        "messages": messages,
        "max_tokens": 800,
        "temperature": 0.3,
        "reasoning": {"type": "disabled"},
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ 调用失败: {e}"


# ─────────────────────────────────────────────
# 并行数据采集
# ─────────────────────────────────────────────
def collect_data(user_text: str):
    """根据用户文本解析关键词，并行获取新闻/情绪/技术面数据"""
    text_lower = user_text.lower()
    targets = []
    for kw, (sym, ex) in INDEX_MAP.items():
        if kw in text_lower:
            targets.append((sym, ex))
    if not targets:
        targets = [("QQQ", "NASDAQ")]  # 默认查询纳指

    results = {}

    def safe_news(sym):
        try:
            return financial_news(symbol=sym, category="all", limit=5)
        except Exception:
            return {}

    def safe_sentiment(sym):
        try:
            return market_sentiment(symbol=sym, category="all", limit=5)
        except Exception:
            return {}

    def safe_analysis(sym, ex):
        try:
            return combined_analysis(symbol=sym, exchange=ex, timeframe="1D")
        except Exception:
            return {}

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {}
        for sym, ex in targets:
            futures[pool.submit(safe_news, sym)] = f"{sym}_news"
            futures[pool.submit(safe_sentiment, sym)] = f"{sym}_sentiment"
            futures[pool.submit(safe_analysis, sym, ex)] = f"{sym}_analysis"

        for future in futures:
            key = futures[future]
            try:
                results[key] = future.result(timeout=15)
            except Exception:
                results[key] = {}

    return targets, results


# ─────────────────────────────────────────────
# 数据格式化
# ─────────────────────────────────────────────
def format_data(user_text: str, targets, results):
    """将搜索结果格式化为 LLM 可读的文本"""
    parts = [f"用户描述的市场现象：{user_text}\n\n"]
    parts.append("=== 搜索到的数据 ===\n")

    for sym, ex in targets:
        parts.append(f"\n--- {sym} ({ex}) ---\n")

        # 新闻
        news_key = f"{sym}_news"
        news_items = []
        raw = results.get(news_key, {})
        if isinstance(raw, dict):
            news_items = raw.get("items", [])
        parts.append(f"新闻({len(news_items)}条):\n")
        for item in news_items[:5]:
            parts.append(
                f"  - {item.get('title', '')[:80]} [source: {item.get('source', '')}]\n"
            )

        # 情绪
        sent_key = f"{sym}_sentiment"
        sent = results.get(sent_key, {})
        if isinstance(sent, dict):
            score = sent.get("sentiment_score", 0)
            label = sent.get("sentiment_label", "N/A")
            posts = sent.get("posts_analyzed", 0)
            parts.append(f"情绪: score={score:.2f} label={label} posts={posts}\n")

        # 技术面
        an_key = f"{sym}_analysis"
        an = results.get(an_key, {})
        if isinstance(an, dict):
            trend = an.get("trend", "N/A")
            rec = an.get("recommendations", {})
            parts.append(f"技术面: trend={trend} recommendations={rec}\n")

    return "".join(parts)


# ─────────────────────────────────────────────
# 渲染函数
# ─────────────────────────────────────────────
def render_market_agent():
    st.markdown("### 🤖 市场分析 Agent")
    st.caption("输入市场现象，AI 自动搜索新闻+情绪+技术面并给出分析结论")

    # 检查 API Key
    if not os.environ.get("MINIMAX_API_KEY"):
        st.warning("⚠️ 请设置 MINIMAX_API_KEY 环境变量")

    # 初始化聊天历史
    st.session_state.setdefault("messages", [])

    # 渲染聊天历史
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 聊天输入
    user_input = st.chat_input("描述你观察到的市场现象...")

    if user_input:
        # 1. 添加用户消息
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # 2. 并行搜索 + 生成分析
        with st.chat_message("assistant"):
            with st.spinner("🔍 分析中..."):
                targets, results = collect_data(user_input)
                formatted = format_data(user_input, targets, results)
                analysis = call_minimax(
                    prompt=f"{formatted}\n\n请根据以上数据给出分析结论。",
                    system=SYSTEM_PROMPT,
                )
                st.markdown(analysis)

        # 3. 保存助手消息
        st.session_state.messages.append({"role": "assistant", "content": analysis})


# ─────────────────────────────────────────────
# 测试入口（可删除）
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # 简单测试 call_minimax
    test_result = call_minimax(
        prompt="纳指昨晚涨了2%，道指小跌，怎么回事？",
        system=SYSTEM_PROMPT,
    )
    print(test_result)


render_market_agent()
