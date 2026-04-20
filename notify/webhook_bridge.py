#!/usr/bin/env python3
"""
TradingView Webhook -> 飞书 中转服务
支持Webhook URL、飞书消息控制、命令执行、自然语言下单
"""

import os
import sys

# 首先应用 nest_asyncio patch（必须在导入 ib_insync 之前）
try:
    from ib_insync.util import patchAsyncio
    patchAsyncio()
except Exception:
    pass

import json
import subprocess
import time
import logging
import json
from pathlib import Path
from flask import Flask, request, jsonify
import requests
import yaml

# 添加配置路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)
from config import load_config, is_query_only, set_query_only, get_webhook_port, get_project_root
from client.ib_connection import get_ib_connection, get_ib_manager
from notify.nl_parser import parse_trading_command
from concurrent.futures import ThreadPoolExecutor
import threading
import sys

# Background executor for submitting orders without blocking HTTP request
_order_executor = ThreadPoolExecutor(max_workers=4)

def _submit_order_in_background(ib, symbol, action, quantity, exchange=None, sec_type=None, conId=None, close_position=False, outside_rth=None):
    """在后台提交订单，避免阻塞主线程。
    
    对于期货（FUT）默认启用 outsideRth=True，允许盘前/盘后交易。
    """
    # 期货默认启用盘前交易
    if outside_rth is None:
        outside_rth = True  # 默认启用，支持期货盘前订单
    def _order_job():
        try:
            from orders.place_order_func import place_order
            return place_order(ib, symbol, action, quantity, exchange=exchange, sec_type=sec_type, conId=conId, close_position=close_position, outside_rth=outside_rth)
        except Exception as e:
            print(f"[FEISHU] Background order error: {e}", file=sys.stderr)
            return {"error": str(e)}
    return _order_executor.submit(_order_job)


# ============ execDetails 回调 - 成交实时通知 ============
_fill_notified = set()  # 已通知的 execId，避免重复

def _on_exec_details(trade, fill):
    """IB 成交回调 - 通过飞书实时推送"""
    try:
        exec_id = fill.execution.execId
        if exec_id in _fill_notified:
            return
        _fill_notified.add(exec_id)

        contract = trade.contract
        symbol = getattr(contract, 'localSymbol', contract.symbol)
        side = fill.execution.side
        qty = fill.execution.shares
        price = fill.execution.price
        avg_price = fill.execution.avgPrice or price
        real_pnl = getattr(fill, 'commissionReport', None)
        commission = getattr(real_pnl, 'commission', 0) if real_pnl else 0

        msg = f"📈 成交回报\n{symbol} {side} {qty} @ ${avg_price:.2f}"
        if commission != 0:
            msg += f"\n手续费: ${abs(commission):.2f}"

        _debug(f"[FILL] {msg}")
        send_feishu(msg, FEISHU_CONVERSATION_ID)
    except Exception as e:
        _debug(f"[FILL] callback error: {e}")


def _register_fill_callback():
    """注册 execDetails 回调到 IB 实例"""
    try:
        ib = get_ib_connection()
        ib.execDetailsEvent.clear()  # 清除旧回调
        ib.execDetailsEvent += _on_exec_details
        _debug("[IB] execDetails callback registered")
        print(f"[IB] execDetails callback registered", flush=True)
    except Exception as e:
        _debug(f"[IB] execDetails register failed: {e}")


# 加载主配置
load_config()

# ============ 启动时预初始化 IB 连接 ============
# 必须在 app.run() 前建立，否则第一个请求会卡在 connect(timeout=10) 里
_ib_init_done = False
def _init_ib():
    global _ib_init_done
    if _ib_init_done:
        return
    try:
        ib = get_ib_connection()
        print(f"[IB] pre-connect: {ib}, connected={ib.isConnected()}")
        # 注册 execDetails 成交回调
        _register_fill_callback()
    except Exception as e:
        print(f"[IB] pre-connect failed (will retry on request): {e}")
    _ib_init_done = True

# 详细调试日志文件（写入 webhook_out.log）
_DEBUG_LOG = os.path.join(os.path.dirname(__file__), "webhook_out.log")
def _debug(msg):
    try:
        with open(_DEBUG_LOG, "a", encoding="utf-8") as f:
            import datetime
            f.write(f"[{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}\n")
        print(msg, flush=True)
    except Exception:
        pass  # 忽略打印错误

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)


def load_feishu_config():
    """从 settings.yaml 加载飞书配置"""
    from config import get_feishu_app_id, get_feishu_app_secret, get_feishu_chat_id, load_config, get
    
    load_config()
    return {
        "app_id": get_feishu_app_id(),
        "app_secret": get_feishu_app_secret(),
        "chat_id": get_feishu_chat_id(),
        "api_endpoint": get("feishu.api_endpoint", "https://open.feishu.cn/open-apis/im/v1/messages"),
        "auth_endpoint": get("feishu.auth_endpoint", "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"),
        "timeout": get("feishu.timeout", 30),
    }


