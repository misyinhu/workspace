#!/usr/bin/env python3
"""Webhook 测试脚本 - 本地调试"""

import requests
import json
import sys

BASE_URL = "http://100.82.238.11:5002"

def test_health():
    """测试 health 端点"""
    print("\n=== Test: /health ===")
    resp = requests.get(f"{BASE_URL}/health")
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
    return resp.status_code == 200

def test_positions():
    """测试 positions 端点"""
    print("\n=== Test: /positions ===")
    resp = requests.get(f"{BASE_URL}/positions")
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:500]}")
    return resp.status_code == 200

def test_feishu_webhook_command():
    """测试飞书命令 /持仓"""
    print("\n=== Test: /持仓 command ===")
    payload = {
        "event": {
            "message": {
                "chat_id": "oc_7455ec51aff3a187248914f978b834e3",
                "message_id": "om_test_cmd_1",
                "content": "{\"text\":\"/持仓\"}",
                "sender": {"user_id": "test"}
            }
        }
    }
    resp = requests.post(f"{BASE_URL}/feishu-webhook", json=payload)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:500]}")
    return resp.status_code == 200

def test_feishu_webhook_nl_buy():
    """测试自然语言买入"""
    print("\n=== Test: 买入1手GC ===")
    payload = {
        "event": {
            "message": {
                "chat_id": "oc_7455ec51aff3a187248914f978b834e3",
                "message_id": "om_test_nl_buy",
                "content": "买入1手GC",
                "sender": {"user_id": "test"}
            }
        }
    }
    resp = requests.post(f"{BASE_URL}/feishu-webhook", json=payload)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:500]}")
    return resp.status_code == 200

def test_feishu_webhook_nl_close():
    """测试自然语言平仓"""
    print("\n=== Test: 平掉BTC仓位 ===")
    payload = {
        "event": {
            "message": {
                "chat_id": "oc_7455ec51aff3a187248914f978b834e3",
                "message_id": "om_test_nl_close",
                "content": "平掉BTC仓位",
                "sender": {"user_id": "test"}
            }
        }
    }
    resp = requests.post(f"{BASE_URL}/feishu-webhook", json=payload)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:500]}")
    return resp.status_code == 200

def test_feishu_mode_switch():
    """测试模式切换"""
    print("\n=== Test: /交易模式 ===")
    payload = {
        "event": {
            "message": {
                "chat_id": "oc_7455ec51aff3a187248914f978b834e3",
                "message_id": "om_test_mode",
                "content": "{\"text\":\"/交易模式\"}",
                "sender": {"user_id": "test"}
            }
        }
    }
    resp = requests.post(f"{BASE_URL}/feishu-webhook", json=payload)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:500]}")
    return resp.status_code == 200


if __name__ == "__main__":
    tests = [
        ("/health", test_health),
        ("/positions", test_positions),
        ("/持仓", test_feishu_webhook_command),
        ("买入1手GC", test_feishu_webhook_nl_buy),
        ("平掉BTC仓位", test_feishu_webhook_nl_close),
        ("/交易模式", test_feishu_mode_switch),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"Error: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 50)
    print("Summary:")
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} - {name}")
    
    failed = sum(1 for _, s in results if not s)
    print(f"\nTotal: {len(results)}, Failed: {failed}")
    sys.exit(0 if failed == 0 else 1)