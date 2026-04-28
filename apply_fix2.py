#!/usr/bin/env python3
import os

# Read new method
new_method_path = os.path.join(os.path.dirname(__file__), "..", "temp_tdx_fix.py")
tdx_path = r"D:\Projects\quant\quant_core\sources\tdx.py"
fix_path = r"D:\temp_tdx_fix.py"

# Use relative path since we're running from CXClaw
with open(
    r"C:\Users\Apple\AppData\Local\Temp\temp_tdx_fix.py", "r", encoding="utf-8"
) as f:
    new_method = f.read()

with open(tdx_path, "r", encoding="utf-8") as f:
    content = f.read()

start_marker = "def get_history_batch(self"
end_marker = "def _bar_size_to_period"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print(f"Markers not found: start={start_idx}, end={end_idx}")
else:
    print(
        f"Replacing {len(content[start_idx:end_idx])} chars with {len(new_method)} chars"
    )
    new_content = content[:start_idx] + new_method + content[end_idx:]
    with open(tdx_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Done")
