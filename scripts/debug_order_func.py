import sys
sys.path.insert(0, 'D:/projects/trading')
from client.ib_connection import get_ib_connection
from orders.place_order_func import place_order

ib = get_ib_connection()
print("IB connected")

# 用正确的参数调用
result = place_order(ib, "GC", "BUY", 1, sec_type="FUT", exchange="COMEX", use_main_contract=True)
print(f"Result: {result}")