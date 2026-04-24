#!/usr/bin/env python3
"""
测试 multi-timeframe 数据获取
动态读取 settings.yaml 配置的品种，轮流测试各周期数据
"""

import os
import sys
import yaml
import requests
import time
from datetime import datetime

CONFIG_PATH = "/Users/wang/.opencode/workspace/trading/config/settings.yaml"
QUANT_CORE_URL = "http://100.82.238.11:8005"
CLIENT_ID = "10"

TIMEFRAMES = ["1m", "5m", "30m", "4h", "1D"]
BAR_MAP = {"1m": "1m", "5m": "5m", "30m": "30m", "4h": "4h", "1D": "1D"}


def load_config():
    """加载共享配置"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_instrument(symbol, source):
    """测试单个品种的所有时间周期"""
    results = {}
    headers = {"X-Client-ID": CLIENT_ID}

    for tf in TIMEFRAMES:
        bar = BAR_MAP.get(tf, tf)
        try:
            resp = requests.get(
                f"{QUANT_CORE_URL}/api/history",
                params={"symbol": symbol, "source": source, "bar": bar, "num": 5},
                headers=headers,
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    results[tf] = ("✅", len(data), data[0].get("close", 0))
                else:
                    results[tf] = ("❌", "empty response", 0)
            else:
                err = resp.json().get("error", "")[:50] if resp.text else "unknown"
                results[tf] = ("❌", err, 0)
        except Exception as e:
            results[tf] = ("❌", str(e)[:30], 0)

    return results


def print_results(symbol, source, results):
    """打印测试结果"""
    print(f"\n{'=' * 60}")
    print(f"品种: {symbol} | 数据源: {source}")
    print(f"{'=' * 60}")

    all_ok = True
    for tf in TIMEFRAMES:
        status, info, price = results[tf]
        if status == "✅":
            print(f"  {tf:5s}: {status} ({info} bars, close={price})")
        else:
            print(f"  {tf:5s}: {status} {info}")
            all_ok = False

    return all_ok


def main():
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API地址: {QUANT_CORE_URL}")
    print(f"Client ID: {CLIENT_ID}")

    config = load_config()
    instruments = config.get("instruments", [])

    if not instruments:
        print("❌ 没有找到品种配置!")
        return

    print(f"\n找到 {len(instruments)} 个品种\n")

    summary = {"total": 0, "ok": 0, "fail": 0}
    source_stats = {}

    for inst in instruments:
        symbol = inst["symbol"]
        source = inst.get("source", "okx")
        summary["total"] += 1

        if source not in source_stats:
            source_stats[source] = {"total": 0, "ok": 0, "fail": 0}
        source_stats[source]["total"] += 1

        results = test_instrument(symbol, source)
        ok = print_results(symbol, source, results)

        if ok:
            summary["ok"] += 1
            source_stats[source]["ok"] += 1
        else:
            summary["fail"] += 1
            source_stats[source]["fail"] += 1

        time.sleep(0.5)

    print(f"\n{'=' * 60}")
    print("汇总")
    print(f"{'=' * 60}")
    print(f"总计: {summary['total']} | ✅: {summary['ok']} | ❌: {summary['fail']}")

    for src, stats in source_stats.items():
        ok_rate = (
            f"{stats['ok'] * 100 / stats['total']:.0f}%" if stats["total"] > 0 else "0%"
        )
        print(
            f"  {src:15s}: {stats['total']} 个 | ✅ {stats['ok']} ({ok_rate}) | ❌ {stats['fail']}"
        )


if __name__ == "__main__":
    main()
