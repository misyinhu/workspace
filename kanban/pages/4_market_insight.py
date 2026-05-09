import streamlit as st
from datetime import date
from concurrent.futures import ThreadPoolExecutor

from tradingview_mcp.server import financial_news, market_sentiment, combined_analysis


# Keyword → (symbol, exchange, label_cn)
INDEX_MAP = {
    "纳指": ("QQQ", "NASDAQ"),
    "nasdaq": ("QQQ", "NASDAQ"),
    "qqq": ("QQQ", "NASDAQ"),
    "道指": ("DIA", "NYSE"),
    "dow": ("DIA", "NYSE"),
    "dia": ("DIA", "NYSE"),
    "标普": ("SPY", "NYSE"),
    "spy": ("SPY", "NYSE"),
    "s&p": ("SPY", "NYSE"),
}


def parse_targets(text: str):
    text_lower = text.lower()
    found = {}
    for kw, (sym, ex) in INDEX_MAP.items():
        if kw in text_lower:
            found[sym] = (sym, ex)
    # Always include at least QQQ as fallback
    if not found:
        found["QQQ"] = ("QQQ", "NASDAQ")
    return list(found.values())


def search_target(symbol, exchange, limit=5):
    news = financial_news(symbol=None, category="all", limit=limit)
    sentiment = market_sentiment(symbol=symbol, category="all", limit=limit)
    analysis = combined_analysis(symbol=symbol, exchange=exchange, timeframe="1D")
    return {
        "symbol": symbol,
        "exchange": exchange,
        "news": news,
        "sentiment": sentiment,
        "analysis": analysis,
    }


def generate_report(targets_data, user_text):
    lines = ["## 📊 分析结论\n"]

    # Collect evidence
    all_news = []
    all_sentiments = []
    all_technicals = []

    for t in targets_data:
        sym = t["symbol"]
        news_items = t["news"].get("items", []) if isinstance(t["news"], dict) else []
        all_news.extend([(n.get("title", ""), n.get("source", "")) for n in news_items])

        sent = t["sentiment"]
        if isinstance(sent, dict):
            all_sentiments.append(
                {
                    "symbol": sym,
                    "score": sent.get("sentiment_score", 0.5),
                    "label": sent.get("sentiment_label", "Neutral"),
                    "posts": sent.get("posts_analyzed", 0),
                }
            )

        an = t["analysis"]
        if isinstance(an, dict):
            trend = an.get("trend", "unknown")
            all_technicals.append({"symbol": sym, "trend": trend})

    # Theme detection from news titles
    themes = {}
    for title, _ in all_news:
        title_l = title.lower()
        if any(w in title_l for w in ["oil", "crude", "petroleum", "油价", "原油"]):
            themes["oil"] = themes.get("oil", 0) + 1
        if any(
            w in title_l
            for w in ["iran", "middle east", "geopolitical", "伊朗", "中东"]
        ):
            themes["iran"] = themes.get("iran", 0) + 1
        if any(w in title_l for w in ["fed", "rate", "interest", "利率"]):
            themes["fed"] = themes.get("fed", 0) + 1
        if any(w in title_l for w in ["tech", "nasdaq", "software", "科技"]):
            themes["tech"] = themes.get("tech", 0) + 1
        if any(
            w in title_l for w in ["bank", "financial", "industrial", "银行", "工业"]
        ):
            themes["bank"] = themes.get("bank", 0) + 1

    # Determine main cause
    top_theme = max(themes, key=themes.get) if themes else None
    theme_labels = {
        "oil": "油价上涨影响传统行业（能源/银行/工业）",
        "iran": "中东地缘政治风险升温",
        "fed": "美联储利率预期分化",
        "tech": "科技股资金轮动",
        "bank": "金融板块承压",
    }
    cause = theme_labels.get(top_theme, "市场结构性分化")

    # Confidence
    total_evidence = len(all_news) + len(all_sentiments) + len(all_technicals)
    if total_evidence >= 10:
        confidence = "🟢 高"
    elif total_evidence >= 5:
        confidence = "🟡 中"
    else:
        confidence = "🔴 低"

    lines.append(f"**主要原因**：{cause}")
    lines.append(f"**置信度**：{confidence}\n")
    lines.append("---\n")
    lines.append("## 🔍 证据汇总\n")

    # Sentiment
    lines.append("### 💬 情绪面")
    for s in all_sentiments:
        emoji = "🟢" if s["score"] > 0.55 else "🔴" if s["score"] < 0.45 else "🟡"
        lines.append(
            f"- {s['symbol']}: {emoji} {s['label']} (score={s['score']:.2f}, {s['posts']}条帖子)"
        )
    lines.append("")

    # Technical
    lines.append("### 📊 技术面")
    for t in all_technicals:
        lines.append(f"- {t['symbol']}: {t['trend']}")
    lines.append("")

    # News themes
    lines.append("### 📰 新闻主题")
    for theme, count in sorted(themes.items(), key=lambda x: -x[1]):
        lines.append(f"- {theme_labels.get(theme, theme)}: {count}条相关新闻")
    if not themes:
        lines.append("- 暂无明显新闻主题")
    lines.append("")
    lines.append("---\n")
    lines.append("## 📋 原始新闻\n")

    for title, source in all_news[:8]:
        if title:
            lines.append(f"- {title[:70]}... ({source})")

    return "\n".join(lines)


def render_market_insight():
    st.markdown("### 🔍 市场洞察")
    st.caption("输入市场现象 → AI 搜索新闻+情绪+技术面 → 输出分析结论")

    user_text = st.text_area(
        "📝 描述你观察到的市场现象",
        placeholder="例如：纳指涨道指跌，油价暴涨，可能跟伊朗战争有关",
        height=80,
        key="insight_input",
    )

    col_btn = st.columns([1, 1, 2])
    with col_btn[0]:
        analyze = st.button("🔍 开始分析", type="primary", key="analyze_btn")
    with col_btn[1]:
        clear = st.button("🗑 清空")

    if clear:
        st.rerun()

    if analyze:
        if not user_text.strip():
            st.warning("请输入市场现象描述")
            return

        targets = parse_targets(user_text)

        with st.spinner("正在搜索新闻、情绪、技术面数据..."):
            results = []
            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = [
                    pool.submit(search_target, sym, ex, 5) for sym, ex in targets
                ]
                for f in futures:
                    try:
                        results.append(f.result(timeout=15))
                    except Exception:
                        pass

        if not results:
            st.error("数据获取超时，请稍后重试")
            return

        # Also search general/oil news
        try:
            oil_news = financial_news(symbol=None, category="all", limit=5)
        except Exception:
            oil_news = {}

        report = generate_report(results, user_text)
        st.markdown(report)


if __name__ == "__main__":
    render_market_insight()