feishu_config = load_feishu_config()
FEISHU_APP_ID = feishu_config.get("app_id", "")
FEISHU_APP_SECRET = feishu_config.get("app_secret", "")
FEISHU_CONVERSATION_ID = feishu_config.get("chat_id", "")

# 仅查询模式
QUERY_ONLY = is_query_only()

_token_cache = {"token": None, "expire": 0}
Z120_SCRIPT = str(Path(PROJECT_ROOT) / "z120_monitor" / "z120_scheduler.py")
Z120_PID_FILE = "/tmp/z120_monitor.pid"


def get_python_cmd():
    """获取 Python 命令（支持虚拟环境和 Windows）"""
    import sys
    try:
        from config.env_config import get_python_path
        return get_python_path()
    except ImportError:
        # Windows 使用 "python"，Unix 使用 "python3"
        return "python" if sys.platform == "win32" else "python3"


def get_z120_status():
    """获取 Z120 监控状态"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "z120_scheduler.py$"], capture_output=True, text=True
        )
        pids = [int(p) for p in result.stdout.strip().split("\n") if p]
        if pids:
            pid = pids[0]
            return f"✅ Z120 监控运行中 (PID: {pid})"
    except:
        pass

    return "🔴 Z120 监控未运行"


def start_z120_monitor():
    """启动 Z120 监控"""
    status = get_z120_status()
    if status.startswith("✅"):
        return "Z120 监控已在运行中"

    try:
        subprocess.Popen(
            [sys.executable, Z120_SCRIPT],
            stdout=open("/tmp/z120_monitor.log", "a"),
            stderr=open("/tmp/z120_monitor.err", "a"),
        )
        time.sleep(2)
        return f"🚀 Z120 监控已启动\n\n{get_z120_status()}"
    except Exception as e:
        return f"❌ 启动失败: {e}"


def stop_z120_monitor():
    """停止 Z120 监控"""
    stopped = False

    try:
        with open(Z120_PID_FILE) as f:
            pid = int(f.read().strip())
        os.kill(pid, 9)
        stopped = True
    except:
        pass

    try:
        result = subprocess.run(
            ["pkill", "-f", "z120_scheduler.py"], capture_output=True
        )
        if result.returncode == 0:
            stopped = True
    except:
        pass

    if stopped:
        return "🛑 Z120 监控已停止"
    return "Z120 监控未运行"


def get_monitor_status():
    """获取监控状态（快速版 - 使用多标缓存）"""
    import yaml

    z120_status = get_z120_status()

    pairs_path = Path(PROJECT_ROOT) / "z120_monitor" / "config" / "pairs.yaml"
    try:
        with open(pairs_path) as f:
            config = yaml.safe_load(f)
            enabled_pairs = [
                p["name"] for p in config.get("pairs", []) if p.get("enabled", False)
            ]
    except:
        enabled_pairs = ["MNQ_MYM"]

    mode = "🔒 仅查询模式" if QUERY_ONLY else "✅ 交易模式"

    status = f"""**📊 Z120 监控状态**

**监控进程:** {z120_status}

**模式:** {mode}

