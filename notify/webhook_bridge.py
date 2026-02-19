#!/usr/bin/env python3
"""
TradingView Webhook -> 飞书 中转服务
支持Webhook URL、飞书消息控制、命令执行、自然语言下单
"""

import os
import sys
import json
import subprocess
import time
import logging
import re
from pathlib import Path
from flask import Flask, request, jsonify
import requests
import yaml

# 添加配置路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)
from config import load_config, is_query_only, set_query_only, get_webhook_port, get_project_root

# 加载主配置
load_config()

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


def get_mode_text():
    """获取当前模式状态"""
    if QUERY_ONLY:
        return "🔒 **当前模式：仅查询模式**\n\n仅允许查询操作，不允许下单。"
    else:
        return "✅ **当前模式：交易模式**\n\n允许查询和下单操作。"


_token_cache = {"token": None, "expire": 0}
Z120_SCRIPT = str(Path(PROJECT_ROOT) / "z120_monitor" / "z120_scheduler.py")
Z120_PID_FILE = "/tmp/z120_monitor.pid"


def get_python_cmd():
    """获取 Python 命令（支持虚拟环境）"""
    try:
        from config.env_config import get_python_path
        return get_python_path()
    except ImportError:
        return "python3"


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
    headers = {"Content-Type": "application/json"}
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}

    try:
        resp = requests.post(url, json=data, headers=headers, timeout=10)
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
    token = get_tenant_token()
    if not token:
        return False, "No token"

    target_id = receive_id or FEISHU_CONVERSATION_ID

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

    try:
        resp = requests.post(
            url, params=params, json=message, headers=headers, timeout=10
        )
        if resp.status_code == 200:
            return True, resp.text
        else:
            return False, f"Status {resp.status_code}: {resp.text}"
    except Exception as e:
        return False, str(e)


def execute_command(cmd):
    """执行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30, cwd=get_project_root()
        )
        return result.stdout + result.stderr
    except Exception as e:
        return str(e)


def parse_natural_language_orders(text):
    """解析自然语言订单"""
    text_lower = text.lower()

    # 检查是否是已知的查询命令（这些不应该被解析为订单）
    query_commands = ["mnqmyM", "mnqmym", "mnq_mym", "价差", "spread"]
    for cmd in query_commands:
        if cmd.lower() in text_lower:
            return None, None

    # 检测动作
    if "买入" in text_lower or "买" in text_lower or "buy" in text_lower:
        action = "BUY"
    elif "卖出" in text_lower or "卖" in text_lower or "sell" in text_lower:
        action = "SELL"
    elif "平仓" in text_lower or "平掉" in text_lower or "close" in text_lower:
        action = "CLOSE"
    else:
        return None, "未检测到买卖动作"

    # 检测数量
    quantity = 1
    numbers = re.findall(r"(\d+)", text)
    if numbers:
        quantity = int(numbers[0])

    # 检测品种
    symbol = None
    symbols = {
        "aapl": "AAPL",
        "苹果": "AAPL",
        "tsla": "TSLA",
        "特斯拉": "TSLA",
        "gc": "GC",
        "黄金": "GC",
        "gold": "GC",
        "mgc": "MGC",
        "微型黄金": "MGC",
        "btc": "BTC",
        "比特币": "BTC",
        "bitcoin": "BTC",
        "eth": "ETH",
        "以太坊": "ETH",
        "ethereum": "ETH",
        "myna": "Myna",
        "myna": "Myna",
        "mnq": "MNQ",
        "迷你纳斯达克": "MNQ",
        "迷你那指": "MNQ",
        "mym": "MYM",
        "迷你道琼斯": "MYM",
        "siv": "SIV",
        "澳洲200": "SIV",
        "hsi": "HSI",
        "恒生指数": "HSI",
        "nk": "NK",
        "日经指数": "NK",
        "xagusd": "XAGUSD",
    }

    for key, value in symbols.items():
        if key in text_lower:
            symbol = value
            break

    if not symbol:
        return None, "未识别到交易品种"

    # 检测订单类型
    if "限价" in text_lower or "lmt" in text_lower:
        order_type = "LMT"
        price_match = re.search(r"[限价|LMT|price][:：]?\s*(\d+\.?\d*)", text_lower)
        limit_price = price_match.group(1) if price_match else None
    else:
        order_type = "MKT"
        limit_price = None

    # 判断证券类型
    futures = {"GC", "MGC", "MNQ", "MYM", "MES", "ES", "NQ", "YM", "CL", "NG", "ZB", "ZN", "ZF", "6E", "6J", "6B", "6A", "SI", "PL", "PA", "HG", "ZC", "ZS", "ZW", "HE", "LE", "GF", "MHI", "MBT"}
    if symbol == "XAGUSD":
        sec_type = "CMDTY"
    elif symbol in futures:
        sec_type = "FUT"
    else:
        sec_type = "STK"

    # 构建命令
    python_cmd = get_python_cmd()
    orders_script = str(Path(PROJECT_ROOT) / "orders" / "place_order.py")
    if action == "CLOSE":
        cmd = f"{python_cmd} {orders_script} --symbol {symbol} --sec_type {sec_type} --close_position --order_type {order_type}"
    else:
        if limit_price:
            cmd = f"{python_cmd} {orders_script} --symbol {symbol} --sec_type {sec_type} --action {action} --quantity {quantity} --order_type {order_type} --limit_price {limit_price}"
        else:
            cmd = f"{python_cmd} {orders_script} --symbol {symbol} --sec_type {sec_type} --action {action} --quantity {quantity} --order_type {order_type}"

    return cmd, f"{action} {quantity} {symbol} @ {order_type}" + (
        f" ${limit_price}" if limit_price else ""
    )


def get_help_text():
    """获取帮助文本"""
    if QUERY_ONLY:
        return """🔒 **仅查询模式**

