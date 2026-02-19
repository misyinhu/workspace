#!/usr/bin/env python3
"""获取成交记录"""

import json
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


def main():
    ib = IB()
    result = []

    try:
        ib.connect(IBKR_HOST, IBKR_PORT, clientId=get_client_id())

        # 获取所有成交记录 (fills)
        fills = ib.fills()

        for fill in fills:
            result.append(
                {
                    "symbol": fill.contract.symbol,
                    "secType": fill.contract.secType,
                    "exchange": fill.contract.exchange,
                    "action": fill.execution.side,
                    "quantity": fill.execution.cumQty,
                    "price": fill.execution.price,
                    "time": fill.execution.time.strftime("%Y-%m-%d %H:%M:%S"),
                    "commission": fill.commissionReport.commission
                    if fill.commissionReport
                    else 0,
                    "execId": fill.execution.execId,
                    "orderId": fill.execution.orderId,
                    "account": fill.execution.acctNumber,
                }
            )

        print(json.dumps(result, indent=2, default=str))

    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2))
    finally:
        if ib.isConnected():
            ib.disconnect()


if __name__ == "__main__":
    main()
