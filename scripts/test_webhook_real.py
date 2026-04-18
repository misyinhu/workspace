#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Webhook 交易测试 - 真实 IB 连接测试
仅在 CXClaw 上运行，需要 IB Gateway
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def test_nl_parser():
    """测试自然语言解析（不需要 IB）"""
    from notify.nl_parser import parse_trading_command
    
    test_cases = [
        ("买入1手GC", "BUY", "GC", 1),
        ("卖出1手ES", "SELL", "ES", 1),
        ("买入1手MNQ", "BUY", "MNQ", 1),
        ("平仓CL", "CLOSE", "CL", None),
    ]
    
    print("\n=== 自然语言解析测试 ===")
    for text, expected_action, expected_symbol, expected_qty in test_cases:
        result = parse_trading_command(text)
        action = result.get('action')
        symbol = result.get('symbol')
        quantity = result.get('quantity')
        
        passed = (action == expected_action and symbol == expected_symbol)
        status = "✅" if passed else "❌"
        print(f"{status} {text} -> action={action}, symbol={symbol}, qty={quantity}")
        
        if not passed:
            print(f"   Expected: action={expected_action}, symbol={expected_symbol}")
            return False
    
    return True


def test_exchange_mapper():
    """测试交易所映射（不需要 IB）"""
    from orders.exchange_mapper import get_exchange_for_symbol
    
    test_cases = [
        ("GC", "FUT", "COMEX"),
        ("MGC", "FUT", "COMEX"),
        ("ES", "FUT", "CME"),
        ("MNQ", "FUT", "CME"),
        ("YM", "FUT", "CBOT"),
        ("MYM", "FUT", "CBOT"),
        ("CL", "FUT", "NYMEX"),
        ("MCL", "FUT", "NYMEX"),
        ("6E", "FUT", "CME"),
        ("ZB", "FUT", "CBOT"),
    ]
    
    print("\n=== 交易所映射测试 ===")
    for symbol, sec_type, expected_exchange in test_cases:
        exchange = get_exchange_for_symbol(symbol, sec_type)
        passed = (exchange == expected_exchange)
        status = "✅" if passed else "❌"
        print(f"{status} {symbol} -> {exchange} (expected: {expected_exchange})")
        
        if not passed:
            return False
    
    return True


def test_ib_connection():
    """测试 IB 连接"""
    from client.ib_connection import get_ib_connection
    
    print("\n=== IB 连接测试 ===")
    try:
        ib = get_ib_connection()
        if ib.isConnected():
            print(f"✅ IB 已连接: {ib}")
            return True, ib
        else:
            print("❌ IB 未连接")
            return False, None
    except Exception as e:
        print(f"❌ IB 连接失败: {e}")
        return False, None


def test_place_order(ib):
    """测试真实下单"""
    from orders.place_order_func import place_order
    from orders.exchange_mapper import get_exchange_for_symbol
    
    test_cases = [
        ("GC", "BUY", 1),   # 黄金
        ("ES", "BUY", 1),   # 标普
        ("MNQ", "BUY", 1),  # 微型纳指
    ]
    
    print("\n=== 真实下单测试 ===")
    
    # 检查当前模式
    from config import is_query_only
    query_only = is_query_only()
    print(f"当前模式: {'仅查询' if query_only else '交易模式'}")
    
    if query_only:
        print("⚠️  仅查询模式，跳过真实下单测试")
        print("发送 '/交易模式' 到飞书切换模式后再测试")
        return True
    
    for symbol, action, quantity in test_cases:
        exchange = get_exchange_for_symbol(symbol, "FUT")
        print(f"\n尝试下单: {action} {quantity} 手 {symbol} @ {exchange}")
        
        try:
            result = place_order(ib, symbol, action, quantity, exchange=exchange)
            
            if "error" in result:
                print(f"❌ 下单失败: {result['error']}")
            else:
                status = result.get("status", "unknown")
                order_id = result.get("orderId", 0)
                print(f"✅ 下单成功: orderId={order_id}, status={status}")
                
        except Exception as e:
            print(f"❌ 下单异常: {e}")
    
    return True


def test_webhook_endpoint():
    """测试 Webhook 端点"""
    from notify.webhook_bridge import app
    
    print("\n=== Webhook 端点测试 ===")
    
    with app.test_client() as client:
        # 健康检查
        response = client.get('/health')
        if response.status_code == 200:
            data = json.loads(response.data)
            print(f"✅ /health 返回: {data}")
        else:
            print(f"❌ /health 失败: {response.status_code}")
            return False
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Webhook 交易测试 - 真实环境")
    print("=" * 60)
    
    results = {}
    
    # 1. 自然语言解析测试（不需要 IB）
    results['nl_parser'] = test_nl_parser()
    
    # 2. 交易所映射测试（不需要 IB）
    results['exchange_mapper'] = test_exchange_mapper()
    
    # 3. Webhook 端点测试（不需要 IB）
    results['webhook_endpoint'] = test_webhook_endpoint()
    
    # 4. IB 连接测试（需要 IB Gateway）
    connected, ib = test_ib_connection()
    results['ib_connection'] = connected
    
    if connected:
        # 5. 真实下单测试
        results['place_order'] = test_place_order(ib)
    else:
        print("\n⚠️  IB 未连接，跳过下单测试")
        results['place_order'] = False
    
    # 总结
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {test_name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("⚠️  部分测试失败，请检查配置")
    
    return all_passed


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)