# Webhook SPEC

## Scope
TradingView/飞书 → IBKR 执行桥接服务

## Endpoints
| Endpoint | Method | 说明 |
|----------|--------|------|
| `/tv-webhook` | POST | TradingView 信号 |
| `/feishu-webhook` | POST | 飞书命令 |
| `/health` | GET | 健康检查 |

## 核心功能
- NL 命令解析: 买入/卖出/平仓/查询
- 后台异步下单 (ThreadPoolExecutor)
- 成交实时推送飞书
- execDetails 回调

## 支持品种
| 类型 | sec_type | 交易所 | 示例 |
|------|----------|--------|------|
| 期货 | FUT | COMEX/CME | GC, MGC, NQ |
| 外汇 | CASH | IDEALPRO | USDJPY, EURUSD |
| 商品 | CMDTY | SMART | XAUUSD, XAGUSD |
| CFD | CFD | SMART | GOLD CFD |
| 加密 | CRYPTO | PAXOS | BTC |

## Tech Stack
- Flask (port 5002)
- ib_insync
- concurrent.futures

## 关键文件
- `notify/webhook_bridge.py` - 主服务
- `notify/nl_parser.py` - 命令解析
- `orders/place_order_func.py` - 下单逻辑
- `client/ib_connection.py` - IB 连接