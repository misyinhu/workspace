# 市场分析调研 Agent — Tasks

## [x] 创建页面文件 `kanban/pages/6_market_agent.py`

- 现象输入框（多行文本，`st.text_area`）→ 使用 `st.chat_input` 聊天交互
- 分析按钮（`st.button`，触发 Agent 工作流）→ 聊天输入自动触发
- 输出区域（`st.markdown` 渲染结构化报告）→ AI 分析结论直接渲染

## [x] 实现关键词解析函数

- 识别指数类型：纳指(QQQ/NASDAQ)、道指(DIA/DOW)、标普(SPY) ✓ INDEX_MAP 已实现
- 识别市场现象：劈差、暴涨、暴跌、背离、散户FOMO → 用户自由文本描述
- 映射到对应的 TV symbol + exchange ✓ INDEX_MAP 已实现

## [x] 实现并行搜索逻辑

- `st.spinner` 加载状态 ✓ 已实现（`with st.spinner("🔍 分析中...")`）
- 并行调用：`tv_mcp_financial_news` + `tv_mcp_market_sentiment` + `tv_mcp_combined_analysis` ✓ 已实现（ThreadPoolExecutor）
- 搜索多个相关标的（如 QQQ + SPY + DIA）✓ 已实现（多标的并行）

## [x] 实现报告生成逻辑

- 汇总新闻标题 + 情绪数据 + 技术面数据 ✓ `format_data()` 实现
- 推断主要原因（从新闻关键词+情绪方向推断）✓ LLM 调用实现
- 计算置信度（证据数量）✓ LLM 输出包含置信度
- 生成 Markdown 格式报告 ✓ SYSTEM_PROMPT 指定格式

## [x] 更新 `kanban/app.py` 导航

- 在侧边栏添加 `page_link("pages/6_market_agent.py", label="🤖 市场分析")` ✓ 已添加

## [ ] 单元测试（未实现）

- 测试关键词解析（纳指、道指、油价等）
- 测试报告生成（空数据/正常数据）
- 测试并行搜索（mock tv-mcp 工具）

---

# P0 Bugs

## [x] `3_three_screen.py:187` - `color` 未定义

**位置**: `kanban/pages/3_three_screen.py:187`
```python
st.subheader(f"{color} {title} ({len(df)} 个)")
```
**问题**: `color` 变量在 `_render_signal_table` 函数中未定义
**修复**: 在函数开头添加 `color = "📈" if "做多" in title else "📉" if "做空" in title else "📊"`

## [x] `webhook_bridge.py:331` - `get_z120_status` 未定义

**位置**: `notify/webhook_bridge.py:331`
```python
z120_status = get_z120_status()
```
**问题**: 函数 `get_z120_status()` 在文件中未定义就被调用（z120 已废弃）
**修复**: 替换为 `z120_status = "已停止"` 并注释说明 z120 已废弃