**可用命令：**

**监控类:**
• /status - 查看监控状态
• /refresh - 立即刷新监控数据
• /log - 查看日志

**模式切换：**
• /交易模式 - 切换到交易模式（允许下单）
• /查询模式 - 切换到仅查询模式

**帮助：**
• /help - 显示帮助"""
    else:
        return """✅ **交易模式**

**查询类 (/命令 或 发文字):**
• /持仓 或发「持仓」
• /账户 或发「账户」

**模式切换：**
• /交易模式 - 切换到交易模式
• /查询模式 - 切换到仅查询模式

**监控类:**
• /status - 查看监控状态
• /refresh - 立即刷新监控数据
• /start - 启动监控
• /stop - 停止监控
• /log - 查看日志

**下单示例 (直接发文字):**
• 「买入100股AAPL」
• 「买入1手微型黄金」
• 「卖出全部TSLA」
• 「平掉MGC持仓」
• 「限价买入BTC 210000」

**帮助:**
• /help 或发「帮助」"""


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


COMMANDS = {
    "status": lambda: get_monitor_status(),
    "refresh": trigger_refresh,
    "start": lambda: start_z120_monitor(),
    "stop": lambda: stop_z120_monitor(),
    "log": lambda: execute_command(
        "tail -30 /tmp/z120_monitor.log 2>/dev/null || echo 'No log'"
    ),
    # 模式切换命令
    "交易模式": lambda: (
        set_query_only(False) or globals().__setitem__("QUERY_ONLY", False),
        "✅ **已切换到交易模式**\n\n现在允许查询和下单操作。",
    )[1],
    "查询模式": lambda: (
        set_query_only(True) or globals().__setitem__("QUERY_ONLY", True),
        "🔒 **已切换到仅查询模式**\n\n现在仅允许查询操作，不允许下单。",
    )[1],
    # IBKR commands
    "持仓": lambda: execute_command(
        f"{get_python_cmd()} {Path(PROJECT_ROOT) / 'account' / 'get_positions.py'}"
    ),
    "账户": lambda: execute_command(
        f"{get_python_cmd()} {Path(PROJECT_ROOT) / 'account' / 'get_account_summary.py'}"
    ),
    "help": lambda: get_help_text(),
}


@app.route("/webhook", methods=["POST"])
def webhook():
    """接收TradingView Webhook"""
    try:
        data = request.json
        print(f"收到TradingView数据:")
        print(json.dumps(data, indent=2, ensure_ascii=False))

        title = data.get("title", "MNQ-MYM警报")
        description = data.get("description", "")

        success, result = send_feishu(f"{title}\n\n{description}")
        return jsonify({"status": "ok" if success else "error", "result": result})
    except Exception as e:
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
                cmd_name_lower = cmd_name.lower()
                logger.info(f"[FEISHU] Command: {cmd_name}")

                # 尝试找到匹配的命令（忽略大小写）
                matched_cmd = None
                for cmd in COMMANDS:
                    if cmd.lower() == cmd_name_lower:
                        matched_cmd = cmd
                        break

                if matched_cmd:
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
                    # 仅查询模式下不允许下单
                    if QUERY_ONLY:
                        send_feishu(
                            "🔒 **仅查询模式已启用**\n\n当前仅允许查询操作，不允许下单。\n\n可用查询命令：\n• 价差 - 查询价差\n• MNQMYM - 查询 MNQ_MYM\n• /spread - 查询价差\n• /持仓 - 查询持仓\n• /账户 - 查询账户\n\n发送 /help 查看帮助",
                            chat_id,
                        )
                    else:
                        # 尝试解析订单
                        logger.info(f"[FEISHU] Trying natural language orders: {text}")

                        cmd, status_msg = parse_natural_language_orders(text)

                        if cmd and status_msg:
                            logger.info(f"[FEISHU] Parsed command: {cmd}")
                            send_feishu(f"**{status_msg}**\n\n执行中...", chat_id)

                            output = execute_command(cmd)
                            logger.info(f"[FEISHU] Order output: {output}")
                            send_feishu(f"**订单执行结果:**\n\n{output}", chat_id)
                        else:
                            # 不是订单命令，显示帮助
                            send_feishu(get_help_text(), chat_id)

        return jsonify({"status": "ok"}), 200
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


@app.route("/health", methods=["GET"])
def health():
    config_status = {
        "app_id": bool(FEISHU_APP_ID),
        "conversation_id": bool(FEISHU_CONVERSATION_ID),
        "query_only": QUERY_ONLY,
    }
    return jsonify({"status": "ok", "config": config_status})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else get_webhook_port()

    print("=" * 60)
    print("🚀 TradingView -> 飞书 中转服务启动")
    print("=" * 60)
    print(f"📍 服务地址: http://0.0.0.0:{port}")
    print(f"🔒 模式: {'仅查询' if QUERY_ONLY else '交易'}")

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
    print("  /status - 查看监控状态")
    print("  /start - 启动监控")
    print("  /stop - 停止监控")
    print("  /help - 显示帮助")
    print("  自然语言: 「买入100股AAPL」")
    print("=" * 60)

    app.run(host="0.0.0.0", port=port)
