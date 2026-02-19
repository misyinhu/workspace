#!/usr/bin/env python3
"""获取当前持仓"""

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

ib = IB()
result = []

try:
    ib.connect(IBKR_HOST, IBKR_PORT, clientId=get_client_id())
    positions = ib.positions()
    for pos in positions:
        result.append(
            {
                "symbol": pos.contract.symbol,
                "secType": pos.contract.secType,
                "exchange": pos.contract.exchange,
                "position": pos.position,
                "avgCost": pos.avgCost,
                "account": pos.account,
            }
        )
    print(json.dumps(result, indent=2, default=str))
except Exception as e:
    print(json.dumps({"error": str(e)}, indent=2))
finally:
    if ib.isConnected():
        ib.disconnect()
