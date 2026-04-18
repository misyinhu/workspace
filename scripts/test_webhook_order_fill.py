#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Webhook 交易功能测试 - 改进版
验证订单是否真正成交
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import time
import requests

BASE_URL = "http://100.82.238.11:5002"
FEISHU_CONVERSATION_ID = "oc_7455ec51aff3a187248914f978b834e3"

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def get_positions():
    """获取当前持仓"""
    resp = requests.get(f"{BASE_URL}/positions", timeout=10)
    if resp.status_code == 200:
        return resp.json().get('positions', [])
    return []


def get_position_qty(symbol, positions):
    """获取指定合约的持仓数量"""
    for pos in positions:
        if pos.get('symbol') == symbol:
            return pos.get('position', 0)
    return 0


def send_command(cmd_text):
    """发送交易命令"""
    resp = requests.post(
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
        timeout=30
    )
    return resp


def wait_for_fill(symbol, expected_qty_change, timeout=30, check_interval=2):
    """等待订单成交"""
    start_time = time.time()
    initial_positions = get_positions()
    initial_qty = get_position_qty(symbol, initial_positions)
    
    print(f"   初始 {symbol} 持仓: {initial_qty}")
    
    while time.time() - start_time < timeout:
        time.sleep(check_interval)
        current_positions = get_positions()
        current_qty = get_position_qty(symbol, current_positions)
        qty_change = current_qty - initial_qty
        
        print(f"   当前 {symbol} 持仓: {current_qty} (变化: {qty_change:+.4f})")
        
        # 检查是否有预期的变化
        if expected_qty_change > 0 and qty_change >= expected_qty_change * 0.9:
            return True, qty_change
        elif expected_qty_change < 0 and qty_change <= expected_qty_change * 0.9:
            return True, qty_change
        
        # 检查是否有其他变化（可能已经反向成交）
        if abs(qty_change) > abs(expected_qty_change) * 0.5:
            print(f"   ⚠️ 持仓变化与预期不符，继续观察...")
    
    return False, current_qty - initial_qty


def test_trading():
    print("=" * 60)
    print("Webhook 交易测试 (改进版)")
    print("=" * 60)
    
    # 先检查健康状态
    resp = requests.get(f"{BASE_URL}/health", timeout=10)
    if resp.status_code != 200:
        print(f"❌ /health 失败: {resp.status_code}")
        return False
    print(f"✅ /health OK")
    
    # 获取初始持仓
    initial_positions = get_positions()
    print(f"\n初始持仓: {json.dumps(initial_positions, indent=2)}")
    
    results = []
    
    # 测试用例：(命令, 预期持仓变化)
    test_cases = [
        ("买入1手GC", "GC", "BUY", 1),
        # ("买入1手MNQ", "MNQ", "BUY", 1),
        # ("卖出1手CL", "CL", "SELL", 1),
    ]
    
    for cmd_text, symbol, action, expected_change in test_cases:
        print(f"\n{'='*50}")
        print(f"测试: {cmd_text}")
        print(f"预期 {symbol} 持仓变化: {expected_change:+d}")
        print("=" * 50)
        
        # 发送命令
        resp = send_command(cmd_text)
        print(f"HTTP 响应: {resp.status_code}")
        print(f"响应内容: {resp.text[:500]}")
        
        if resp.status_code != 200:
            print(f"❌ HTTP 请求失败")
            results.append((cmd_text, False, "HTTP失败"))
            continue
        
        # 等待订单成交
        print("\n等待订单成交...")
        success, actual_change = wait_for_fill(symbol, expected_change, timeout=30)
        
        if success:
            print(f"\n✅ {cmd_text} - 订单已成交")
            print(f"   持仓变化: {actual_change:+.4f}")
            results.append((cmd_text, True, f"成交{actual_change:+.4f}"))
        else:
            print(f"\n⚠️ {cmd_text} - 订单未成交或未完全成交")
            print(f"   持仓变化: {actual_change:+.4f}")
            results.append((cmd_text, False, f"未成交{actual_change:+.4f}"))
        
        # 等待一小段时间再进行下一个测试
        time.sleep(3)
    
    # 检查最终持仓
    final_positions = get_positions()
    print(f"\n{'='*60}")
    print("最终持仓")
    print("=" * 60)
    print(json.dumps(final_positions, indent=2))
    
    # 总结
    print(f"\n{'='*60}")
    print("测试结果汇总")
    print("=" * 60)
    for cmd, passed, detail in results:
        status = "✅" if passed else "❌"
        print(f"{status} {cmd}: {detail}")
    
    all_passed = all(r[1] for r in results)
    print(f"\n{'='*60}")
    if all_passed:
        print("🎉 所有订单成交成功！")
    else:
        print("⚠️  部分订单未成交，需要检查")
    print("=" * 60)
    
    return all_passed


if __name__ == '__main__':
    success = test_trading()
    sys.exit(0 if success else 1)
