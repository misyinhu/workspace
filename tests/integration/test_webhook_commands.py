#!/usr/bin/env python3
"""
Webhook 命令集成测试
测试所有飞书命令和监控功能
"""

import requests
import json
import sys
import time
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# 配置
BASE_URL = "http://localhost:5002"
WEBHOOK_URL = f"{BASE_URL}/webhook"
HEALTH_URL = f"{BASE_URL}/health"

# 3个交易对配置
PAIRS_CONFIG = {
    "MNQ_MYM": {"threshold": 1000},
    "HSTECH_MCH": {"threshold": 10000},
    "RB_CL": {"threshold": 5000},
}

# 测试结果存储
test_results = {
    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "tests": [],
    "summary": {"passed": 0, "failed": 0, "total": 0},
}


def log_test(name: str, passed: bool, details: str = ""):
    """记录测试结果"""
    test_results["tests"].append({
        "name": name,
        "passed": passed,
        "details": details,
        "time": datetime.now().strftime("%H:%M:%S"),
    })
    if passed:
        test_results["summary"]["passed"] += 1
        print(f"  ✅ {name}")
    else:
        test_results["summary"]["failed"] += 1
        print(f"  ❌ {name} - {details}")
    test_results["summary"]["total"] += 1


def health_check() -> bool:
    """健康检查"""
    try:
        resp = requests.get(HEALTH_URL, timeout=5)
        return resp.status_code == 200 and "ok" in resp.text
    except:
        return False