**启用的交易对:**"""
    for pair in enabled_pairs:
        status += f"\n  • {pair}"

    # 快速获取 Z120（从缓存，不调用 IBKR）
    try:
        sys.path.insert(0, PROJECT_ROOT)
        from z120_monitor.z120_cache import format_status_text, get_all_status

        all_data = get_all_status()
        if all_data:
            status += f"\n\n**当前状态:**\n{format_status_text()}"
        else:
            status += "\n\n**当前状态:** 暂无数据"
            status += "\n等待监控任务刷新..."
    except Exception as e:
        status += f"\n\n**当前状态:** 暂无数据 ({e})"

    return status


def get_tenant_token():
    """获取 tenant_access_token"""
    global _token_cache
    
    if _token_cache["token"] and time.time() < _token_cache["expire"]:
        return _token_cache["token"]
    
    url = feishu_config.get(
        "auth_endpoint",
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    )
    headers = {"Content-Type": "application/json; charset=utf-8"}
    payload = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        result = resp.json()
        if result.get("code") == 0:
            _token_cache["token"] = result["tenant_access_token"]
            _token_cache["expire"] = time.time() + result.get("expire", 7200) - 60
            return _token_cache["token"]
        else:
            print(f"获取 token 失败: {result}")
            return None
    except Exception as e:
        print(f"获取 token 错误: {e}")
        return None


def send_feishu(text, receive_id=None):
    """发送消息到飞书"""
    _debug(f"[FEISHU] send_feishu called: text={text[:50]}..., receive_id={receive_id}")
    try:
        token = get_tenant_token()
        _debug(f"[FEISHU] Token result: {token}")
        if not token:
            print("[FEISHU] Error: No token available")
            return (False, "No token")

        target_id = receive_id or FEISHU_CONVERSATION_ID
        _debug(f"[FEISHU] target_id: {target_id}")
        if not target_id:
            print("[FEISHU] Error: No target_id available")
            return (False, "No target_id")

        url = feishu_config.get(
            "api_endpoint", "https://open.feishu.cn/open-apis/im/v1/messages"
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        params = {"receive_id_type": "chat_id"}
        message = {
            "receive_id": target_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}),
        }

        resp = requests.post(
            url, params=params, json=message, headers=headers, timeout=10
        )
        _debug(f"[FEISHU] Response: {resp.status_code}")
        if resp.status_code == 200:
            return (True, resp.text)
        else:
            return (False, f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        import traceback
        _debug(f"[FEISHU] Exception: {e}")
        traceback.print_exc()
        return (False, str(e))


def execute_command(cmd):
    """执行命令并返回结果（Windows UTF-8 兼容）"""
    try:
        import sys
        # Windows 需要特殊处理编码
        if sys.platform == "win32":
            import subprocess
            result = subprocess.run(
                cmd, shell=True, capture_output=True, timeout=30, cwd=get_project_root()
            )
            # 手动解码，避免 GBK 错误
            stdout = result.stdout.decode('utf-8', errors='replace') if result.stdout else ""
            stderr = result.stderr.decode('utf-8', errors='replace') if result.stderr else ""
            return stdout + stderr
        else:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30, cwd=get_project_root()
            )
            return result.stdout + result.stderr
    except Exception as e:
        return str(e)


def _get_ib():
    """获取 IB 连接，未连接时返回 None"""
    ib = get_ib_connection()
    if ib is None or not ib.isConnected():
        return None
    return ib


def _run_ib(fn, timeout=15.0):
    """在 IB 线程中执行函数（通过 run_sync 队列）"""
    manager = get_ib_manager()
    return manager.run_sync(fn, timeout=timeout)


def get_positions_formatted():
    """获取格式化持仓"""
    try:
        ib = _get_ib()
        if ib is None:
            return "❌ IB 未连接"
        # positions 是缓存数据，可以直接读取
        positions = ib.positions()
        if not positions:
            return "📊 当前无持仓"
        lines = ["**📊 当前持仓**\n"]
        for pos in positions:
            symbol = pos.contract.symbol
            sec_type = pos.contract.secType
            position = pos.position
            avg_cost = pos.avgCost
            if position == 0:
                continue
            pos_str = f"{position:+.0f}" if position != int(position) else f"{int(position):+}"
            cost_str = f"{avg_cost:.2f}" if avg_cost else "N/A"
            lines.append(f"• {symbol} ({sec_type}): {pos_str} @ {cost_str}")
        if len(lines) == 1:
            return "📊 当前无持仓"
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 获取持仓失败: {e}"


def get_account_summary_formatted():
    """获取格式化账户摘要（通过 run_sync 在 IB 线程执行）"""
    try:
        ib = _get_ib()
        if ib is None:
            return "❌ IB 未连接"
        summary = _run_ib(lambda: ib.accountSummary(), timeout=15)
        if not summary:
            return "📊 无账户数据"
        key_tags = {
            "NetLiquidation": "净值",
            "UnrealizedPnL": "未实现盈亏",
            "RealizedPnL": "已实现盈亏",
            "AvailableFunds": "可用资金",
            "BuyingPower": "购买力",
            "TotalCashValue": "现金",
            "GrossPositionValue": "持仓市值",
            "MaintMarginReq": "维持保证金",
        }
        lines = ["**💰 账户摘要**\n"]
        tag_map = {}
        for item in summary:
            tag_map[item.tag] = item
        for tag, label in key_tags.items():
            if tag in tag_map:
                val = tag_map[tag].value
                currency = tag_map[tag].currency
                try:
                    num = float(val)
                    lines.append(f"• {label}: {num:,.2f} {currency}")
                except (ValueError, TypeError):
                    lines.append(f"• {label}: {val} {currency}")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 获取账户摘要失败: {e}"


def get_orders_formatted():
    """获取格式化订单列表（通过 run_sync 在 IB 线程执行）"""
    try:
        ib = _get_ib()
        if ib is None:
            return "❌ IB 未连接"
        trades = _run_ib(lambda: ib.trades(), timeout=10)
        if not trades:
            return "📋 当前无订单"
        pending, filled, cancelled, inactive = [], [], [], []
        for trade in trades:
            os = trade.orderStatus
            c = trade.contract
            order_info = {
                "orderId": trade.order.orderId,
                "symbol": c.localSymbol if hasattr(c, "localSymbol") and c.localSymbol else c.symbol,
                "action": trade.order.action,
                "quantity": trade.order.totalQuantity,
                "filled": os.filled,
                "remaining": os.remaining,
                "avgFillPrice": os.avgFillPrice,
                "status": os.status,
            }
            if os.status in {"Submitted", "PendingSubmit", "PreSubmitted", "Active", "ApiPending"}:
                pending.append(order_info)
            elif os.status in {"Filled", "ApiTraded"}:
                filled.append(order_info)
            elif os.status in {"Cancelled", "ApiCancelled"}:
                cancelled.append(order_info)
            else:
                inactive.append(order_info)
        lines = ["**📋 订单状态**\n"]
        if pending:
            lines.append(f"🔄 待成交 ({len(pending)} 单)")
            for o in pending:
                lines.append(f"  • {o['symbol']}: {o['action']} {o['filled']:.0f}/{o['quantity']} ({o['status']})")
        if filled:
            lines.append(f"\n✅ 已成交 ({len(filled)} 单)")
            for o in filled:
                lines.append(f"  • {o['symbol']}: {o['action']} {o['filled']:.0f}/{o['quantity']} @ ${o['avgFillPrice']:.2f}")
        if cancelled:
            lines.append(f"\n❌ 已取消 ({len(cancelled)} 单)")
            for o in cancelled:
                lines.append(f"  • {o['symbol']}: {o['action']} {o['quantity']}")
        if inactive:
            lines.append(f"\n⏸ 未激活 ({len(inactive)} 单)")
            for o in inactive:
                lines.append(f"  • {o['symbol']}: {o['action']} {o['quantity']} ({o['status']})")
        if len(lines) == 1:
            return "📋 当前无订单"
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 获取订单失败: {e}"


def get_fills_formatted():
    """获取格式化成交记录（通过 run_sync 在 IB 线程执行）"""
    try:
        ib = _get_ib()
        if ib is None:
            return "❌ IB 未连接"
        fills = _run_ib(lambda: ib.fills(), timeout=10)
        if not fills:
            return "📊 今日无成交"
        lines = ["**📊 成交记录**\n"]
        for fill in fills:
            symbol = fill.contract.symbol
            action = fill.execution.side
            qty = fill.execution.cumQty
            price = fill.execution.price
            commission = fill.commissionReport.commission if fill.commissionReport else 0
            exec_time = fill.execution.time.strftime("%H:%M:%S") if fill.execution.time else ""
            lines.append(f"• {symbol}: {action} {qty} @ ${price:.2f} (手续费 ${commission:.2f}) {exec_time}")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 获取成交记录失败: {e}"


def get_help_text():
    """获取帮助文本"""
    return """**📊 交易系统命令列表**

