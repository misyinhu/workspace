#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import time
import requests
_session = requests.Session()
_session.trust_env = False  # 禁用系统代理

BASE_URL = "http://100.82.238.11:5002"
FEISHU_CONVERSATION_ID = "oc_7455ec51aff3a187248914f978b834e3"

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

TEST_CASES = [
    ("买入1手GC", "BUY", "GC"),
    ("买入1手MNQ", "BUY", "MNQ"),
    ("平仓MNQ", "CLOSE", "MNQ"),
    ("平仓GC", "CLOSE", "GC"),
    ("卖出1手CL", "SELL", "CL"),
]


def test_nl_parser():
    from notify.nl_parser import parse_trading_command
    
    print("\n=== 测试自然语言解析 ===")
    
    all_passed = True
    for text, expected_action, expected_symbol in TEST_CASES:
        result = parse_trading_command(text)
        action = result.get('action')
        symbol = result.get('symbol')
        
        if action == expected_action and symbol == expected_symbol:
            print(f"   ✅ {text} -> {action} {symbol}")
        else:
            print(f"   ❌ {text} -> {action} {symbol} (expected: {expected_action} {expected_symbol})")
            all_passed = False
    
    return all_passed


def test_webhook_health():
    print("\n=== 测试 Webhook 健康检查 ===")
    
    resp = _session.get(f"{BASE_URL}/health", timeout=10)
    if resp.status_code == 200:
        print(f"   ✅ /health OK: {resp.json()}")
        return True
    else:
        print(f"   ❌ /health 失败: {resp.status_code}")
        return False


def get_positions():
    resp = _session.get(f"{BASE_URL}/positions", timeout=10)
    if resp.status_code == 200:
        return resp.json().get('positions', [])
    return []


def send_command(cmd_text):
    resp = _session.post(
        f"{BASE_URL}/feishu-webhook",
        json={
            "header": {"event_type": "im.message.receive_v1"},
            "event": {
                "message": {
                    "message_id": f"test_{int(time.time())}",
                    "chat_id": FEISHU_CONVERSATION_ID,
                    "content": json.dumps({"text": cmd_text})
                }
            }
        },
        timeout=15
    )
    data = resp.json() if resp.status_code == 200 else {}
    return resp.status_code == 200 and data.get("status") == "ok", data


def has_position(symbol, positions):
    return any(
        pos.get('symbol') == symbol and abs(pos.get('position', 0)) >= 1
        for pos in positions
    )


def test_trading_commands():
    print("\n=== 测试交易命令 ===")
    
    positions = get_positions()
    print(f"   初始持仓: {positions}")
    
    all_passed = True
    
    for cmd_text, action, symbol in TEST_CASES:
        print(f"\n   --- {cmd_text} ({action} {symbol}) ---")
        
        if action == "CLOSE":
            if not has_position(symbol, positions):
                print(f"   ⚠️  {symbol} 无持仓，跳过")
                continue
            
            print(f"   执行前 {symbol} 持仓: {[p for p in positions if p.get('symbol') == symbol]}")
            
            if not send_command(cmd_text):
                print(f"   ❌ 请求失败")
                all_passed = False
                continue
            
            print(f"   ✅ 命令已发送，等待成交...")
            time.sleep(5)
            
            new_positions = get_positions()
            print(f"   执行后持仓: {new_positions}")
            
            if has_position(symbol, new_positions):
                print(f"   ❌ {symbol} 仍有持仓")
                all_passed = False
            else:
                print(f"   ✅ {symbol} 已平仓")
                positions = new_positions
        
        elif action in ("BUY", "SELL"):
            print(f"   发送订单...")
            
            ok, data = send_command(cmd_text)
            order = data.get("order", {})
            
            # 打印订单结果
            if order:
                if "error" in order:
                    print(f"   ❌ 订单错误: {order['error']}")
                else:
                    status = order.get("status", "unknown")
                    order_id = order.get("orderId", "?")
                    filled = order.get("filled", 0)
                    avg_fill = order.get("avgFill", 0)
                    remaining = order.get("remaining", 0)
                    print(f"   📋 订单 #{order_id}: status={status}, filled={filled}, remaining={remaining}")
                    if status in ("Filled", "PartFilled"):
                        print(f"   ✅ 成交! avgFill={avg_fill}")
                    elif status in ("Submitted", "PendingSubmit"):
                        print(f"   ⏳ 等待成交...")
                    elif status == "ApiPending":
                        print(f"   ⏳ API待提交...")
                    else:
                        print(f"   ⚠️  未成交 (status={status})")
            else:
                print(f"   ❌ 无响应")
                all_passed = False
                continue
            
            time.sleep(5)
            new_positions = get_positions()
            print(f"   当前持仓: {new_positions}")
            positions = new_positions  # 更新持仓列表
    
    return all_passed


def main():
    print("=" * 60)
    print("Webhook 交易测试")
    print("=" * 60)
    
    results = {}
    results['nl_parser'] = test_nl_parser()
    results['health'] = test_webhook_health()
    results['trading'] = test_trading_commands()
    
    print("\n" + "=" * 60)
    print("测试结果")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("⚠️  部分测试失败")
    
    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