def send_command(cmd: str) -> Tuple[bool, str]:
    """发送命令到 webhook"""
    try:
        resp = requests.post(
            WEBHOOK_URL,
            json={"text": cmd},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        return resp.status_code == 200, resp.text
    except Exception as e:
        return False, str(e)


def check_health() -> bool:
    """测试 1: 健康检查"""
    passed = health_check()
    log_test("Health check", passed, "服务正常运行" if passed else "服务未运行")
    return passed


def test_status_command() -> bool:
    """测试 2: /status 命令"""
    passed, resp = send_command("/status")
    if passed:
        has_z120 = "Z120" in resp or "监控状态" in resp
        log_test("/status 命令", has_z120, "返回包含监控状态")
        return has_z120
    else:
        log_test("/status 命令", False, resp)
        return False


def test_help_command() -> bool:
    """测试 3: /help 命令"""
    passed, resp = send_command("/help")
    if passed:
        has_commands = "命令" in resp or "help" in resp.lower()
        log_test("/help 命令", has_commands, "返回包含命令列表")
        return has_commands
    else:
        log_test("/help 命令", False, resp)
        return False


def test_query_mode() -> bool:
    """测试 4: /查询模式 命令"""
    passed, resp = send_command("/查询模式")
    if passed:
        has_result = "查询模式" in resp
        log_test("/查询模式 命令", has_result, "返回确认消息")
        return has_result
    else:
        log_test("/查询模式 命令", False, resp)
        return False


def test_trade_mode() -> bool:
    """测试 5: /交易模式 命令"""
    passed, resp = send_command("/交易模式")
    if passed:
        has_result = "交易模式" in resp
        log_test("/交易模式 命令", has_result, "返回确认消息")
        return has_result
    else:
        log_test("/交易模式 命令", False, resp)
        return False


def test_stop_monitor() -> bool:
    """测试 6: /stop 命令"""
    passed, resp = send_command("/stop")
    if passed:
        has_result = "停止" in resp or "停止" in resp
        log_test("/stop 命令", has_result, "返回停止确认")
        return has_result
    else:
        log_test("/stop 命令", False, resp)
        return False


def test_start_monitor() -> bool:
    """测试 7: /start 命令"""
    passed, resp = send_command("/start")
    if passed:
        has_result = "启动" in resp or "运行" in resp
        log_test("/start 命令", has_result, "返回启动确认")
        return has_result
    else:
        log_test("/start 命令", False, resp)
        return False


def test_positions() -> bool:
    """测试 8: /持仓 命令"""
    passed, resp = send_command("/持仓")
    if passed:
        has_data = "[" in resp or "symbol" in resp.lower() or "持仓" in resp
        log_test("/持仓 命令", has_data, "返回持仓数据")
        return has_data
    else:
        log_test("/持仓 命令", False, resp)
        return False


def test_account() -> bool:
    """测试 9: /账户 命令"""
    passed, resp = send_command("/账户")
    if passed:
        has_data = "账户" in resp or "NetLiquidation" in resp or "value" in resp.lower()
        log_test("/账户 命令", has_data, "返回账户数据")
        return has_data
    else:
        log_test("/账户 命令", False, resp)
        return False


def test_orders() -> bool:
    """测试 10: /订单 命令"""
    passed, resp = send_command("/订单")
    if passed:
        has_data = "订单" in resp or "order" in resp.lower()
        log_test("/订单 命令", has_data, "返回订单数据")
        return has_data
    else:
        log_test("/订单 命令", False, resp)
        return False


def parse_status_response(resp: str) -> Dict:
    """解析 status 返回，提取交易对信息"""
    result = {
        "has_status": False,
        "pairs": {},
    }
    
    if "MNQ_MYM" in resp:
        result["pairs"]["MNQ_MYM"] = {"found": True}
        result["has_status"] = True
    if "HSTECH_MCH" in resp:
        result["pairs"]["HSTECH_MCH"] = {"found": True}
        result["has_status"] = True
    if "RB_CL" in resp:
        result["pairs"]["RB_CL"] = {"found": True}
        result["has_status"] = True
    
    return result


def test_all_pairs_in_status() -> bool:
    """测试 11: /status 包含所有3个交易对"""
    passed, resp = send_command("/status")
    if passed:
        result = parse_status_response(resp)
        all_found = all(
            result["pairs"].get(pair, {}).get("found", False)
            for pair in PAIRS_CONFIG.keys()
        )
        missing = [p for p in PAIRS_CONFIG.keys() if not result["pairs"].get(p, {}).get("found", False)]
        details = f"找到: {list(result['pairs'].keys())}" if all_found else f"缺失: {missing}"
        log_test("3个交易对都显示", all_found, details)
        return all_found
    else:
        log_test("3个交易对都显示", False, resp)
        return False


def test_refresh() -> bool:
    """测试 12: /refresh 命令"""
    passed, resp = send_command("/refresh")
    if passed:
        has_result = "刷新" in resp or "刷新" in resp
        log_test("/refresh 命令", has_result, "返回刷新确认")
        return has_result
    else:
        log_test("/refresh 命令", False, resp)
        return False


def run_basic_tests():
    """运行基础命令测试"""
    print("\n" + "=" * 60)
    print("阶段 1: 基础命令测试")
    print("=" * 60)
    
    test_status_command()
    test_help_command()
    test_query_mode()
    test_trade_mode()


def run_monitor_tests():
    """运行监控命令测试"""
    print("\n" + "=" * 60)
    print("阶段 2: 监控命令测试")
    print("=" * 60)
    
    test_stop_monitor()
    time.sleep(1)
    test_start_monitor()
    time.sleep(2)
    test_all_pairs_in_status()


def run_ib_tests():
    """运行 IB 查询测试"""
    print("\n" + "=" * 60)
    print("阶段 3: IB 查询测试")
    print("=" * 60)
    
    test_positions()
    test_account()
    test_orders()


def run_refresh_test():
    """运行刷新测试"""
    print("\n" + "=" * 60)
    print("阶段 4: 数据刷新测试")
    print("=" * 60)
    
    test_refresh()
    time.sleep(3)
    test_status_command()


def continuous_monitor(interval: int = 300, duration: int = 3600):
    """持续监控模式"""
    print("\n" + "=" * 60)
    print(f"持续监控模式 - 间隔 {interval}秒，持续 {duration}秒")
    print("=" * 60)
    
    start_time = time.time()
    iteration = 0
    
    while time.time() - start_time < duration:
        iteration += 1
        print(f"\n--- 迭代 {iteration} ---")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 刷新数据
        print("执行 /refresh...")
        send_command("/refresh")
        
        # 等待数据更新
        time.sleep(5)
        
        # 检查状态
        print("检查 /status...")
        passed, resp = send_command("/status")
        
        if passed:
            result = parse_status_response(resp)
            pairs_status = []
            for pair in PAIRS_CONFIG.keys():
                if result["pairs"].get(pair, {}).get("found"):
                    pairs_status.append(f"✅ {pair}")
                else:
                    pairs_status.append(f"❌ {pair}")
            print(f"交易对状态: {', '.join(pairs_status)}")
        else:
            print(f"❌ 获取状态失败")
        
        # 记录结果
        log_test(f"持续监控 #{iteration}", passed, datetime.now().strftime("%H:%M:%S"))
        
        # 等待下一个间隔
        if time.time() - start_time + interval < duration:
            print(f"等待 {interval}秒...")
            time.sleep(interval)
    
    print("\n持续监控结束")


def print_summary():
    """打印测试总结"""
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    summary = test_results["summary"]
    print(f"总计: {summary['total']}")
    print(f"通过: ✅ {summary['passed']}")
    print(f"失败: ❌ {summary['failed']}")
    
    pass_rate = (summary['passed'] / summary['total'] * 100) if summary['total'] > 0 else 0
    print(f"通过率: {pass_rate:.1f}%")
    
    return summary['failed'] == 0


def save_report(filename: str = None):
    """保存测试报告"""
    if filename is None:
        filename = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(test_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n测试报告已保存: {filename}")
    return filename


def main():
    parser = argparse.ArgumentParser(description="Webhook 命令集成测试")
    parser.add_argument("--url", default="http://localhost:5002", help="Webhook 服务地址")
    parser.add_argument("--watch", action="store_true", help="持续监控模式")
    parser.add_argument("--interval", type=int, default=300, help="监控间隔（秒）")
    parser.add_argument("--duration", type=int, default=3600, help="持续时间（秒）")
    parser.add_argument("--save", type=str, help="保存报告到文件")
    parser.add_argument("--basic", action="store_true", help="仅运行基础测试")
    parser.add_argument("--monitor", action="store_true", help="仅运行监控测试")
    parser.add_argument("--ib", action="store_true", help="仅运行IB测试")
    
    args = parser.parse_args()
    
    global BASE_URL, WEBHOOK_URL, HEALTH_URL
    BASE_URL = args.url
    WEBHOOK_URL = f"{BASE_URL}/webhook"
    HEALTH_URL = f"{BASE_URL}/health"
    
    print("=" * 60)
    print("Webhook 命令集成测试")
    print("=" * 60)
    print(f"目标: {BASE_URL}")
    print(f"时间: {test_results['timestamp']}")
    
    # 健康检查
    print("\n检查服务状态...")
    if not health_check():
        print(f"❌ 服务未运行: {BASE_URL}")
        print("请先启动 webhook 服务:")
        print("  python3 notify/webhook_bridge.py")
        sys.exit(1)
    
    print("✅ 服务运行中")
    
    # 根据参数选择测试模式
    if args.watch:
        continuous_monitor(args.interval, args.duration)
    elif args.basic:
        run_basic_tests()
        print_summary()
    elif args.monitor:
        run_monitor_tests()
        print_summary()
    elif args.ib:
        run_ib_tests()
        print_summary()
    else:
        # 完整测试流程
        run_basic_tests()
        run_monitor_tests()
        run_ib_tests()
        run_refresh_test()
        
        if print_summary():
            print("\n🎉 所有测试通过!")
        else:
            print("\n⚠️  部分测试失败")
    
    # 保存报告
    if args.save:
        save_report(args.save)
    else:
        save_report(f"tests/integration/test_results_{datetime.now().strftime('%Y%m%d')}.json")


if __name__ == "__main__":
    main()
