"""
MT5 META AGENT V10 - FIBONACCI CALCULATOR (V2.021)
Calculates 12-zone Fibonacci retracement system with multipliers
Matches TradingView Pine Script V6 Fibonacci logic exactly
"""

import numpy as np
from typing import Dict, Tuple, Optional

# Fibonacci Zone Multipliers (from Pine Script inputs)
ZONE_MULTIPLIERS = {
    1: 0.0,    # Zone 1 (0.000-0.118)
    2: 0.0,    # Zone 2 (0.118-0.236)
    3: 0.7,    # Zone 3 (0.236-0.309)
    4: 4.4,    # Zone 4 (0.309-0.382)
    5: 0.0,    # Zone 5 (0.382-0.441)
    6: 6.0,    # Zone 6 (0.441-0.500)
    7: 6.0,    # Zone 7 (0.500-0.559)
    8: 6.8,    # Zone 8 (0.559-0.618)
    9: 6.0,    # Zone 9 (0.618-0.702) - GOLDEN ZONE START
    10: 10.0,  # Zone 10 (0.702-0.786) - GOLDEN ZONE END
    11: 0.5,   # Zone 11 (0.786-0.893)
    12: 1.3,   # Zone 12 (0.893-1.000)
    0: 1.0     # Zone 0 (outside range)
}

# Fibonacci Ratios (13 levels from 0.000 to 1.000)
FIB_RATIOS = [
    0.000,
    0.118,
    0.236,
    0.309,
    0.382,
    0.441,
    0.500,
    0.559,
    0.618,
    0.702,
    0.786,
    0.893,
    1.000
]

def calculate_fibonacci_levels(
    highs: np.ndarray,
    lows: np.ndarray,
    lookback_bars: int = 100
) -> Dict[str, float]:
    """
    Calculate all 13 Fibonacci retracement levels
    
    Args:
        highs: Array of high prices
        lows: Array of low prices
        lookback_bars: Period for swing high/low calculation
    
    Returns:
        Dictionary with pivot_high, pivot_low, fib_range, and all 13 fib levels
    """
    
    # Calculate swing high and low over lookback period
    pivot_high = np.max(highs[-lookback_bars:])
    pivot_low = np.min(lows[-lookback_bars:])
    fib_range = pivot_high - pivot_low
    
    # Calculate all 13 Fibonacci levels with explicit names matching database schema
    fib_levels = {
        'pivot_high': round(pivot_high, 5),
        'pivot_low': round(pivot_low, 5),
        'fib_range': round(fib_range, 5),
        'fib_level_0000': round(pivot_low + (fib_range * 0.000), 5),
        'fib_level_0118': round(pivot_low + (fib_range * 0.118), 5),
        'fib_level_0236': round(pivot_low + (fib_range * 0.236), 5),
        'fib_level_0309': round(pivot_low + (fib_range * 0.309), 5),
        'fib_level_0382': round(pivot_low + (fib_range * 0.382), 5),
        'fib_level_0441': round(pivot_low + (fib_range * 0.441), 5),
        'fib_level_0500': round(pivot_low + (fib_range * 0.500), 5),
        'fib_level_0559': round(pivot_low + (fib_range * 0.559), 5),
        'fib_level_0618': round(pivot_low + (fib_range * 0.618), 5),
        'fib_level_0702': round(pivot_low + (fib_range * 0.702), 5),
        'fib_level_0786': round(pivot_low + (fib_range * 0.786), 5),
        'fib_level_0893': round(pivot_low + (fib_range * 0.893), 5),
        'fib_level_1000': round(pivot_low + (fib_range * 1.000), 5)
    }
    
    return fib_levels


def determine_fib_zone(
    close_price: float,
    fib_levels: Dict[str, float]
) -> Tuple[int, bool, float, Optional[float]]:
    """
    Determine which Fibonacci zone the current price is in
    
    Args:
        close_price: Current close price
        fib_levels: Dictionary of Fibonacci levels from calculate_fibonacci_levels()
    
    Returns:
        Tuple of:
        - current_fib_zone (1-12, or 0 if outside range)
        - in_golden_zone (boolean)
        - zone_multiplier (float)
        - distance_to_next_level (float or None)
    """
    
    # Extract levels for zone determination
    levels = [
        fib_levels['fib_level_0000'],
        fib_levels['fib_level_0118'],
        fib_levels['fib_level_0236'],
        fib_levels['fib_level_0309'],
        fib_levels['fib_level_0382'],
        fib_levels['fib_level_0441'],
        fib_levels['fib_level_0500'],
        fib_levels['fib_level_0559'],
        fib_levels['fib_level_0618'],
        fib_levels['fib_level_0702'],
        fib_levels['fib_level_0786'],
        fib_levels['fib_level_0893'],
        fib_levels['fib_level_1000']
    ]
    
    # Determine zone (1-12)
    current_zone = 0
    distance_to_next = None
    
    for i in range(len(levels) - 1):
        if close_price >= levels[i] and close_price < levels[i + 1]:
            current_zone = i + 1
            distance_to_next = round(levels[i + 1] - close_price, 5)
            break
    
    # Check if at or above highest level
    if close_price >= levels[-1]:
        current_zone = 12
        distance_to_next = 0.0
    
    # Check if below lowest level
    if close_price < levels[0]:
        current_zone = 0
        distance_to_next = round(levels[0] - close_price, 5)
    
    # Golden Zone: Zones 9 and 10 (0.618-0.786)
    in_golden_zone = current_zone in [9, 10]
    
    # Get zone multiplier
    zone_multiplier = ZONE_MULTIPLIERS.get(current_zone, 1.0)
    
    return current_zone, in_golden_zone, zone_multiplier, distance_to_next


