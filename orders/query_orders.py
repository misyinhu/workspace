#!/usr/bin/env python3
"""获取订单列表 - 函数版本"""

import json
from typing import List, Dict, Any, Optional
from ib_insync import IB


def get_orders(ib: Optional[IB] = None) -> Dict[str, List[Dict[str, Any]]]:
    if ib is None:
        from client.ib_connection import get_ib_connection
        ib = get_ib_connection()
    
    orders_by_status = {
        "pending": [],
        "filled": [],
        "cancelled": [],
        "inactive": [],
    }
    
    for trade in ib.trades():
        os = trade.orderStatus
        c = trade.contract
        
        order_info = {
            "orderId": trade.order.orderId,
            "symbol": c.localSymbol if hasattr(c, "localSymbol") and c.localSymbol else c.symbol,
            "action": trade.order.action,
            "quantity": trade.order.totalQuantity,
            "orderType": trade.order.orderType,
            "status": os.status,
            "filled": os.filled,
            "remaining": os.remaining,
            "avgFillPrice": os.avgFillPrice,
        }
        
        if os.status in {"Submitted", "PendingSubmit", "PreSubmitted", "Active", "ApiPending"}:
            orders_by_status["pending"].append(order_info)
        elif os.status in {"Filled", "ApiTraded"}:
            orders_by_status["filled"].append(order_info)
        elif os.status in {"Cancelled", "ApiCancelled"}:
            orders_by_status["cancelled"].append(order_info)
        else:
            orders_by_status["inactive"].append(order_info)
    
    return orders_by_status


def format_orders(ib: Optional[IB] = None) -> str:
    orders = get_orders(ib)
    
    if not any(orders.values()):
        return "📋 当前无订单"
    
    lines = ["**📋 订单状态**\n"]
    
    pending = orders.get("pending", [])
    if pending:
        lines.append(f"🔄 待成交 ({len(pending)} 单)")
        for o in pending:
            symbol = o.get("symbol", "")
            action = o.get("action", "")
            filled = o.get("filled", 0)
            quantity = o.get("quantity", 0)
            status = o.get("status", "")
            lines.append(f"  • {symbol}: {action} {filled:.0f}/{quantity} ({status})")
    
    filled = orders.get("filled", [])
    if filled:
        lines.append(f"\n✅ 已成交 ({len(filled)} 单)")
        for o in filled:
            symbol = o.get("symbol", "")
            action = o.get("action", "")
            filled_qty = o.get("filled", 0)
            quantity = o.get("quantity", 0)
            avg_price = o.get("avgFillPrice", 0)
            lines.append(f"  • {symbol}: {action} {filled_qty:.0f}/{quantity} @ ${avg_price:.2f}")
    
    cancelled = orders.get("cancelled", [])
    if cancelled:
        lines.append(f"\n❌ 已取消 ({len(cancelled)} 单)")
        for o in cancelled:
            symbol = o.get("symbol", "")
            action = o.get("action", "")
            quantity = o.get("quantity", 0)
            lines.append(f"  • {symbol}: {action} {quantity}")
    
    return "\n".join(lines)