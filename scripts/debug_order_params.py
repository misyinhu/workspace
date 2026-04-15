#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from orders.place_order_func import place_order
from unittest.mock import Mock, MagicMock


def test_sec_type_branch():

    mock_ib = Mock()
    
    gc_contract = __import__('ib_insync', fromlist=['Future']).Future(
        conId=430360630,
        symbol='GC',
        lastTradeDateOrContractMonth='20260626',
        multiplier='100',
        exchange='COMEX',
        currency='USD',
        localSymbol='GCM6',
        tradingClass='GC'
    )

    mock_ib.positions = MagicMock(return_value=[])

    def side_effect_details(*args, **kwargs):
        class MockDetail:
            def __init__(self, contract):
                self.contract = contract
        return [MockDetail(gc_contract)]

    mock_ib.reqContractDetails = MagicMock(side_effect=side_effect_details)

    mock_trade = Mock()
    mock_trade.orderStatus.status = 'Filled'
    mock_trade.orderStatus.filled = 1
    mock_trade.orderStatus.remaining = 0
    mock_trade.orderStatus.avgFillPrice = 48190.00
    mock_trade.order.orderId = 19
    mock_trade.order.totalQuantity = 1
    mock_trade.log = []
    mock_ib.placeOrder = MagicMock(return_value=mock_trade)

    print("Calling place_order")
    result = place_order(
        ib=mock_ib,
        symbol='GC',
        action='BUY',
        quantity=1,
        sec_type='FUT',
        exchange='COMEX'
    )

    print("\n=== PLACE ORDER RETURN ===")
    print(result)
    print()
    
    print("\n=== MOCK PLACE ORDER CALL ===")
    print(f"Times called: {mock_ib.placeOrder.call_count}")
    for call in mock_ib.placeOrder.call_args_list:
        print()
        args, kwargs = call
        print(f"Call args: {args}")
        print()
        if len(args) >1:
            contract, order = args[:2]
            print(f"  Contract: {contract}")
            print(f"  Order: {order}")
            print(f"  Action: {order.action}")
            print(f"  Total Quantity: {order.totalQuantity}")
            print(f"  Order Type: {order.orderType}")
            print(f"  Cash Quantity: {getattr(order, 'cashQty', None)}")
            print(f"  Time in Force: {getattr(order, 'tif', None)}")


if __name__ == "__main__":

    print("=== Debugging order parameter branch ===")

    try:
        import traceback
        test_sec_type_branch()
        
    except Exception as e:
        print(f"Test failed: {type(e)} - {e}")
        print()
        print(traceback.format_exc())

