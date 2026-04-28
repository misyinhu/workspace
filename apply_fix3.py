#!/usr/bin/env python3
new_method = '''def get_history_batch(self, symbols: List[str], num: int = 100, timeframe: str = "1d") -> Dict[str, List[Bar]]:
        """Batch get history for multiple symbols using TDX batch API."""
        from typing import Dict
        tq_obj = self._get_tq()
        if not tq_obj:
            return {s: [] for s in symbols}
        
        normalized_map = {}
        for symbol in symbols:
            upper = symbol.upper()
            if upper.startswith("SSE:"):
                normalized_map[symbol] = upper.replace("SSE:", "") + ".SH"
            elif upper.startswith("SZSE:"):
                normalized_map[symbol] = upper.replace("SZSE:", "") + ".SZ"
            elif upper.startswith("HKEX:"):
                normalized_map[symbol] = upper.replace("HKEX:", "") + ".HK"
            else:
                normalized_map[symbol] = upper
        
        normalized_list = list(normalized_map.values())
        period = self._bar_size_to_period(timeframe)
        count = num or 100
        
        try:
            df_dict = tq_obj.get_market_data(
                field_list=["Open", "High", "Low", "Close", "Volume"],
                stock_list=normalized_list,
                period=period,
                count=count,
            )
        except Exception:
            return {s: [] for s in symbols}
        
        if not df_dict or not isinstance(df_dict, dict):
            return {s: [] for s in symbols}
        
        reverse_map = {v: k for k, v in normalized_map.items()}
        result: Dict[str, List[Bar]] = {s: [] for s in symbols}
        
        all_timestamps = []
        close_df = df_dict.get("Close")
        if close_df is not None and hasattr(close_df, "index"):
            all_timestamps = sorted(pd.to_datetime(close_df.index).unique().tolist())
        
        if not all_timestamps:
            return result
        
        for normalized_sym in normalized_list:
            original_sym = reverse_map.get(normalized_sym, normalized_sym)
            bars_list = []
            
            for ts in all_timestamps:
                bar = Bar(
                    timestamp=ts,
                    open=0.0, high=0.0, low=0.0, close=0.0, volume=0.0,
                    symbol=original_sym,
                    source=self.source_name,
                )
                
                for field_name, df in df_dict.items():
                    if not hasattr(df, "iterrows"):
                        continue
                    if normalized_sym not in df.columns:
                        continue
                    try:
                        if ts in df.index:
                            value = df.loc[ts, normalized_sym]
                            if pd.notna(value):
                                fl = field_name.lower()
                                if fl == "open":
                                    bar.open = float(value)
                                elif fl == "high":
                                    bar.high = float(value)
                                elif fl == "low":
                                    bar.low = float(value)
                                elif fl == "close":
                                    bar.close = float(value)
                                elif fl == "volume":
                                    bar.volume = float(value)
                    except (KeyError, TypeError, ValueError):
                        continue
                
                bars_list.append(bar)
            
            result[original_sym] = bars_list
        
        return result

'''

import os

tdx_path = r"D:\Projects\quant\quant_core\sources\tdx.py"
with open(tdx_path, "r", encoding="utf-8") as f:
    content = f.read()

start_marker = "def get_history_batch(self"
end_marker = "def _bar_size_to_period"
start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print(f"ERROR: markers not found: start={start_idx}, end={end_idx}")
else:
    print(
        f"Replacing {len(content[start_idx:end_idx])} chars with {len(new_method)} chars"
    )
    new_content = content[:start_idx] + new_method + content[end_idx:]
    with open(tdx_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("DONE")
