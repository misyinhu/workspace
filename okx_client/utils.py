from typing import List, Optional

def calculate_ema(values: List[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    
    multiplier = 2 / (period + 1)
    ema = sum(values[:period]) / period
    
    for value in values[period:]:
        ema = (value - ema) * multiplier + ema
    return ema
