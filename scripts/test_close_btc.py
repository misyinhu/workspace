import asyncio
import sys
sys.path.insert(0, 'D:/projects/trading')
from ib_insync import IB, MarketOrder
from client.ib_connection import get_ib_connection

async def close_btc():
    ib = get_ib_connection()
    
    positions = ib.positions()
    pos = None
    for p in positions:
        if p.contract.symbol == 'BTC':
            pos = p
            break
    
    if pos:
        print(f"Found position: {pos.position} {pos.contract.symbol}")
        print(f"Contract: secType={pos.contract.secType}, localSymbol={pos.contract.localSymbol}, conId={pos.contract.conId}")
        
        order = MarketOrder(action="SELL", totalQuantity=abs(pos.position))
        trade = ib.placeOrder(pos.contract, order)
        
        print(f"Order placed: {trade.order.orderId}")
        print(f"Status: {trade.orderStatus.status}")
        
        for log in trade.log:
            print(f"  Log: {log.status} - {log.message}")
    
    ib.disconnect()

asyncio.run(close_btc())