"""Direct IB API test for different bar sizes"""

import sys
from ib_insync import IB, Future

ib = IB()

host = "100.82.238.11"
port = 4002
client_id = 99

print(f"Connecting to {host}:{port} with client_id={client_id}...")
ib.connect(host, port, clientId=client_id)

if not ib.isConnected():
    print("Failed to connect!")
    sys.exit(1)

print("Connected!")

contract = Future(symbol="MNQ")
details = ib.reqContractDetails(contract)

if not details:
    print("No contract details found!")
    ib.disconnect()
    sys.exit(1)

c = details[0].contract
print(f"Contract: {c.symbol} {c.exchange} {c.lastTradeDateOrContractMonth}")

bar_sizes = ["1 min", "5 mins", "30 mins", "1 hour", "1 day"]

for bar_size in bar_sizes:
    print(f"\n--- Testing bar_size={bar_size} ---")
    bars = ib.reqHistoricalData(
        contract=c,
        endDateTime="",
        durationStr="2 D",
        barSizeSetting=bar_size,
        whatToShow="TRADES",
        useRTH=False,
        formatDate=1,
    )

    if bars:
        print(f"Got {len(bars)} bars")
        for b in bars[-3:]:
            print(f"  {b.date} close={b.close}")
    else:
        print("No bars returned!")

ib.disconnect()
print("\nDone!")
