#!/usr/bin/env python3
"""获取成交记录"""

import json
from typing import List, Dict, Any, Optional
from ib_insync import IB


def get_trades(ib: Optional[IB] = None) -> List[Dict[str, Any]]:
    if ib is None:
        from client.ib_connection import get_ib_connection
        ib = get_ib_connection()
    
    fills = ib.fills()
    result = []
    for fill in fills:
        result.append({
            "symbol": fill.contract.symbol,
            "secType": fill.contract.secType,
            "exchange": fill.contract.exchange,
            "action": fill.execution.side,
            "quantity": fill.execution.cumQty,
            "price": fill.execution.price,
            "time": fill.execution.time.strftime("%Y-%m-%d %H:%M:%S"),
            "commission": fill.commissionReport.commission if fill.commissionReport else 0,
            "execId": fill.execution.execId,
            "orderId": fill.execution.orderId,
            "account": fill.execution.acctNumber,
        })
    return result


def format_trades(ib: Optional[IB] = None, limit: int = 20) -> str:
    trades = get_trades(ib)
    
    if not trades:
        return "📝 最近无成交"
    
    trades = trades[-limit:]
    lines = ["**📝 最近成交**\n"]
    for trade in trades:
        symbol = trade.get("symbol", "")
        action = trade.get("action", "")
        quantity = trade.get("quantity", 0)
        price = trade.get("price", 0)
        time_str = trade.get("time", "")[:16]
        
        action_emoji = "🟢" if action == "BUY" else "🔴"
        lines.append(f"{action_emoji} {symbol}: {action} {quantity} @ {price:.2f} ({time_str})")
    
    return "\n".join(lines)