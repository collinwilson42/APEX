"""
MT5 META AGENT V10 - ATH (ALL-TIME HIGH) CALCULATOR (V2.032)
Tracks distance from all-time high with dynamic multiplier mapping
Matches TradingView Pine Script ATH system exactly
"""

import numpy as np
from typing import Dict, Tuple

# ATH Configuration (from Pine Script inputs)
DEFAULT_ATH_LOOKBACK = 500           # Bars to scan for ATH
DEFAULT_MIN_THRESHOLD = -3.0         # Min % from ATH (gets min multiplier)
DEFAULT_MAX_THRESHOLD = 1.0          # Max % from ATH (gets max multiplier)
DEFAULT_MULT_MIN = 0.0               # Multiplier at min threshold
DEFAULT_MULT_MAX = 2.0               # Multiplier at max threshold

# Zone Classifications
ZONE_NEAR_ATH = "NEAR_ATH"           # Within 1% of ATH
ZONE_MID_RANGE = "MID_RANGE"         # Between -1% and -2.5%
ZONE_FAR_ATH = "FAR_ATH"             # More than -2.5% from ATH


def calculate_ath(
    highs: np.ndarray,
    lookback_bars: int = DEFAULT_ATH_LOOKBACK
) -> float:
    """
    Calculate all-time high over lookback period
    
    Args:
        highs: Array of high prices
        lookback_bars: Number of bars to scan for ATH
    
    Returns:
        All-time high value
    """
    if len(highs) < lookback_bars:
        lookback_bars = len(highs)
    
    ath = np.max(highs[-lookback_bars:])
    return round(ath, 5)


def calculate_ath_distance(
    current_close: float,
    ath: float
) -> Tuple[float, float]:
    """
    Calculate distance from all-time high
    
    Args:
        current_close: Current close price
        ath: All-time high value
    
    Returns:
        Tuple of (distance_points, distance_pct)
    """
    distance_points = current_close - ath
    distance_pct = ((current_close - ath) / ath) * 100
    
    return round(distance_points, 5), round(distance_pct, 5)


def calculate_ath_multiplier(
    distance_pct: float,
    min_threshold: float = DEFAULT_MIN_THRESHOLD,
    max_threshold: float = DEFAULT_MAX_THRESHOLD,
    mult_min: float = DEFAULT_MULT_MIN,
    mult_max: float = DEFAULT_MULT_MAX
) -> float:
    """
    Calculate dynamic multiplier based on ATH distance
    Uses linear interpolation between thresholds
    Matches Pine Script V6 ATH multiplier logic exactly
    
    Args:
        distance_pct: Distance from ATH as percentage
        min_threshold: Min % threshold (e.g., -3.0)
        max_threshold: Max % threshold (e.g., 1.0)
        mult_min: Multiplier at min threshold (e.g., 0.0)
        mult_max: Multiplier at max threshold (e.g., 2.0)
    
    Returns:
        Calculated multiplier (clamped to min/max range)
    """
    # Below min threshold - return min multiplier
    if distance_pct <= min_threshold:
        return mult_min
    
    # Above max threshold - return max multiplier
    if distance_pct >= max_threshold:
        return mult_max
    
    # Between thresholds - linear interpolation
    threshold_range = max_threshold - min_threshold
    multiplier_range = mult_max - mult_min
    distance_ratio = (distance_pct - min_threshold) / threshold_range
    
    multiplier = mult_min + (distance_ratio * multiplier_range)
    
    return round(multiplier, 5)


def classify_ath_zone(
    distance_pct: float
) -> str:
    """
    Classify current position relative to ATH
    
    Args:
        distance_pct: Distance from ATH as percentage
    
    Returns:
        Zone classification: NEAR_ATH / MID_RANGE / FAR_ATH
    """
    if distance_pct >= -1.0:
        return ZONE_NEAR_ATH
    elif distance_pct >= -2.5:
        return ZONE_MID_RANGE
    else:
        return ZONE_FAR_ATH


def calculate_ath_data(
    highs: np.ndarray,
    current_close: float,
    lookback_bars: int = DEFAULT_ATH_LOOKBACK,
    min_threshold: float = DEFAULT_MIN_THRESHOLD,
    max_threshold: float = DEFAULT_MAX_THRESHOLD,
    mult_min: float = DEFAULT_MULT_MIN,
    mult_max: float = DEFAULT_MULT_MAX
) -> Dict[str, any]:
    """
    Complete ATH calculation for a single bar
    Matches Pine Script V6 ATH system exactly
    
    Args:
        highs: Array of high prices (needs at least lookback_bars)
        current_close: Current close price
        lookback_bars: Period for ATH calculation
        min_threshold: Min % threshold for multiplier
        max_threshold: Max % threshold for multiplier
        mult_min: Multiplier at min threshold
        mult_max: Multiplier at max threshold
    
    Returns:
        Dictionary with all ATH data ready for database insertion
    """
    if len(highs) < 1:
        raise ValueError("Need at least 1 bar for ATH calculation")
    
    # Calculate ATH
    ath = calculate_ath(highs, lookback_bars)
    
    # Calculate distance
    distance_points, distance_pct = calculate_ath_distance(current_close, ath)
    
    # Calculate multiplier
    multiplier = calculate_ath_multiplier(
        distance_pct,
        min_threshold,
        max_threshold,
        mult_min,
        mult_max
    )
    
    # Classify zone
    zone = classify_ath_zone(distance_pct)
    
    # Compile complete ATH data
    ath_data = {
        # ATH Calculation
        'current_ath': ath,
        'ath_lookback_bars': min(lookback_bars, len(highs)),
        
        # Current Price
        'current_close': current_close,
        
        # Distance Metrics
        'ath_distance_points': distance_points,
        'ath_distance_pct': distance_pct,
        
        # Multiplier Configuration
        'ath_min_threshold': min_threshold,
        'ath_max_threshold': max_threshold,
        'ath_multiplier': multiplier,
        
        # Zone Classification
        'ath_zone': zone,
        
        # Percentile (calculated separately later)
        'distance_from_ath_percentile': None
    }
    
    return ath_data


