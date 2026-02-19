通用价差查询计划草案
1. 目标与范围
目标：在现有的 z120_monitor 基础上实现一个通用的价差查询模块，支持任意两对品种，且两种价差形式均可通过配置驱动（价值价差 value、价差比率 ratio）。
实时性：以实时数据为主，当前 MVP 不强制使用历史数据，必要时提供兜底方案。
MVP 起点：1 对1 的 MNQ-MYM 配对，后续扩展到更多对与并发监控。
输出形式：文本输出为 MVP，未来扩展为 JSON、卡片输出（如飞书 Card）和通知。
与现有代码的对接点：尽量保持对 /z120_monitor 的接口向后兼容，便于渐进落地。
2. 关键数据模型（YAML 配置驱动）
资产定义（AssetConfig）
symbol: 资产代码
exchange: 交易所
sec_type: 证券类型（STK、FUT、CFD 等）
currency: 货币
multiplier: 合约乘数
ratio1: 第一个资产的价差系数
ratio2: 第二个资产的价差系数
对/配对定义（PairConfig）
name: 对名，例如 MNQ-MYM
assets: [AssetConfig, AssetConfig]
mode: "value" 或 "ratio"（两种价差形式的切换）
threshold: 触发阈值
lookback_days: 用于历史统计的天数（后续扩展）
window: 滑动历史窗口长度（如 120，后续扩展）
enabled: true/false
配置示例（config/pairs.yaml，YAML） pairs:
name: "MNQ-MYM" mode: "value" threshold: 1000 lookback_days: 7 window: 120 enabled: true assets:
symbol: "MNQ" exchange: "CME" sec_type: "FUT" currency: "USD" multiplier: 2.0 ratio1: 1
symbol: "MYM" exchange: "CME" sec_type: "FUT" currency: "USD" multiplier: 0.5 ratio2: 2
3. 价差计算核心（两种形式）
价值价差（Value Spread） spread_value(price1, price2) = price1 × multiplier1 × ratio1 − price2 × multiplier2 × ratio2
价差比率（Spread Ratio） spread_ratio(price1, price2) = (price1 × multiplier1 × ratio1) / (price2 × multiplier2 × ratio2)
注意：分母为 0 时应处理，返回 0.0（或按业务需求处理）
4. 信号与输出（MVP 初版）
输出文本为主，后续可扩展为 JSON/卡片输出
输出字段（文本版本，便于直接展示）：
pair: 对名
time: 时间戳
price1: 第一个资产价格
price2: 第二个资产价格
mode: "value" 或 "ratio"
spread_value 或 spread_ratio: 对应价差
threshold: 阈值
signal_type: "NO_SIGNAL" / "LONG" / "SHORT"
signal_action: 具体操作建议，例如 "LONG_ASSET1_SHORT_ASSET2"
reason: 触发原因
history_stats: 历史统计（可选，例如 current、max_7d、min_7d、mean_7d、std_7d）
文本输出示例（1 对 MNQ-MYM，mode=value）

您的输入：MNQ-MYM，price1=25246.0，price2=12500.0，mode=value，threshold=1000
计算：spread_value = 25246 × 2.0 × 1 − 12500 × 0.5 × 2 = 50492 − 12500 = 37992
输出要点：对 MNQ-MYM 的价差为 37992.0，mode=value，threshold=1000，signal_type=NO_SIGNAL，reason=价差未达到阈值
文本输出示例（mode=ratio）

输入：MNQ-MYM，price1=25246.0，price2=12500.0，mode=ratio，threshold=1000
计算：spread_ratio = (25246 × 2.0 × 1) / (12500 × 0.5 × 2) = 50492 / 12500 ≈ 4.039
输出要点：signal_type=NO_SIGNAL，reason=价差比率未超过阈值
5. 数据源与接口设计
数据源接口（DataSource）
get_price(pair_name, asset1_config, asset2_config) -> (price1, price2, timestamp)
subscribe(pair_name, callback)
unsubscribe(pair_name)
实时数据源实现优先：IBKRDataSource（基于 ib_insync）
兜底数据源：HistoryFallbackDataSource（历史/模拟数据）
对接点：GenericSpreadMonitor（单对 MVP 的统一入口，未来扩展为多对并发）
配置加载：通过 YAML 解析 config/pairs.yaml，支持热加载（后续）
输出渲染：render_text_report(pair_result)；后续扩展 render_json_report
6. 实现要点（落地要点，便于落地执行）
单对 MVP：MNQ-MYM，mode=value，实时数据优先
输出：文本为主，支持简单的日志输出
接口对接：保持对 z120_monitor 的 SpreadEngine/历史偏离检测器的兼容性
测试：单元测试覆盖公式、边界、历史统计，集成测试覆盖单对端到端
7. 风险与对策
数据源波动与延迟
对策：多数据源兜底、缓存策略、延迟监控
合约变动/到期
对策：合约滚动策略、切换逻辑
配置错配
对策：配置校验、默认值、回滚机制
性能
对策：单对 MVP 的资源优化，后续扩展并发与向量化
8. 后续落地路径（简要）
先落地 MNQ-MYM 的 MVP（value/ratio 均可切换）
增加对 HSTECH-MCH.HK 等对的配置入口
实时数据源优先，飞书通知集成（文本输出优先，卡片输出后续）
提供可维护的测试用例和文档