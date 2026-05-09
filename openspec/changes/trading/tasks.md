# Trading 项目需求清单

## [P0] 紧急

- [ ] **运行时错误 - 未定义名称 `color`** (kanban/pages/3_three_screen.py:187)
  - 来源：ruff F821
  - `color` 变量在 f-string 中使用但未定义，会导致页面崩溃

- [ ] **运行时错误 - 未定义名称 `get_z120_status`** (notify/webhook_bridge.py:331)
  - 来源：ruff F821
  - 函数调用未定义，z120 已废弃，应清理此调用或定义桩函数

- [ ] **运行时错误 - 未定义名称 `List/Dict/Bar/pd`** (temp_tdx_fix.py)
  - 来源：ruff F821
  - 类型注解缺失导入，该文件无法作为模块导入

- [ ] **字典键重复** (notify/nl_parser.py:132)
  - 来源：ruff F601
  - `"黄金"` 键在 symbol_map 中重复定义，后值会覆盖前值

## [P1] 重要

- [ ] **代码质量 - 大量裸 except (E722)**：342 处
  - 来源：ruff check
  - 主要分布在：client/ibkr_client.py (4处), client/ib_connection.py (1处), data/get_realtime_data.py (1处), kanban/pages/*.py (3处), orders/place_order.py (3处), orders/place_order_func.py (3处), notify/webhook_bridge.py (2处)
  - 风险：错误被静默吞噬，调试困难，可能隐藏严重 bug

- [ ] **代码质量 - 模块级导入顺序错误 (E402)**：852 处
  - 来源：ruff check
  - 主要分布在：orders/place_order_func.py, notify/refresh_and_notify.py, notify/webhook_bridge.py
  - 影响：代码维护性差，依赖关系不清晰

- [ ] **测试覆盖不足 - okx_client 模块**：38 个文件，无单元测试
  - 来源：pytest --co
  - okx_client/ 下仅有 test_backtest.py，核心交易逻辑 (grid_bot.py, okx_trader.py) 无测试

- [ ] **测试覆盖不足 - orders 模块**：8 个文件，无单元测试
  - 来源：pytest --co
  - place_order_func.py, cancel_order_func.py, query_orders.py 等核心模块无测试

- [ ] **测试覆盖不足 - account 模块**：5 个文件，无单元测试
  - 来源：pytest --co
  - get_positions.py, get_account_summary.py, get_trades.py 等核心模块无测试

- [ ] **测试覆盖不足 - client 模块**：仅 2 个文件，无单元测试
  - 来源：pytest --co
  - ibkr_client.py, ib_connection.py 无测试

- [ ] **文档缺失 - 项目根目录无 README.md**
  - 来源：glob 检查
  - /Users/wang/.opencode/workspace/trading/README.md 不存在

- [ ] **文档缺失 - kanban/README.md 为空**
  - 来源：read 检查
  - /Users/wang/.opencode/workspace/trading/kanban/README.md 存在但内容为空

- [ ] **类型注解覆盖率低**：100 个 Python 文件
  - 来源：ruff check
  - account/, orders/, notify/, client/ 等核心模块大量缺失类型注解

- [ ] **z120_monitor 模块已废弃** - 目录仍存在，需清理
  - 来源：用户确认
  - z120_monitor/ 目录及相关代码需评估是否删除

## [P2] 常规

- [ ] **未使用的导入 (F401)**：大量
  - 来源：ruff check
  - account/__init__.py: 6处, orders/__init__.py: 6处, 各个模块的 unused imports
  - 建议：使用 `ruff check --fix` 自动清理

- [ ] **无用的 f-string (F541)**：多处
  - 来源：ruff check
  - account/get_trades_year.py:140, config/env_config.py:152, notify/feishu.py:123, orders/place_order.py:309/317/435 等
  - 建议：替换为普通字符串

- [ ] **未使用的局部变量 (F841)**：多处
  - 来源：ruff check
  - kanban/pages/2_market_scan.py:222 (has_scanner), kanban/pages/4_resonance.py:394 (level) 等
  - 建议：删除或合理使用

- [ ] **依赖版本不明确**
  - 来源：requirements.txt
  - kanban/requirements.txt 版本约束宽松 (>=)
  - 建议：锁定具体版本，避免依赖漂移

- [ ] **scripts/ 目录混乱**
  - 来源：glob 检查
  - 大量 debug/test 脚本堆积，如 apply_fix*.py, test_*.py 等
  - 建议：清理或归档

- [ ] **备份文件残留**
  - 来源：ls 检查
  - orders/place_order_func.py.bak 存在
  - 建议：删除或移至备份目录

## 统计摘要

| 检查项 | 数量 | 优先级 |
|--------|------|--------|
| F821 运行时错误 | 15 | P0 |
| F601 字典键重复 | 1 | P0 |
| E722 裸 except | 342 | P1 |
| E402 导入顺序 | 852 | P1 |
| F401 未使用导入 | ~100 | P2 |
| F541 无用 f-string | ~30 | P2 |
| F841 未使用变量 | ~15 | P2 |
| 测试缺失模块 | 4 | P1 |
| 文档缺失 | 2 | P1 |
| z120 废弃待清理 | 1 | P1 |