def calculate_fibonacci_data(
    highs: np.ndarray,
    lows: np.ndarray,
    close_price: float,
    lookback_bars: int = 100
) -> Dict[str, any]:
    """
    Complete Fibonacci calculation for a single bar
    Matches Pine Script V6 Fibonacci system exactly
    
    Args:
        highs: Array of high prices (needs at least lookback_bars)
        lows: Array of low prices (needs at least lookback_bars)
        close_price: Current close price
        lookback_bars: Period for swing high/low calculation
    
    Returns:
        Dictionary with all Fibonacci data ready for database insertion
    """
    
    if len(highs) < lookback_bars or len(lows) < lookback_bars:
        raise ValueError(f"Need at least {lookback_bars} bars for Fibonacci calculation")
    
    # Calculate all Fibonacci levels
    fib_levels = calculate_fibonacci_levels(highs, lows, lookback_bars)
    
    # Determine current zone
    current_zone, in_golden_zone, zone_multiplier, distance_to_next = determine_fib_zone(
        close_price, fib_levels
    )
    
    # Compile complete Fibonacci data
    fib_data = {
        # Anchors
        'pivot_high': fib_levels['pivot_high'],
        'pivot_low': fib_levels['pivot_low'],
        'fib_range': fib_levels['fib_range'],
        'lookback_bars': lookback_bars,
        
        # All 13 levels
        'fib_level_0000': fib_levels['fib_level_0000'],
        'fib_level_0118': fib_levels['fib_level_0118'],
        'fib_level_0236': fib_levels['fib_level_0236'],
        'fib_level_0309': fib_levels['fib_level_0309'],
        'fib_level_0382': fib_levels['fib_level_0382'],
        'fib_level_0441': fib_levels['fib_level_0441'],
        'fib_level_0500': fib_levels['fib_level_0500'],
        'fib_level_0559': fib_levels['fib_level_0559'],
        'fib_level_0618': fib_levels['fib_level_0618'],
        'fib_level_0702': fib_levels['fib_level_0702'],
        'fib_level_0786': fib_levels['fib_level_0786'],
        'fib_level_0893': fib_levels['fib_level_0893'],
        'fib_level_1000': fib_levels['fib_level_1000'],
        
        # Zone analysis
        'current_fib_zone': current_zone,
        'in_golden_zone': in_golden_zone,
        'zone_multiplier': zone_multiplier,
        'distance_to_next_level': distance_to_next,
        
        # Percentile (calculated separately later)
        'zone_time_percentile': None
    }
    
    return fib_data


# ============================================================================
# TESTING & VALIDATION
# ============================================================================

def test_fibonacci_calculator():
    """Test Fibonacci calculator with sample data"""
    
    print("="*70)
    print("FIBONACCI CALCULATOR TEST")
    print("="*70)
    
    # Sample price data (100 bars)
    np.random.seed(42)
    base_price = 2650.0
    highs = base_price + np.random.uniform(0, 50, 100)
    lows = base_price - np.random.uniform(0, 50, 100)
    
    # Current close price in golden zone (~0.65 retracement)
    pivot_high_test = np.max(highs)
    pivot_low_test = np.min(lows)
    test_close = pivot_low_test + ((pivot_high_test - pivot_low_test) * 0.65)
    
    print(f"\nTest Data:")
    print(f"  Pivot High: {pivot_high_test:.2f}")
    print(f"  Pivot Low: {pivot_low_test:.2f}")
    print(f"  Current Close: {test_close:.2f}")
    print(f"  Lookback: 100 bars")
    
    # Calculate Fibonacci
    fib_data = calculate_fibonacci_data(highs, lows, test_close, lookback_bars=100)
    
    print(f"\nFibonacci Results:")
    print(f"  Current Zone: {fib_data['current_fib_zone']}")
    print(f"  In Golden Zone: {fib_data['in_golden_zone']}")
    print(f"  Zone Multiplier: {fib_data['zone_multiplier']}")
    print(f"  Distance to Next Level: {fib_data['distance_to_next_level']}")
    
    print(f"\nFibonacci Levels:")
    level_names = [
        'fib_level_0000', 'fib_level_0118', 'fib_level_0236', 'fib_level_0309',
        'fib_level_0382', 'fib_level_0441', 'fib_level_0500', 'fib_level_0559',
        'fib_level_0618', 'fib_level_0702', 'fib_level_0786', 'fib_level_0893',
        'fib_level_1000'
    ]
    
    for i, (ratio, level_name) in enumerate(zip(FIB_RATIOS, level_names)):
        level_value = fib_data[level_name]
        in_zone = ""
        if i < len(level_names) - 1:
            next_level = fib_data[level_names[i + 1]]
            if test_close >= level_value and test_close < next_level:
                in_zone = " <-- CURRENT PRICE"
        elif i == len(level_names) - 1 and test_close >= level_value:
            in_zone = " <-- CURRENT PRICE"
        print(f"  {ratio:.3f}: {level_value:.2f}{in_zone}")
    
    print("\n" + "="*70)
    print("✓ Fibonacci calculator test complete")
    print("="*70)


if __name__ == "__main__":
    test_fibonacci_calculator()
