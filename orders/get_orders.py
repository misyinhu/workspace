#!/usr/bin/env python3
"""获取订单列表（按状态分类）"""

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

try:
    ib.connect(IBKR_HOST, IBKR_PORT, clientId=get_client_id())

    # 按状态分类
    orders_by_status = {
        "pending": [],  # 待成交
        "filled": [],  # 已成交
        "cancelled": [],  # 已取消
        "inactive": [],  # 未激活
    }

    for i, trade in enumerate(ib.trades()):
        os = trade.orderStatus
        c = trade.contract

        print(f"DEBUG TRADE {i}: orderId={trade.order.orderId}"
              f" contract={c}"
              f" action={trade.order.action}"
              f" totalQuantity={trade.order.totalQuantity}"
              f" filled={os.filled}"
              f" remaining={os.remaining}"
              f" avgFillPrice={os.avgFillPrice}"
              f" status={os.status}", file=sys.stderr)

        order_info = {
            "orderId": trade.order.orderId,
            "symbol": c.localSymbol
            if hasattr(c, "localSymbol") and c.localSymbol
            else c.symbol,
            "action": trade.order.action,
            "quantity": trade.order.totalQuantity,
            "orderType": trade.order.orderType,
            "status": os.status,
            "filled": os.filled,
            "remaining": os.remaining,
            "avgFillPrice": os.avgFillPrice,
        }

        # 按状态分类
        if os.status in {
            "Submitted",
            "PendingSubmit",
            "PreSubmitted",
            "Active",
            "ApiPending",
        }:
            orders_by_status["pending"].append(order_info)
        elif os.status in {"Filled", "ApiTraded"}:
            orders_by_status["filled"].append(order_info)
        elif os.status in {"Cancelled", "ApiCancelled"}:
            orders_by_status["cancelled"].append(order_info)
        else:
            orders_by_status["inactive"].append(order_info)

    # 打印分类结果
    print("\n" + "=" * 60)
    print("订单状态汇总")
    print("=" * 60)

    print(f"\n待成交 ({len(orders_by_status['pending'])} 单)")
    for o in orders_by_status["pending"]:
        print(
            f"  {o['symbol']:8} | {o['action']:4} | {o['status']:12} | {o['filled']:.1f}/{o['quantity']}"
        )

    print(f"\n已成交 ({len(orders_by_status['filled'])} 单)")
    for o in orders_by_status["filled"]:
        print(
            f"  {o['symbol']:8} | {o['action']:4} | {o['status']:12} | {o['filled']:.1f}/{o['quantity']} @ ${o['avgFillPrice']:.2f}"
        )

    print(f"\n已取消 ({len(orders_by_status['cancelled'])} 单)")
    for o in orders_by_status["cancelled"]:
        print(
            f"  {o['symbol']:8} | {o['action']:4} | {o['status']:12} | {o['filled']:.1f}/{o['quantity']}"
        )

    print(f"\n未激活 ({len(orders_by_status['inactive'])} 单)")
    for o in orders_by_status["inactive"]:
        print(
            f"  {o['symbol']:8} | {o['action']:4} | {o['status']:12} | {o['filled']:.1f}/{o['quantity']}"
        )

    print("\n" + "=" * 60)

    # 也输出 JSON 格式
    print("\nJSON 输出：")
    print(json.dumps(orders_by_status, indent=2, default=str))

except Exception as e:
    print(json.dumps({"error": str(e)}, indent=2))
finally:
    if ib.isConnected():
        ib.disconnect()