# ============================================================================
# TESTING & VALIDATION
# ============================================================================

def test_ath_calculator():
    """Test ATH calculator with sample scenarios"""
    
    print("="*70)
    print("ATH CALCULATOR TEST")
    print("="*70)
    
    # Sample price data (500 bars with uptrend)
    np.random.seed(42)
    base_prices = np.linspace(2500, 2680, 500)  # Uptrend
    noise = np.random.uniform(-10, 10, 500)
    highs = base_prices + noise + 5  # Highs slightly above base
    
    print(f"\nTest Data:")
    print(f"  Bars: 500")
    print(f"  Range: ${base_prices[0]:.2f} - ${base_prices[-1]:.2f}")
    print(f"  ATH: ${np.max(highs):.2f}")
    
    # Test Scenario 1: Near ATH (bullish)
    print(f"\n{'='*70}")
    print("SCENARIO 1: NEAR ATH (Bullish)")
    print('='*70)
    ath_value = np.max(highs)
    close_near = ath_value - 5.0  # 5 points below ATH
    
    ath_data_1 = calculate_ath_data(highs, close_near)
    
    print(f"  Current Close: ${close_near:.2f}")
    print(f"  ATH: ${ath_data_1['current_ath']:.2f}")
    print(f"  Distance: {ath_data_1['ath_distance_points']:.2f} pts ({ath_data_1['ath_distance_pct']:.2f}%)")
    print(f"  Multiplier: {ath_data_1['ath_multiplier']:.2f}x")
    print(f"  Zone: {ath_data_1['ath_zone']}")
    print(f"  Assessment: {get_assessment(ath_data_1['ath_multiplier'])}")
    
    # Test Scenario 2: Mid-Range (neutral)
    print(f"\n{'='*70}")
    print("SCENARIO 2: MID-RANGE (Neutral)")
    print('='*70)
    close_mid = ath_value - 40.0  # ~1.5% below ATH
    
    ath_data_2 = calculate_ath_data(highs, close_mid)
    
    print(f"  Current Close: ${close_mid:.2f}")
    print(f"  ATH: ${ath_data_2['current_ath']:.2f}")
    print(f"  Distance: {ath_data_2['ath_distance_points']:.2f} pts ({ath_data_2['ath_distance_pct']:.2f}%)")
    print(f"  Multiplier: {ath_data_2['ath_multiplier']:.2f}x")
    print(f"  Zone: {ath_data_2['ath_zone']}")
    print(f"  Assessment: {get_assessment(ath_data_2['ath_multiplier'])}")
    
    # Test Scenario 3: Far from ATH (weak)
    print(f"\n{'='*70}")
    print("SCENARIO 3: FAR FROM ATH (Weak)")
    print('='*70)
    close_far = ath_value - 100.0  # ~3.7% below ATH
    
    ath_data_3 = calculate_ath_data(highs, close_far)
    
    print(f"  Current Close: ${close_far:.2f}")
    print(f"  ATH: ${ath_data_3['current_ath']:.2f}")
    print(f"  Distance: {ath_data_3['ath_distance_points']:.2f} pts ({ath_data_3['ath_distance_pct']:.2f}%)")
    print(f"  Multiplier: {ath_data_3['ath_multiplier']:.2f}x")
    print(f"  Zone: {ath_data_3['ath_zone']}")
    print(f"  Assessment: {get_assessment(ath_data_3['ath_multiplier'])}")
    
    # Test Scenario 4: New ATH (maximum bullish)
    print(f"\n{'='*70}")
    print("SCENARIO 4: NEW ATH (Maximum Bullish)")
    print('='*70)
    close_new_ath = ath_value + 10.0  # Breaking new ATH
    
    highs_with_new = np.append(highs, close_new_ath)
    ath_data_4 = calculate_ath_data(highs_with_new, close_new_ath)
    
    print(f"  Current Close: ${close_new_ath:.2f}")
    print(f"  ATH: ${ath_data_4['current_ath']:.2f}")
    print(f"  Distance: {ath_data_4['ath_distance_points']:.2f} pts ({ath_data_4['ath_distance_pct']:.2f}%)")
    print(f"  Multiplier: {ath_data_4['ath_multiplier']:.2f}x")
    print(f"  Zone: {ath_data_4['ath_zone']}")
    print(f"  Assessment: {get_assessment(ath_data_4['ath_multiplier'])}")
    
    print("\n" + "="*70)
    print("✓ ATH calculator test complete")
    print("="*70)


def get_assessment(multiplier: float) -> str:
    """Get qualitative assessment of multiplier strength"""
    if multiplier >= 1.8:
        return "🟢 PREMIUM SETUP - Very near ATH"
    elif multiplier >= 1.4:
        return "🟢 STRONG SETUP - Near ATH"
    elif multiplier >= 1.0:
        return "🟡 GOOD SETUP - Moderate distance"
    elif multiplier >= 0.5:
        return "🟡 WEAK SETUP - Far from ATH"
    else:
        return "🔴 POOR SETUP - Very far from ATH"


if __name__ == "__main__":
    test_ath_calculator()