**查询类:**
• /持仓 - 查询当前持仓
• /账户 - 查询账户摘要
• /订单 - 查询活动订单
• /成交 - 查询成交记录

**监控类:**
• /status - 查看监控状态
• /refresh - 刷新监控数据
• /start - 启动监控
• /stop - 停止监控
• /log - 查看日志

**模式切换:**
• /交易模式 - 切换到交易模式
• /查询模式 - 切换到仅查询模式

**分析类:**
• /多周期分析 - 执行多周期共振分析（默认DOGEUSDT）
• /多周期分析 BTCUSDT - 指定品种

**帮助:**
• /help - 显示此帮助"""


def trigger_refresh():
    """触发监控刷新，完成后主动发送飞书反馈"""
    import threading
    import subprocess

    def do_refresh():
        try:
            python_cmd = get_python_cmd()
            refresh_script = str(Path(__file__).parent / "refresh_and_notify.py")
            result = subprocess.run(
                [
                    python_cmd,
                    refresh_script,
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )
            print(f"刷新结果: {result.stdout}{result.stderr}")
        except Exception as e:
            print(f"刷新出错: {e}")

    threading.Thread(target=do_refresh, daemon=True).start()
    return "🔄 监控刷新中，请稍候..."


def run_multi_timeframe_analysis(symbol: str = "DOGE-USDT") -> str:
    """运行多周期共振分析"""
    try:
        sys.path.insert(0, PROJECT_ROOT)
        from quant_core.sources import create_datasource
        
        _debug(f"[MTF] Starting analysis for {symbol}")
        
        okx = create_datasource("okx")
        
        timeframes = [
            ("1h", "1H", 50),
            ("4h", "4H", 50),
            ("1D", "1D", 30),
            ("1W", "1W", 20),
        ]
        
        results = []
        for tf_name, tf_bar, tf_num in timeframes:
            try:
                _debug(f"[MTF] Fetching {tf_name}...")
                bars = okx.get_history(symbol, bar_size=tf_bar, num=tf_num)
                
                if not bars:
                    results.append(f"  {tf_name}: 无数据")
                    continue
                
                closes = [b.close for b in bars]
                current_price = closes[-1]
                
                rsi = calculate_rsi(closes)
                ma20 = calculate_ma(closes, 20) if len(closes) >= 20 else None
                ma50 = calculate_ma(closes, 50) if len(closes) >= 50 else None
                
                if ma20 and current_price > ma20:
                    ma_signal = "BUY"
                elif ma20 and current_price < ma20:
                    ma_signal = "SELL"
                else:
                    ma_signal = "NEUTRAL"
                
                if rsi < 30:
                    osc_signal = "BUY"
                elif rsi > 70:
                    osc_signal = "SELL"
                else:
                    osc_signal = "NEUTRAL"
                
                results.append(f"  {tf_name}: RSI={rsi:.1f} MA={ma_signal} OSC={osc_signal}")
            except Exception as e:
                _debug(f"[MTF] Error {tf_name}: {e}")
                results.append(f"  {tf_name}: 获取失败 - {str(e)[:30]}")
        
        if not results:
            return f"无法获取 {symbol} 的数据，请检查品种代码"
        
        buy_count = sum(1 for r in results if "BUY" in r)
        sell_count = sum(1 for r in results if "SELL" in r)
        total = len(timeframes)
        resonance = int((max(buy_count, sell_count) / total) * 100) if total > 0 else 0
        
        level = "强共振" if buy_count > sell_count and buy_count >= 3 else "强分歧" if sell_count > buy_count and sell_count >= 3 else "分歧"
        
        return f"""**{symbol} 多周期共振分析**

