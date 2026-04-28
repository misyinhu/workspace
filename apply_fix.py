with open(r"D:\Projects\quant\quant_core\sources\tdx.py", "r", encoding="utf-8") as f:
    content = f.read()

with open(r"/tmp/tdx_fix.py", "r", encoding="utf-8") as f:
    new_method = f.read()

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
    with open(
        r"D:\Projects\quant\quant_core\sources\tdx.py", "w", encoding="utf-8"
    ) as f:
        f.write(new_content)
    print("Done")
