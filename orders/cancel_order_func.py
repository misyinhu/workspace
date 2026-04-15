#!/usr/bin/env python3
"""取消订单 - 函数版本"""

import json
from typing import Optional, Dict, Any
from ib_insync import IB


def cancel_order(ib: Optional[IB], order_id: int) -> Dict[str, Any]:
    result = {}
    
    try:
        for trade in ib.trades():
            if trade.order.orderId == order_id:
                ib.cancelOrder(trade.order)
                result = {
                    "orderId": order_id,
                    "status": "Cancelled",
                    "message": f"Order {order_id} cancelled",
                }
                break
        else:
            result = {"error": f"Order {order_id} not found"}
    
    except Exception as e:
        result = {"error": str(e)}
    
    return result


def format_cancel_result(result: Dict[str, Any]) -> str:
    if "error" in result:
        return f"❌ 取消失败: {result['error']}"
    
    return f"✅ 订单 {result.get('orderId')} 已取消"