{chr(10).join(results)}

**共振评分:** {resonance}/100 ({level})"""
    except Exception as e:
        _debug(f"[MTF] Final error: {e}")
        return f"分析失败: {str(e)}"


def calculate_rsi(prices: list, period: int = 14) -> float:
    """计算 RSI"""
    if len(prices) < period + 1:
        return 50.0
    
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_ma(prices: list, period: int) -> float:
    """计算移动平均"""
    if len(prices) < period:
        return 0.0
    return sum(prices[-period:]) / period


COMMANDS = {
    # 监控类
    "status": lambda: get_monitor_status(),
    "refresh": trigger_refresh,
    "start": lambda: start_z120_monitor(),
    "stop": lambda: stop_z120_monitor(),
    "log": lambda: execute_command(
        "tail -30 /tmp/z120_monitor.log 2>/dev/null || echo 'No log'"
    ),
    # 模式切换
    "交易模式": lambda: (
        set_query_only(False) or globals().__setitem__("QUERY_ONLY", False),
        "✅ **已切换到交易模式**\n\n现在允许查询和下单操作。",
    )[1],
    "查询模式": lambda: (
        set_query_only(True) or globals().__setitem__("QUERY_ONLY", True),
        "🔒 **已切换到仅查询模式**\n\n现在仅允许查询操作，不允许下单。",
    )[1],
    # 查询类（内联，复用 webhook IB 连接）
    "持仓": lambda: get_positions_formatted(),
    "账户": lambda: get_account_summary_formatted(),
    "订单": lambda: get_orders_formatted(),
    "成交": lambda: get_fills_formatted(),
    "help": lambda: get_help_text(),
    # 多周期分析
    "多周期分析": lambda: run_multi_timeframe_analysis(),
}


@app.route("/tv-webhook", methods=["POST"])
def tv_webhook():
    """接收Webhook（任意来源，支持 TradingView 自动交易）"""
    try:
        data = request.json
        print(f"收到Webhook数据:")
        print(json.dumps(data, indent=2, ensure_ascii=False))

        # 检查是否是交易信号（包含 symbol, action）
        symbol = data.get("symbol", "").upper()
        action = data.get("action", "").upper()

        if symbol and action in ("BUY", "SELL", "CLOSE"):
            # 自动交易模式
            quantity = data.get("quantity", 1)
            order_type = data.get("order_type", "MKT")
            sec_type = data.get("sec_type", "FUT")
            exchange = data.get("exchange", "COMEX")
            use_main_contract = data.get("use_main_contract", True)
            limit_price = data.get("limit_price")

            # 复用 IB 连接直接下单，避免 subprocess 创建新连接导致 clientId 冲突
            try:
                from orders.exchange_mapper import get_exchange_for_symbol
                exchange = get_exchange_for_symbol(symbol, "FUT") if sec_type == "FUT" else ""
            except Exception:
                exchange = ""
            
            try:
                from client.ib_connection import get_ib_connection
                from orders.place_order_func import place_order

                ib = get_ib_connection()
                if ib is None or not ib.isConnected():
                    output = "IB 连接失败或已断开"
                else:
                    # 期货默认启用 outside_rth，支持盘前/盘后交易
                    future = _submit_order_in_background(
                        ib, symbol, action, quantity,
                        exchange=exchange,
                        sec_type=sec_type,
                        close_position=(action == "CLOSE"),
                        outside_rth=True
                    )
                    output = {"status": "Submitted", "message": f"后台已提交下单: {symbol} {action} {quantity}"}
                    # Feishu 提示提交状态 (不指定 chat_id，使用默认)
                    _ = send_feishu(f"✅ 订单已提交: {symbol} {action} {quantity}")
            except Exception as e:
                output = f"错误: {e}"

            # 发送交易结果到飞书
            output_str = str(output)[:500] if output else ""
            msg = f"🤖 Webhook 交易信号\n\n标的: {symbol}\n操作: {action}\n数量: {quantity}\n订单类型: {order_type}\n\n结果:\n{output_str}"
            send_feishu(msg)

            order_payload = output if isinstance(output, dict) else {"status": "Unknown", "order": str(output)}
            return jsonify({"status": "ok", "order": order_payload})
        else:
            # 仅通知模式
            title = data.get("title", "Webhook 警报")
            description = data.get("description", "")
            success, result = send_feishu(f"{title}\n\n{description}")
            return jsonify({"status": "ok" if success else "error", "result": result})

    except Exception as e:
        print(f"Webhook错误: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/feishu-webhook", methods=["GET", "POST"])
def feishu_webhook():
    """接收飞书消息并执行命令"""
    logger.info(f"[FEISHU] Method: {request.method}")
    logger.info(f"[FEISHU] Headers: {dict(request.headers)}")
    logger.info(f"[FEISHU] Data: {request.data}")

    if request.method == "GET":
        challenge = request.args.get("challenge", request.args.get("chu") or "")
        logger.info(f"[FEISHU] GET challenge: {challenge}")
        return jsonify({"challenge": challenge})

    try:
        order_result = None  # 捕获订单结果用于 HTTP 响应
        event = request.json
        logger.info(f"[FEISHU] Event: {json.dumps(event, ensure_ascii=False)}")

        if event.get("type") == "url_verification" or event.get("challenge"):
            challenge = event.get("challenge", "")
            logger.info(f"[FEISHU] URL verification challenge: {challenge}")
            return jsonify({"challenge": challenge})

        msg_type = event.get("header", {}).get("event_type", "")
        logger.info(f"[FEISHU] Event type: {msg_type}")
        logger.info(f"[FEISHU] Full event: {json.dumps(event, ensure_ascii=False)}")

        if msg_type == "im.message.receive_v1":
            # Schema 2.0: message is in event.message.content
            # Schema 1.0: message is in body.message.content
            event_data = event.get("event", event.get("body", {}))
            message = event_data.get("message", {})

            # 去重：检查 message_id
            msg_id = message.get("message_id", "")
            if msg_id:
                cache_key = f"feishu_msg_{msg_id}"
                import time
                current_time = int(time.time())
                if not hasattr(feishu_webhook, "_msg_cache"):
                    feishu_webhook._msg_cache = {}
                # 5秒内重复消息跳过
                if cache_key in feishu_webhook._msg_cache:
                    if current_time - feishu_webhook._msg_cache[cache_key] < 5:
                        logger.info(f"[FEISHU] Duplicate message: {msg_id}, skip")
                        return jsonify({"status": "ok", "order": order_result}), 200
                feishu_webhook._msg_cache[cache_key] = current_time
            
            logger.info(f"[FEISHU] Message: {json.dumps(message, ensure_ascii=False)}")

            content_raw = message.get("content", "{}")
            logger.info(f"[FEISHU] Content raw: {content_raw}")

            try:
                content = json.loads(content_raw)
                text = content.get("text", "").strip()
            except Exception as parse_err:
                logger.info(f"[FEISHU] Content parse error: {parse_err}")
                text = ""

            logger.info(f"[FEISHU] Message text: '{text}'")

            # 获取 chat_id 用于回复
            chat_id = message.get("chat_id", FEISHU_CONVERSATION_ID)
            logger.info(f"[FEISHU] Will reply to: {chat_id}")

            # 检查是否以 / 开头（命令模式）
            if text.startswith("/"):
                cmd_name = text[1:].strip()
                _debug(f"[FEISHU] CMD: {cmd_name}")
                logger.info(f"[FEISHU] Command: {cmd_name}")

                # 分离命令和参数
                parts = cmd_name.split(None, 1)
                cmd_base = parts[0]
                cmd_args = parts[1] if len(parts) > 1 else ""

                # 尝试找到匹配的命令（忽略大小写）
                matched_cmd = None
                for cmd in COMMANDS:
                    if cmd.lower() == cmd_base.lower():
                        matched_cmd = cmd
                        break

                if matched_cmd:
                    logger.info(f"[FEISHU] matched_cmd={matched_cmd}")
                    # 支持带参数的命令
                    if matched_cmd == "多周期分析" and cmd_args:
                        logger.info(f"[FEISHU] 调用多周期分析 with args: {cmd_args}")
                        output = run_multi_timeframe_analysis(cmd_args.strip().upper())
                    elif matched_cmd == "多周期分析":
                        logger.info(f"[FEISHU] 调用多周期分析 default")
                        output = run_multi_timeframe_analysis()
                    else:
                        output = COMMANDS[matched_cmd]()
                    logger.info(f"[FEISHU] Command output: {output}")
                    success, resp = send_feishu(f"**{cmd_name}**\n\n{output}", chat_id)
                    logger.info(f"[FEISHU] Send result: {success}")
                else:
                    send_feishu(
                        f"未知命令: {cmd_name}\n\n发送 `/help` 查看可用命令", chat_id
                    )
            else:
                # 自然语言模式 - 先检查是否在命令中（忽略大小写）
                cmd_key = text.strip()
                cmd_key_lower = cmd_key.lower()

                # 尝试找到匹配的命令（忽略大小写）
                matched_cmd = None
                for cmd in COMMANDS:
                    if cmd.lower() == cmd_key_lower:
                        matched_cmd = cmd
                        break

                if matched_cmd:
                    logger.info(f"[FEISHU] Found command: {cmd_key} -> {matched_cmd}")
                    output = COMMANDS[matched_cmd]()
                    success, resp = send_feishu(f"**{cmd_key}**\n\n{output}", chat_id)
                else:
                    parsed = parse_trading_command(text)
                    action = parsed.get('action')
                    symbol = parsed.get('symbol')
                    quantity = parsed.get('quantity', 1)
                    sec_type = parsed.get('sec_type')  # 外汇为 CASH, 黄金为 CFD
                    parsed_exchange = parsed.get('exchange')  # 交易所
                    cfd_symbol = parsed.get('cfd_symbol')  # CFD 实际符号
                    cfd_conId = parsed.get('cfd_conId')  # CFD 合约ID
                    
                    if quantity is None:
                        quantity = 1
                    
                    if action and action != 'UNKNOWN':
                        try:
                            logger.info(f"[FEISHU] NL parsed: action={action}, symbol={symbol}, qty={quantity}, sec_type={sec_type}")
                            
                            # 复用 IB 连接，直接调用 place_order_func.place_order
                            # 添加事件循环，避免 ib_insync 内部错误
                            import asyncio
                            import sys
                            import traceback as tb_module
                            
                            # 应用 nest_asyncio 允许嵌套事件循环（修复 ib_insync 在子线程中的问题）
                            try:
                                import nest_asyncio
                                nest_asyncio.apply()
                            except ImportError:
                                pass
                            
                            from client.ib_connection import get_ib_connection
                            from orders.place_order_func import place_order
                            from orders.exchange_mapper import get_exchange_for_symbol
                            
                            _debug(f"[FEISHU] get_ib_connection() calling...", )
                            ib = get_ib_connection()
                            _debug(f"[FEISHU] get_ib_connection() returned ib={ib}, connected={ib.isConnected() if ib else None}", )
                            
                            if ib is None or not ib.isConnected():
                                error_msg = "IB 连接失败或已断开"
                                _debug(f"[FEISHU] {error_msg}", )
                                send_feishu(f"❌ 下单失败: {error_msg}\n请检查 IB Gateway", chat_id)
                            else:
                                # 使用解析出的交易所，或根据品种类型推断
                                if parsed_exchange:
                                    exchange = parsed_exchange
                                elif sec_type:
                                    exchange = get_exchange_for_symbol(symbol, sec_type)
                                else:
                                    exchange = get_exchange_for_symbol(symbol, "FUT")
                                is_close = (action == "CLOSE")
                                
                                # CFD 使用实际符号
                                actual_symbol = cfd_symbol if cfd_symbol else symbol
                                actual_conId = cfd_conId if cfd_conId else None
                                
                                _debug(f"[FEISHU] Calling place_order: symbol={actual_symbol}, action={action}, qty={quantity}, sec_type={sec_type}, exchange={exchange}, conId={actual_conId}, close_position={is_close}")
                                
                                # 使用后台提交，避免阻塞
                                future = _submit_order_in_background(ib, actual_symbol, action, quantity, exchange=exchange, sec_type=sec_type, conId=actual_conId, close_position=is_close)
                                order_result = {"status": "Submitted", "symbol": symbol, "action": action, "quantity": quantity, "exchange": exchange}
                                fs_result = send_feishu(f"✅ 订单已提交: {symbol} {action} {quantity}", chat_id)
                        except Exception as e:
                            err_str = tb_module.format_exc()
                            _debug(f"[FEISHU] IB/connect EXCEPTION: {type(e).__name__}: {e}\n{err_str}", )
                            order_result = {"error": f"{type(e).__name__}: {e}"}
                    else:
                        send_feishu(get_help_text(), chat_id)

        return jsonify({"status": "ok", "order": order_result}), 200
    except Exception as e:
        logger.info(f"[FEISHU] Error: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/test-api", methods=["POST"])
def test_api():
    """测试API方式"""
    success, result = send_feishu("🧪 测试消息")
    return jsonify({"success": success, "result": result})


@app.route("/positions", methods=["GET"])
def get_positions_endpoint():
    """Get current positions"""
    try:
        from client.ib_connection import get_ib_manager
        manager = get_ib_manager()
        ib = manager.get_connection()
        positions = manager.run_sync(lambda: ib.positions(), timeout=10)
        result = []
        for p in positions:
            result.append({
                "symbol": p.contract.symbol,
                "position": p.position,
                "avgCost": p.avgCost,
                "account": p.account,
                "contract": str(p.contract),
            })
        return jsonify({"positions": result, "count": len(result)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/orders", methods=["GET"])
def get_orders_endpoint():
    """Get open orders"""
    try:
        from client.ib_connection import get_ib_manager
        manager = get_ib_manager()
        ib = manager.get_connection()
        trades = manager.run_sync(lambda: ib.openTrades(), timeout=10)
        result = []
        for t in trades:
            result.append({
                "orderId": t.order.orderId,
                "symbol": t.contract.symbol,
                "action": t.order.action,
                "quantity": t.order.totalQuantity,
                "status": t.orderStatus.status,
                "filled": t.orderStatus.filled,
            })
        return jsonify({"orders": result, "count": len(result)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    config_status = {
        "app_id": bool(FEISHU_APP_ID),
        "conversation_id": bool(FEISHU_CONVERSATION_ID),
        "query_only": QUERY_ONLY,
    }
    return jsonify({"status": "ok", "config": config_status})


@app.route("/test-mtf", methods=["POST"])
def test_mtf():
    try:
        text = request.json.get("text", "/多周期分析")
        if text.startswith("/多周期分析"):
            cmd = text[1:].strip()
            if cmd == "多周期分析":
                symbol = "DOGE-USDT"
            else:
                symbol = cmd.strip().upper()
            result = run_multi_timeframe_analysis(symbol)
            return jsonify({"status": "ok", "result": result})
        return jsonify({"status": "error", "message": "invalid command"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    # Fix Windows GBK encoding for emoji
    import sys
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    port = int(sys.argv[1]) if len(sys.argv) > 1 else get_webhook_port()

    print("=" * 60)
    print("[START] TradingView -> Feishu Bridge")
    print("=" * 60)
    print(f"Address: http://0.0.0.0:{port}")

    # 启动时预初始化 IB（后台线程，避免阻塞 Flask）
    import threading
    def _bg_connect():
        try:
            ib = get_ib_connection()
            print(f"[IB] pre-connect result: connected={ib.isConnected() if ib else False}")
            # 注册 execDetails 成交回调
            _register_fill_callback()
        except Exception as e:
            print(f"[IB] pre-connect failed: {e}")
    t = threading.Thread(target=_bg_connect, daemon=True)
    t.start()
    # 不等待，让 Flask 立即启动，IB 在后台连接
    print("[IB] 连接已在后台启动...")

    print()
    print(f"Mode: {'Query Only' if QUERY_ONLY else 'Trading'}")

    # 自动检查并启动 Z120 监控
    z120_running = get_z120_status()
    if z120_running.startswith("✅"):
        print(f"📊 Z120 监控: 已运行")
    else:
        print("📊 Z120 监控: 自动启动...")
        start_result = start_z120_monitor()
        print(f"      {start_result}")

    print()
    print("端点:")
    print(f"  Webhook: http://localhost:{port}/webhook")
    print(f"  飞书控制: POST /feishu-webhook")
    print(f"  测试: POST /test-api")
    print(f"  健康检查: GET /health")
    print()
    print("命令 (在飞书群发送):")
    print("  /持仓 - 查询持仓")
    print("  /账户 - 查询账户")
    print("  /订单 - 查询订单")
    print("  /成交 - 查询成交")
    print("  /status - 查看监控状态")
    print("  /help - 显示帮助")
    print("=" * 60)

    app.run(host="0.0.0.0", port=port, threaded=True)
