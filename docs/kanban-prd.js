const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        Header, Footer, AlignmentType, LevelFormat, HeadingLevel, BorderStyle,
        WidthType, ShadingType, VerticalAlign, PageNumber, PageBreak } = require('docx');
const fs = require('fs');

const cellBorder = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const cellBorders = { top: cellBorder, bottom: cellBorder, left: cellBorder, right: cellBorder };

function headerCell(text, width) {
  return new TableCell({
    borders: cellBorders,
    width: { size: width, type: WidthType.DXA },
    shading: { fill: "D5E8F0", type: ShadingType.CLEAR },
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text, bold: true, size: 22 })]
    })]
  });
}

function dataCell(text, width) {
  return new TableCell({
    borders: cellBorders,
    width: { size: width, type: WidthType.DXA },
    children: [new Paragraph({
      children: [new TextRun({ text, size: 22 })]
    })]
  });
}

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 24 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal",
        run: { size: 56, bold: true, color: "000000", font: "Arial" },
        paragraph: { spacing: { before: 240, after: 120 }, alignment: AlignmentType.CENTER } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, color: "000000", font: "Arial" },
        paragraph: { spacing: { before: 360, after: 240 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, color: "333333", font: "Arial" },
        paragraph: { spacing: { before: 240, after: 180 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, color: "555555", font: "Arial" },
        paragraph: { spacing: { before: 180, after: 120 }, outlineLevel: 2 } },
    ]
  },
  numbering: {
    config: [
      { reference: "bullet-list", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "bullet-list-2", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbered-list", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },
  sections: [{
    properties: {
      page: { margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } }
    },
    headers: {
      default: new Header({ children: [new Paragraph({
        alignment: AlignmentType.RIGHT,
        children: [new TextRun({ text: "Kanban Trading System PRD", color: "888888", size: 20 })]
      })] })
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "Page ", size: 20 }), new TextRun({ children: [PageNumber.CURRENT], size: 20 }),
                   new TextRun({ text: " of ", size: 20 }), new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 20 })]
      })] })
    },
    children: [
      // Title
      new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun("Kanban 交易系统 PRD")] }),
      new Paragraph({ children: [new TextRun({ text: "版本: v2.0 | 更新日期: 2026-04-28", color: "666666", size: 22 })] }),
      new Paragraph({ children: [new PageBreak()] }),

      // 1. 项目背景
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("1. 项目背景")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("1.1 问题")] }),
      new Paragraph({ children: [new TextRun({ text: "交易员当前痛点：", bold: true })] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun("手动在 TradingView 切换周期，肉眼对比趋势 → 耗时且容易遗漏信号")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun("不同数据源（加密货币、A股、美股、港股）分散在不同平台")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun("需要统一的市场扫描工具，从大量标的中快速筛选符合条件的交易机会")] }),

      new Paragraph({ children: [new TextRun({ text: "当前已有基础设施：", bold: true })] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun("quant-core 统一数据基础设施已部署")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun("/api/scan/market API 已上线")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun("三滤网交易法信号生成器已实现")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("1.2 目标")] }),
      new Paragraph({ children: [new TextRun({ text: "核心目标：", bold: true })] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun("实现市场扫描页面，支持多交易所批量扫描")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun("提供多种扫描策略（交易量突破、布林带、趋势、连续K线、多周期变化）")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun("支持三滤网信号精筛，过滤假信号")] }),

      new Paragraph({ children: [new TextRun({ text: "成功指标：", bold: true })] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun("扫描响应时间 < 30秒（单交易所，50个品种）")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun("三滤网信号确认准确率 > 70%（通过历史回测验证）")] }),

      new Paragraph({ children: [new PageBreak()] }),

      // 2. 用户故事
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("2. 用户故事")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("US-01：多周期共振分析")] }),
      new Paragraph({ children: [new TextRun({ text: "角色：", bold: true }), new TextRun("交易员")] }),
      new Paragraph({ children: [new TextRun({ text: "场景：", bold: true }), new TextRun("当我在下单前需要分析多个时间周期的趋势一致性时")] }),
      new Paragraph({ children: [new TextRun({ text: "意图：", bold: true }), new TextRun("我希望一眼看到各周期（M1/M5/M30/M1H/4H/1D）的趋势方向、共振评分、三滤网入场信号")] }),
      new Paragraph({ children: [new TextRun({ text: "动机：", bold: true }), new TextRun("以便快速判断是否多周期共振，提高决策效率")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("US-02：跨品种套利分析")] }),
      new Paragraph({ children: [new TextRun({ text: "角色：", bold: true }), new TextRun("交易员")] }),
      new Paragraph({ children: [new TextRun({ text: "场景：", bold: true }), new TextRun("当我发现两个相关品种存在价差机会时")] }),
      new Paragraph({ children: [new TextRun({ text: "意图：", bold: true }), new TextRun("我希望输入两个品种，自动计算价差、比率、相关性、Z-Score，并生成套利信号")] }),
      new Paragraph({ children: [new TextRun({ text: "动机：", bold: true }), new TextRun("以便捕捉均值回归的套利机会")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("US-03：TradingView 警报监控")] }),
      new Paragraph({ children: [new TextRun({ text: "角色：", bold: true }), new TextRun("交易员")] }),
      new Paragraph({ children: [new TextRun({ text: "场景：", bold: true }), new TextRun("当我在 TradingView 设置了技术指标警报，需要统一查看所有警报触发情况时")] }),
      new Paragraph({ children: [new TextRun({ text: "意图：", bold: true }), new TextRun("我希望有一个警报中心，自动扫描 TradingView 布局中的指标警报状态")] }),
      new Paragraph({ children: [new TextRun({ text: "动机：", bold: true }), new TextRun("以便无需切换窗口即可监控所有警报")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("US-04：市场扫描 - 选择扫描策略")] }),
      new Paragraph({ children: [new TextRun({ text: "角色：", bold: true }), new TextRun("交易员")] }),
      new Paragraph({ children: [new TextRun({ text: "场景：", bold: true }), new TextRun("当我需要进行全市场扫描，寻找符合条件的交易机会时")] }),
      new Paragraph({ children: [new TextRun({ text: "意图：", bold: true }), new TextRun("我希望选择扫描策略和市场，一键扫描")] }),
      new Paragraph({ children: [new TextRun({ text: "动机：", bold: true }), new TextRun("以便从大量标的中快速筛选出符合条件的候选品种")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("US-05：市场扫描 - 信号精筛")] }),
      new Paragraph({ children: [new TextRun({ text: "角色：", bold: true }), new TextRun("交易员")] }),
      new Paragraph({ children: [new TextRun({ text: "场景：", bold: true }), new TextRun("当扫描结果返回大量候选标的时")] }),
      new Paragraph({ children: [new TextRun({ text: "意图：", bold: true }), new TextRun("我希望启用三滤网信号过滤，让 Scanner 粗筛的结果再经过 MultiPeriodSignalGenerator 精筛")] }),
      new Paragraph({ children: [new TextRun({ text: "动机：", bold: true }), new TextRun("以便过滤假突破，提高信号质量")] }),

      new Paragraph({ children: [new PageBreak()] }),

      // 3. 功能说明
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("3. 功能说明")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("F-01：多周期共振分析")] }),
      new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("F-01-1：多周期 K 线图表展示")] }),
      new Paragraph({ children: [new TextRun("通过 streamlit-lightweight-charts-pro 渲染 K 线图，支持周期切换（1m/5m/30m/4h/1D）。实时获取 quant-core API 多周期数据。")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("F-01-2：三滤网入场信号")] }),
      new Paragraph({ children: [new TextRun("M30 趋势（MomentumFilter）+ M5 回调（PullbackFilter）+ M1 入场（EntryFilter），计算信号强度 0-100，展示入场价、止损、盈亏比。")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("F-01-3：共振评分仪表盘")] }),
      new Paragraph({ children: [new TextRun("计算各周期趋势一致性，评分 0-100，显示上涨/下跌/震荡分布。")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("F-01-4：交易建议")] }),
      new Paragraph({ children: [new TextRun("根据共振评分和矛盾检测生成建议：强烈买入/买入/观望/卖出/强烈卖出，含置信度和原因说明。")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("F-02：跨品种套利分析")] }),
      new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("F-02-1：双品种价差计算")] }),
      new Paragraph({ children: [new TextRun("获取两个品种历史数据，计算价差（spread）和价格比率（ratio）。")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("F-02-2：相关性分析")] }),
      new Paragraph({ children: [new TextRun("计算 20 日滚动相关性，相关性 > 0.8 适合套利。")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("F-02-3：Z-Score 计算与套利信号")] }),
      new Paragraph({ children: [new TextRun("Z-Score > 2.0 生成 SELL_SPREAD 信号，Z-Score < -2.0 生成 BUY_SPREAD 信号。")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("F-03：TradingView 警报监控")] }),
      new Paragraph({ children: [new TextRun("通过 Chrome CDP 连接 TradingView，扫描所有打开的图表布局，提取指标数值和警报状态。")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("F-04：市场扫描 - 扫描策略")] }),
      new Paragraph({ children: [new TextRun("支持 5 种扫描策略：")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun("volume_breakout：交易量突破（放量倍数 > 2x，价格变化 > 3%）")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun("bollinger：布林带分析（价格触及上下轨）")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun("trending：趋势分析（均线斜率）")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun("consecutive：连续K线（连续 3 根同向K线）")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun("multi_changes：多周期变化（跨周期信号确认）")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("F-05：市场扫描 - 信号精筛")] }),
      new Paragraph({ children: [new TextRun("三滤网开关控制：")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun("关闭时：Scanner 粗筛结果直接返回")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun("开启时：Scanner 结果经过 MultiPeriodSignalGenerator 精筛，只返回 TAKE_LONG/TAKE_SHORT")] }),

      new Paragraph({ children: [new PageBreak()] }),

      // 4. 页面结构
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("4. 页面结构")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.1 页面导航")] }),
      new Paragraph({ children: [new TextRun("侧边栏显示页面导航：")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun("📰 新闻事件中心")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun("🚨 警报中心")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun("📈 多周期共振分析")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, children: [new TextRun("🔍 市场扫描")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.2 市场扫描页面布局")] }),
      new Paragraph({ children: [new TextRun({ text: "左侧边栏：", bold: true }), new TextRun("扫描类型多选 + 市场多选 + 参数配置")] }),
      new Paragraph({ children: [new TextRun({ text: "主内容区：", bold: true }), new TextRun("扫描结果表格（品种/方向/强度/放量/涨跌/M30趋势/回调/入场/建议）")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.3 共振分析页面布局")] }),
      new Paragraph({ children: [new TextRun({ text: "左侧边栏：", bold: true }), new TextRun("品种选择 + 跨品种套利开关 + 自动刷新")] }),
      new Paragraph({ children: [new TextRun({ text: "主内容区：", bold: true }), new TextRun("K线图 + 三滤网信号 + 各周期趋势卡片 + 共振仪表 + 交易建议")] }),

      new Paragraph({ children: [new PageBreak()] }),

      // 5. API 接口
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("5. API 接口")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("5.1 市场扫描 API")] }),
      new Paragraph({ children: [new TextRun({ text: "端点：", bold: true }), new TextRun("POST /api/scan/market")] }),
      new Paragraph({ children: [new TextRun({ text: "数据源：", bold: true }), new TextRun("quant-core (http://100.82.238.11:8005)")] }),

      new Table({
        columnWidths: [2160, 7200],
        rows: [
          new TableRow({ children: [headerCell("参数", 2160), headerCell("说明", 7200)] }),
          new TableRow({ children: [dataCell("scanners", 2160), dataCell("扫描类型列表 [volume_breakout/bollinger/trending/consecutive/multi_changes]", 7200)] }),
          new TableRow({ children: [dataCell("exchanges", 2160), dataCell("市场列表 [okx/bybit/coinbase/sse/szse/nasdaq/nyse/hkex/twse]", 7200)] }),
          new TableRow({ children: [dataCell("use_signal_filter", 2160), dataCell("是否启用三滤网精筛 (true/false)", 7200)] }),
          new TableRow({ children: [dataCell("timeframe", 2160), dataCell("时间周期 (5m/15m/30m/1h/4h)", 7200)] }),
          new TableRow({ children: [dataCell("volume_multiplier", 2160), dataCell("放量倍数阈值 (默认 2.0)", 7200)] }),
          new TableRow({ children: [dataCell("price_change_min", 2160), dataCell("最小价格变化百分比 (默认 3.0)", 7200)] }),
          new TableRow({ children: [dataCell("limit", 2160), dataCell("返回结果数量上限 (默认 25)", 7200)] }),
        ]
      }),

      new Paragraph({ children: [new PageBreak()] }),

      // 6. 技术架构
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("6. 技术架构")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("6.1 系统架构")] }),
      new Paragraph({ children: [new TextRun("前端：Streamlit 多页面应用，部署于本地或 CXClaw 服务器")] }),
      new Paragraph({ children: [new TextRun("后端：quant-core FastAPI 服务，远程部署于 100.82.238.11:8005")] }),
      new Paragraph({ children: [new TextRun("数据源：OKX / TradingView / IB / TdxQuant 通过 quant-core 统一接入")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("6.2 核心模块")] }),
      new Table({
        columnWidths: [2160, 7200],
        rows: [
          new TableRow({ children: [headerCell("模块", 2160), headerCell("说明", 7200)] }),
          new TableRow({ children: [dataCell("quant_core/scanner", 2160), dataCell("市场扫描模块：volume_breakout/bollinger/trending/consecutive/multi_changes", 7200)] }),
          new TableRow({ children: [dataCell("quant_core/factors", 2160), dataCell("技术因子模块：MACD/KDJ/RSI/均线/斐波那契/三滤网信号", 7200)] }),
          new TableRow({ children: [dataCell("quant_core/data", 2160), dataCell("市场数据模块：交易所配置/品种列表/screener映射", 7200)] }),
          new TableRow({ children: [dataCell("trading/kanban", 2160), dataCell("Streamlit 前端：多周期共振/套利分析/警报监控/市场扫描", 7200)] }),
        ]
      }),

      new Paragraph({ children: [new PageBreak()] }),

      // 7. 交付清单
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("7. 交付清单")] }),

      new Table({
        columnWidths: [2160, 3600, 3600],
        rows: [
          new TableRow({ children: [headerCell("功能", 2160), headerCell("文件", 3600), headerCell("状态", 3600)] }),
          new TableRow({ children: [dataCell("多周期共振分析", 2160), dataCell("1_resonance.py", 3600), dataCell("已完成", 3600)] }),
          new TableRow({ children: [dataCell("跨品种套利分析", 2160), dataCell("1_resonance.py (render_pair_analysis)", 3600), dataCell("已完成", 3600)] }),
          new TableRow({ children: [dataCell("TradingView警报监控", 2160), dataCell("2_alerts.py", 3600), dataCell("已完成", 3600)] }),
          new TableRow({ children: [dataCell("市场扫描-扫描策略", 2160), dataCell("3_market_scan.py", 3600), dataCell("已完成", 3600)] }),
          new TableRow({ children: [dataCell("市场扫描-信号精筛", 2160), dataCell("3_market_scan.py (filter_with_signal)", 3600), dataCell("已完成", 3600)] }),
          new TableRow({ children: [dataCell("Scanner模块", 2160), dataCell("quant_core/scanner/", 3600), dataCell("已完成", 3600)] }),
          new TableRow({ children: [dataCell("Factors模块", 2160), dataCell("quant_core/factors/", 3600), dataCell("已完成", 3600)] }),
          new TableRow({ children: [dataCell("Data模块", 2160), dataCell("quant_core/data/", 3600), dataCell("已完成", 3600)] }),
        ]
      }),

      new Paragraph({ spacing: { before: 480 }, children: [new TextRun({ text: "文档版本：v2.0 | 更新日期：2026-04-28", color: "666666", size: 20 })] }),
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("/Users/wang/.opencode/workspace/trading/docs/kanban-prd-v2.docx", buffer);
  console.log("PRD document created successfully!");
});
