def get_history_batch(
    self, symbols: List[str], num: int = 100, timeframe: str = "1d"
) -> Dict[str, List[Bar]]:
    """Batch get history for multiple symbols using TDX batch API.

    TDX returns data as dict of DataFrames, one per field (Open/High/Low/Close/Volume).
    Each DataFrame has timestamps as index and stock symbols as columns.
    """
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

    all_timestamps: List[datetime] = []
    close_df = df_dict.get("Close")
    if close_df is not None and hasattr(close_df, "index"):
        all_timestamps = sorted(pd.to_datetime(close_df.index).unique().tolist())

    if not all_timestamps:
        return result

    for normalized_sym in normalized_list:
        original_sym = reverse_map.get(normalized_sym, normalized_sym)
        bars_list: List[Bar] = []

        for ts in all_timestamps:
            bar = Bar(
                timestamp=ts,
                open=0.0,
                high=0.0,
                low=0.0,
                close=0.0,
                volume=0.0,
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
                            field_lower = field_name.lower()
                            if field_lower == "open":
                                bar.open = float(value)
                            elif field_lower == "high":
                                bar.high = float(value)
                            elif field_lower == "low":
                                bar.low = float(value)
                            elif field_lower == "close":
                                bar.close = float(value)
                            elif field_lower == "volume":
                                bar.volume = float(value)
                except (KeyError, TypeError, ValueError):
                    continue

            bars_list.append(bar)

        result[original_sym] = bars_list

    return result
