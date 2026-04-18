#!/usr/bin/env python3
import subprocess
import sys

cmd = [sys.executable, "D:/projects/trading/orders/place_order_func.py", "--symbol", "GC", "--action", "BUY", "--quantity", "1"]
print(f"Running: {' '.join(cmd)}")

result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
print("stdout:", result.stdout[:500] if result.stdout else "(empty)")
print("stderr:", result.stderr[:500] if result.stderr else "(empty)")
print("returncode:", result.returncode)