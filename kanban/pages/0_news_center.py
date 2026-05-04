import streamlit as st
from datetime import date

from tradingview_mcp.server import financial_news as tv_financial_news
from tradingview_mcp.server import market_sentiment as tv_market_sentiment


def render_news_center():
    st.markdown("### 📰 新闻事件中心")
    st.caption("实时财经新闻与社区情绪分析")

    col_dates = st.columns(2)
    with col_dates[0]:
        start_date = st.date_input(
            "开始日期",
            value=date.today(),
            key="news_start",
        )
    with col_dates[1]:
        end_date = st.date_input(
            "结束日期",
            value=date.today(),
            key="news_end",
        )

    category = st.selectbox(
        "分类",
        ["all", "crypto", "stocks"],
        index=0,
        format_func=lambda x: {"all": "全部", "crypto": "加密货币", "stocks": "股票"}[
            x
        ],
        key="news_category",
    )

    limit = st.slider("新闻数量", 5, 30, 10, key="news_limit")

    tab_news, tab_sentiment = st.tabs(["📋 财经新闻", "💬 市场情绪"])

    with tab_news:
        with st.spinner("加载财经新闻..."):
            news_items = tv_financial_news(symbol=None, category=category, limit=limit)
        raw_items = news_items.get("items", []) if isinstance(news_items, dict) else []
        if not raw_items:
            st.info("暂无新闻数据")
        else:
            for item in raw_items:
                pub_date = item.get("published", "")[:16]
                title = item.get("title", "")
                summary = item.get("summary", "") or item.get("title", "")
                source = item.get("source", "")
                date_str = pub_date[:10] if pub_date else ""
                if date_str:
                    try:
                        item_date = date.fromisoformat(date_str)
                        if not (start_date <= item_date <= end_date):
                            continue
                    except Exception:
                        pass
                with st.expander(f"**{title[:80]}**"):
                    st.caption(f"{pub_date} | {source}")
                    st.write(summary[:300] if summary else title)

    with tab_sentiment:
        default_symbol = "BTC" if category in ("all", "crypto") else "AAPL"
        sentiment_symbol = st.text_input(
            "查询Symbol",
            value=default_symbol,
            key="sentiment_symbol",
        ).strip()

        if sentiment_symbol:
            with st.spinner(f"加载 {sentiment_symbol} 情绪数据..."):
                sentiment_data = tv_market_sentiment(
                    symbol=sentiment_symbol,
                    category="all",
                    limit=limit,
                )
            top_posts = (
                sentiment_data.get("top_posts", [])
                if isinstance(sentiment_data, dict)
                else []
            )
            if not top_posts:
                st.info("暂无情绪数据")
            else:
                score = sentiment_data.get("sentiment_score", 0.5)
                label = sentiment_data.get("sentiment_label", "Neutral")
                st.caption(
                    f"整体情绪: {label} ({score:.2f}) · 已分析 {sentiment_data.get('posts_analyzed', 0)} 条帖子"
                )
                st.divider()
                for post in top_posts:
                    title = post.get("title", "")
                    author = post.get("author", "匿名")
                    upvotes = post.get("upvotes", 0)
                    subreddit = post.get("subreddit", "")
                    post_sentiment = post.get("sentiment", "").lower()
                    if post_sentiment == "bullish":
                        emoji, sent_label = "🟢", "看多"
                    elif post_sentiment == "bearish":
                        emoji, sent_label = "🔴", "看空"
                    else:
                        emoji, sent_label = "🟡", "中立"
                    sentiment_score = post.get("sentimentScore", 0.5)
                    with st.expander(f"{emoji} {sent_label} | {title[:60]}..."):
                        st.caption(
                            f"u/{author} · r/{subreddit} · ▲{upvotes} · score:{sentiment_score:.2f}"
                        )


render_news_center()
