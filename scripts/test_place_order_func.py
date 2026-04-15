#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from client.ib_connection import get_ib_connection
from orders.place_order_func import place_order

def test_place_gc():
    print("Getting IB connection...")
    ib = get_ib_connection()
    
    print(f"IB Connected: {ib.isConnected()}")
    
    result = place_order(
        ib,
        "GC",
        "BUY",
        1.0
    )
    
    print("Order Result:", repr(result))

if __name__ == "__main__":
    test_place_gc()