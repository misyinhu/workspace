# 市场分析调研 Agent — SPEC

## 页面

| # | 页面 | 文件 | 功能 |
|---|---|---|---|
| 6 | 市场洞察 | `kanban/pages/4_market_insight.py` | 现象输入 → AI 分析报告 |

## 数据源

| 功能 | 调用 |
|---|---|
| 财经新闻 | `tv_mcp_financial_news(symbol, category, limit)` |
| 市场情绪 | `tv_mcp_market_sentiment(symbol, category, limit)` |
| 综合技术分析 | `tv_mcp_combined_analysis(symbol, exchange, timeframe)` |

## 工作流

```
用户输入现象 → 解析关键词 → 并行搜索 → 整合报告 → 展示结果
```

## 输出格式

```
## 分析结论
[原因推断 + 置信度]

## 证据
- 📰 新闻：...
- 💬 情绪：...
- 📊 技术面：...

## 相关链接
[新闻标题 → URL]
```

## 技术要求

- 并行调用多个 tv-mcp 工具，汇总结果
- 超过 5 秒未返回，显示 spinner 加载状态
- 数据为空时，显示"暂无数据，请尝试其他关键词"