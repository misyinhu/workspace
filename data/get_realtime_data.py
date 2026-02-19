#!/usr/bin/env python3
"""获取实时数据"""

import json
import argparse
import time
from datetime import datetime
from ib_insync import IB, Stock, Future, CFD, util
import sys
import os

# 确保使用正确的 Python 环境（虚拟环境支持）
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
try:
    from config.env_config import ensure_venv
    ensure_venv()
except ImportError:
    pass

from client.ibkr_client import get_client_id, IBKR_HOST, IBKR_PORT


def parse_args():
    parser = argparse.ArgumentParser(description="获取实时数据")
    parser.add_argument("--symbol", required=True, help="品种代码")
    parser.add_argument("--exchange", default="SMART", help="交易所")
    parser.add_argument("--sec_type", default="STK", help="证券类型")
    parser.add_argument("--currency", default="USD", help="货币")
    parser.add_argument("--local_symbol", default="", help="本地合约代码")
    parser.add_argument("--timeout", type=int, default=15, help="超时时间(秒)")
    parser.add_argument(
        "--format", choices=["json", "table"], default="json", help="输出格式"
    )
    return parser.parse_args()


def get_contract(args):
    """根据参数创建合约对象"""
    if args.sec_type == "FUT":
        if args.local_symbol:
            contract = Future(
                symbol=args.symbol,
                localSymbol=args.local_symbol,
                exchange=args.exchange,
                currency=args.currency,
            )
        else:
            contract = Future(
                args.symbol, exchange=args.exchange, currency=args.currency
            )
    elif args.sec_type == "CFD":
        contract = CFD(args.symbol, exchange=args.exchange, currency=args.currency)
    else:
        contract = Stock(args.symbol, exchange=args.exchange, currency=args.currency)
    return contract


def get_realtime_price(ib, contract, timeout=15):
    """获取实时价格数据"""
    try:
        # 请求市场数据
        ticker = ib.reqMktData(contract, "", False, False)

        # 等待数据填充
        start_time = time.time()
        while time.time() - start_time < timeout:
            util.sleep(0.5)
            if ticker.last > 0 and ticker.bid > 0 and ticker.ask > 0:
                break

        # 检查数据完整性
        if ticker.last == 0:
            return None, "市场数据订阅不足或市场休市"

        return {
            "timestamp": ticker.time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            if ticker.time
            else datetime.now().isoformat(),
            "bid": ticker.bid,
            "ask": ticker.ask,
            "last": ticker.last,
            "volume": ticker.volume,
            "bid_size": ticker.bidSize,
            "ask_size": ticker.askSize,
        }, None

    finally:
        # 取消市场数据订阅
        try:
            ib.cancelMktData(contract)
        except:
            pass


def format_output(data, contract, args, error=None):
    """格式化输出结果"""
    if error:
        if args.format == "json":
            print(json.dumps({"error": error, "symbol": args.symbol}, indent=2))
        else:
            print(f"❌ 错误: {error}")
            print(f"💡 可能原因:")
            print("1. 市场休市时间")
            print("2. 缺少市场数据订阅")
            print("3. 合约代码错误")
            print("4. 交易所配置错误")
        return

    if args.format == "table":
        print(f"📊 {args.symbol} 实时价格")
        print("=" * 40)
        print(f"品种: {args.symbol}")
        print(f"交易所: {args.exchange}")
        print(f"类型: {args.sec_type}")
        print(f"时间: {data['timestamp']}")
        print(f"最新价: {data['last']}")
        print(f"买价: {data['bid']}")
        print(f"卖价: {data['ask']}")
        print(f"成交量: {data['volume']}")
        print(f"买量: {data['bid_size']}")
        print(f"卖量: {data['ask_size']}")
        if args.local_symbol:
            print(f"合约代码: {args.local_symbol}")
        return

    # JSON格式输出
    result = {
        "symbol": args.symbol,
        "exchange": args.exchange,
        "timestamp": data["timestamp"],
        "bid": data["bid"],
        "ask": data["ask"],
        "last": data["last"],
        "volume": data["volume"],
        "bid_size": data["bid_size"],
        "ask_size": data["ask_size"],
        "contract_info": {
            "symbol": contract.symbol,
            "sec_type": contract.secType,
            "exchange": contract.exchange,
            "currency": contract.currency,
        },
    }

    if args.local_symbol:
        result["contract_info"]["local_symbol"] = args.local_symbol

    print(json.dumps(result, indent=2, default=str))


def main():
    args = parse_args()
    ib = IB()

    try:
        # 连接IBKR (使用可用端口)
        ib.connect(IBKR_HOST, IBKR_PORT, clientId=get_client_id())
        print(f"✅ 成功连接到IBKR")

        # 创建合约
        contract = get_contract(args)
        print(f"📈 正在查询 {args.symbol} 的实时价格...")

        # 获取实时价格
        price_data, error = get_realtime_price(ib, contract, args.timeout)

        # 格式化输出
        format_output(price_data, contract, args, error)

    except Exception as e:
        error_result = {"error": str(e)}
        if args.format == "json":
            print(json.dumps(error_result, indent=2))
        else:
            print(f"❌ 连接错误: {e}")

    finally:
        if ib.isConnected():
            ib.disconnect()
            print("🔌 已断开IBKR连接")


if __name__ == "__main__":
    main()
