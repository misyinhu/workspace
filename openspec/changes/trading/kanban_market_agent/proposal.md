# 市场分析调研 Agent

## 1. 目标

在 Kanban 中新增一个**市场分析调研 Agent**，帮助交易者快速获取针对当前市场现象的**实时分析观点**，回答"为什么会产生这种行情"这类问题。

## 2. 用户故事

> 交易者发现纳指和道指出现劈差，想知道原因。
> 他在 Kanban 里输入"纳指和道指劈差，可能跟伊朗战争/油价有关，帮我查一下市场分析"。
> Agent 自动执行：搜新闻 + 搜情绪 + 综合技术面，输出一段人话结论。

## 3. 核心功能

| 功能 | 说明 |
|---|---|
| **现象输入** | 用户描述观察到的市场现象（如"纳指涨道指跌"、"油价暴涨"） |
| **多源搜索** | 并行搜索：财经新闻、Reddit社区情绪、技术面数据 |
| **AI 综合结论** | 将搜索结果整合成一段人话分析结论 |
| **输出格式** | 结构化报告：原因推断 + 置信度 + 相关新闻链接 |

## 4. 实现方式

使用现有 `tv-mcp` 工具链，无需新增数据源：

```python
# 现象："纳指 vs 道指劈差 + 伊朗战争"
symbol = "QQQ"  # 纳指
exchange = "NASDAQ"
道指_symbol = "DIA"  # 道指ETF
exchange2 = "NYSE"

# 1. 并行搜索新闻 + 情绪 + 技术面
news_qqq = tv_mcp_financial_news(symbol="QQQ", category="stocks", limit=5)
news_dia = tv_mcp_financial_news(symbol="DIA", category="stocks", limit=5)
sentiment_qqq = tv_mcp_market_sentiment(symbol="QQQ", category="stocks", limit=5)
sentiment_dia = tv_mcp_market_sentiment(symbol="DIA", category="stocks", limit=5)
analysis_qqq = tv_mcp_combined_analysis(symbol="QQQ", exchange="NASDAQ", timeframe="1D")
analysis_dia = tv_mcp_combined_analysis(symbol="DIA", exchange="NYSE", timeframe="1D")

# 2. 搜索地缘政治/大宗商品新闻
news_oil = tv_mcp_financial_news(category="all", limit=5)  # 油价相关新闻
```

## 5. UI 页面

在 `kanban/pages/` 下新增 `4_market_insight.py`：

- 顶部：**现象输入框**（多行文本，用户描述观察到的市场现象）
- 中部：**分析 Agent 按钮**（触发搜索 + 生成报告）
- 底部：**分析报告输出**（结构化展示：原因、置信度、证据来源）

## 6. 成功标准

- [ ] 用户输入市场现象，10秒内返回分析报告
- [ ] 报告包含：主要原因推断、置信度、至少3条证据（新闻/情绪/技术面）
- [ ] 支持常见市场现象：指数劈差、油价异动、单边行情、社区FOMO等

## 7. 风险

- `tv-mcp` 工具返回空结果时，需要有降级策略
- Reddit 情绪数据有时延，不能作为实时判断的唯一依据