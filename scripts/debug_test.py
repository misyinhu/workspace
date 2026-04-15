import sys
sys.path.insert(0, 'D:/projects/trading')

# Test 1: Parse
print("=== Test 1: Parse ===")
from notify.nl_parser import parse_trading_command
r = parse_trading_command("买入1手GC")
print(f"action: {r['action']}, symbol: {r['symbol']}, qty: {r['quantity']}")
print(f"Types: action={type(r['action'])}, symbol={type(r['symbol'])}, qty={type(r['quantity'])}")

# Test 2: Sec type
print("\n=== Test 2: Sec Type ===")
symbol = r['symbol']
sec = "FUT" if symbol in ("GC", "ES", "NQ", "YM", "ZB", "ZN") else "STK"
print(f"symbol={symbol}, sec_type={sec}")

# Test 3: Place order
print("\n=== Test 3: Place Order ===")
from client.ib_connection import get_ib_connection
from orders.place_order_func import place_order

ib = get_ib_connection()
print("IB connected")

action = r['action']
quantity = r['quantity']

result = place_order(ib, symbol, action, quantity, sec_type=sec, use_main_contract=True)
print(f"Result: {result}")