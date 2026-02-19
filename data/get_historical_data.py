#!/usr/bin/env python3
"""获取历史数据"""

import json
import argparse
from ib_insync import IB, Stock, Future, CFD
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
    parser = argparse.ArgumentParser(description="获取历史数据")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--duration", default="1 D")
    parser.add_argument("--bar_size", default="1 hour")
    parser.add_argument("--exchange", default="SMART")
    parser.add_argument("--sec_type", default="STK")
    parser.add_argument("--currency", default="USD")
    parser.add_argument("--what_to_show", default="TRADES")
    parser.add_argument("--local_symbol", default="")
    return parser.parse_args()


def main():
    args = parse_args()
    ib = IB()
    result = []

    try:
        ib.connect(IBKR_HOST, IBKR_PORT, clientId=get_client_id())

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
            contract = Stock(
                args.symbol, exchange=args.exchange, currency=args.currency
            )

        bars = ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr=args.duration,
            barSizeSetting=args.bar_size,
            whatToShow=args.what_to_show,
            useRTH=False,
            formatDate=1,
        )

        for bar in bars:
            result.append(
                {
                    "date": str(bar.date),
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                    "wap": bar.average,
                    "count": bar.barCount,
                }
            )

    except Exception as e:
        result = [{"error": str(e)}]
    finally:
        if ib.isConnected():
            ib.disconnect()

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
