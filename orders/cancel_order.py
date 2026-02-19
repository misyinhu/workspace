#!/usr/bin/env python3
"""取消订单"""

import json
import argparse
import sys
import os
from ib_insync import IB

# 确保使用正确的 Python 环境（虚拟环境支持）
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    from config.env_config import ensure_venv
    ensure_venv()
except ImportError:
    pass

from client.ibkr_client import get_client_id, IBKR_HOST, IBKR_PORT


def parse_args():
    parser = argparse.ArgumentParser(description="取消订单")
    parser.add_argument("--order_id", type=int, required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    ib = IB()
    result = {}

    try:
        ib.connect(IBKR_HOST, IBKR_PORT, clientId=get_client_id())

        for trade in ib.trades():
            if trade.order.orderId == args.order_id:
                ib.cancelOrder(trade.order)
                result = {
                    "orderId": args.order_id,
                    "status": "Cancelled",
                    "message": f"Order {args.order_id} cancelled",
                }
                break
        else:
            result = {"error": f"Order {args.order_id} not found"}

    except Exception as e:
        result = {"error": str(e)}
    finally:
        if ib.isConnected():
            ib.disconnect()

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
