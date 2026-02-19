#!/usr/bin/env python3
"""获取账户摘要"""

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
result = {}

try:
    ib.connect(IBKR_HOST, IBKR_PORT, clientId=get_client_id())
    summary = ib.accountSummary()
    for item in summary:
        result[item.tag] = {
            "value": item.value,
            "currency": item.currency,
            "account": item.account,
        }
    print(json.dumps(result, indent=2, default=str))
except Exception as e:
    print(json.dumps({"error": str(e)}, indent=2))
finally:
    if ib.isConnected():
        ib.disconnect()
