#!/usr/bin/env python3
"""获取账户摘要"""

import json
from typing import Dict, Any, Optional
from ib_insync import IB


def get_account_summary(ib: Optional[IB] = None) -> Dict[str, Any]:
    if ib is None:
        from client.ib_connection import get_ib_connection
        ib = get_ib_connection()
    
    summary = ib.accountSummary()
    result = {}
    for item in summary:
        result[item.tag] = {
            "value": item.value,
            "currency": item.currency,
            "account": item.account,
        }
    return result


def format_account_summary(ib: Optional[IB] = None) -> str:
    summary = get_account_summary(ib)
    
    if not summary:
        return "📋 账户摘要: 无数据"
    
    key_fields = [
        "NetLiquidationByCurrency",
        "CashBalance",
        "BuyingPower",
        "ExcessLiquidity",
        "AvailableFunds",
        "MarginReq",
        "TotalCashValue",
    ]
    
    lines = ["**📋 账户摘要**\n"]
    for field in key_fields:
        if field in summary:
            value = summary[field].get("value", "N/A")
            currency = summary[field].get("currency", "")
            lines.append(f"• {field}: {value} {currency}")
    
    return "\n".join(lines)


if __name__ == "__main__":
    print(json.dumps(get_account_summary(), indent=2, default=str))