import asyncio
from ib_insync import IB

ib = IB()
ib.connect('127.0.0.1', 4002, clientId=99)
positions = ib.positions()
for p in positions:
    if p.contract.symbol == 'BTC':
        print(f'symbol: {p.contract.symbol}')
        print(f'secType: {p.contract.secType}')
        print(f'exchange: {p.contract.exchange}')
        print(f'conId: {p.contract.conId}')
        print(f'localSymbol: {p.contract.localSymbol}')
        print(f'position: {p.position}')
        break