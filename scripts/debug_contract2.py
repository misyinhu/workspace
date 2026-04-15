import sys
sys.path.insert(0, 'D:/projects/trading')

from ib_insync import IB, Future
from client.ib_connection import get_ib_connection

ib = get_ib_connection()
print("IB connected")

# Try COMEX instead of SMART
base_contract = Future("GC", exchange="COMEX", currency="USD")
print(f"Asking for: {base_contract}")

details = ib.reqContractDetails(base_contract)
print(f"Got {len(details)} contract details")

for i, d in enumerate(details[:5]):
    c = d.contract
    print(f"  {i}: {c.symbol} {c.localSymbol} conId={c.conId} expiry={c.lastTradeDateOrContractMonth}")