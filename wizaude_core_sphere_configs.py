# wizaude_core/sphere_configs.py
"""
SPHERE CONFIGURATIONS
Pre-defined sphere configurations for different market views.

These configurations are designed based on:
- Proven indicator combinations
- Market microstructure research
- Multi-period analysis for maximum adaptability

HIGH SUCCESS PROBABILITY CONFIGS are marked with ★
"""

from .sphere import SphereConfig

# ═══════════════════════════════════════════════════════════════════════════
# MOMENTUM-BASED SPHERES
# Best for: Trending markets, breakout trading
# ═══════════════════════════════════════════════════════════════════════════

MOMENTUM_FAST = SphereConfig(
    name="Momentum Fast",
    classifier_type="momentum",
    classifier_config={
        'rsi_period': 7,
        'momentum_period': 5,
        'roc_period': 5
    },
    lookback_window=200,
    decay_factor=0.95,  # Fast decay = recent data matters more
)

MOMENTUM_SLOW = SphereConfig(
    name="Momentum Slow",
    classifier_type="momentum",
    classifier_config={
        'rsi_period': 14,
        'momentum_period': 14,
        'roc_period': 14
    },
    lookback_window=1000,
    decay_factor=0.99,  # Slow decay = historical patterns matter
)

# ★ HIGH SUCCESS - Adapts to current market conditions
MOMENTUM_ADAPTIVE = SphereConfig(
    name="Momentum Adaptive",
    classifier_type="multi_period",
    classifier_config={
        'indicator': 'momentum',
        'short_periods': [1, 2, 3],
        'medium_periods': [5, 7, 9],
        'long_periods': [11, 13, 14]
    },
    lookback_window=500,
    decay_factor=0.97,
)

# ═══════════════════════════════════════════════════════════════════════════
# VOLATILITY-BASED SPHERES
# Best for: Regime detection, breakout confirmation
# ═══════════════════════════════════════════════════════════════════════════

VOLATILITY_BREAKOUT = SphereConfig(
    name="Volatility Breakout",
    classifier_type="volatility",
    classifier_config={
        'atr_period': 14,
        'bb_period': 20,
        'adx_period': 14
    },
    lookback_window=300,
    decay_factor=0.96,
)

VOLATILITY_SQUEEZE = SphereConfig(
    name="Volatility Squeeze",
    classifier_type="volatility",
    classifier_config={
        'atr_period': 10,
        'bb_period': 14,
        'adx_period': 10
    },
    lookback_window=200,
    decay_factor=0.94,
)

# ═══════════════════════════════════════════════════════════════════════════
# OSCILLATOR-BASED SPHERES
# Best for: Mean reversion, extreme detection
# ═══════════════════════════════════════════════════════════════════════════

# ★ HIGH SUCCESS - Multiple oscillators must agree
OSCILLATOR_CONFLUENCE = SphereConfig(
    name="Oscillator Confluence",
    classifier_type="oscillator",
    classifier_config={
        'period': 14
    },
    lookback_window=400,
    decay_factor=0.97,
)

OSCILLATOR_FAST = SphereConfig(
    name="Oscillator Fast",
    classifier_type="oscillator",
    classifier_config={
        'period': 7
    },
    lookback_window=200,
    decay_factor=0.94,
)

# ★ HIGH SUCCESS - Detects when short/long periods diverge
RSI_MULTI_PERIOD = SphereConfig(
    name="RSI Multi-Period",
    classifier_type="multi_period",
    classifier_config={
        'indicator': 'rsi',
        'short_periods': [2, 3, 4],
        'medium_periods': [6, 7, 8],
        'long_periods': [10, 12, 14]
    },
    lookback_window=500,
    decay_factor=0.97,
)

# ═══════════════════════════════════════════════════════════════════════════
# VOLUME-BASED SPHERES
# Best for: Confirmation, accumulation/distribution detection
# ═══════════════════════════════════════════════════════════════════════════

VOLUME_CONFIRMATION = SphereConfig(
    name="Volume Confirmation",
    classifier_type="volume",
    classifier_config={
        'cmf_period': 14
    },
    lookback_window=300,
    decay_factor=0.96,
)

VOLUME_FAST = SphereConfig(
    name="Volume Fast",
    classifier_type="volume",
    classifier_config={
        'cmf_period': 7
    },
    lookback_window=150,
    decay_factor=0.93,
)

# ═══════════════════════════════════════════════════════════════════════════
# COMPOSITE SPHERES (MOST POWERFUL)
# Best for: All-around performance, highest success probability
# ═══════════════════════════════════════════════════════════════════════════

# ★★ HIGHEST SUCCESS - Balanced combination of all factors
COMPOSITE_BALANCED = SphereConfig(
    name="Composite Balanced",
    classifier_type="composite",
    classifier_config={
        'momentum': {'rsi_period': 14, 'momentum_period': 10, 'roc_period': 10},
        'volatility': {'atr_period': 14, 'bb_period': 20, 'adx_period': 14},
        'oscillator': {'period': 14},
        'volume': {'cmf_period': 14},
        'weights': {
            'momentum': 0.30,
            'volatility': 0.25,
            'oscillator': 0.25,
            'volume': 0.20
        }
    },
    lookback_window=500,
    decay_factor=0.97,
)

# ★ HIGH SUCCESS - For trending markets
COMPOSITE_MOMENTUM_HEAVY = SphereConfig(
    name="Composite Momentum Heavy",
    classifier_type="composite",
    classifier_config={
        'momentum': {'rsi_period': 10, 'momentum_period': 7, 'roc_period': 7},
        'volatility': {'atr_period': 14, 'bb_period': 14, 'adx_period': 14},
        'oscillator': {'period': 10},
        'volume': {'cmf_period': 10},
        'weights': {
            'momentum': 0.50,
            'volatility': 0.20,
            'oscillator': 0.20,
            'volume': 0.10
        }
    },
    lookback_window=300,
    decay_factor=0.95,
)

# ★ HIGH SUCCESS - For volatile markets
COMPOSITE_VOLATILITY_AWARE = SphereConfig(
    name="Composite Volatility Aware",
    classifier_type="composite",
    classifier_config={
        'momentum': {'rsi_period': 14, 'momentum_period': 14, 'roc_period': 14},
        'volatility': {'atr_period': 14, 'bb_period': 20, 'adx_period': 14},
        'oscillator': {'period': 14},
        'volume': {'cmf_period': 14},
        'weights': {
            'momentum': 0.25,
            'volatility': 0.40,
            'oscillator': 0.20,
            'volume': 0.15
        }
    },
    lookback_window=400,
    decay_factor=0.96,
)

# Mean reversion focused
COMPOSITE_MEAN_REVERSION = SphereConfig(
    name="Composite Mean Reversion",
    classifier_type="composite",
    classifier_config={
        'momentum': {'rsi_period': 7, 'momentum_period': 5, 'roc_period': 5},
        'volatility': {'atr_period': 10, 'bb_period': 14, 'adx_period': 10},
        'oscillator': {'period': 7},
        'volume': {'cmf_period': 7},
        'weights': {
            'momentum': 0.20,
            'volatility': 0.25,
            'oscillator': 0.40,  # Heavy oscillator weight for extremes
            'volume': 0.15
        }
    },
    lookback_window=250,
    decay_factor=0.94,
)

# ═══════════════════════════════════════════════════════════════════════════
# SYMBOL-SPECIFIC SPHERE FACTORIES
# Best for: Asset-specific optimization
# ═══════════════════════════════════════════════════════════════════════════

def create_gold_sphere(name_suffix: str = "") -> SphereConfig:
    """
    Gold-optimized sphere configuration.
    
    Gold characteristics:
    - Session-driven (London fix, NY close)
    - Volatility-sensitive
    - Tends to trend within sessions
    """
    return SphereConfig(
        name=f"Gold Specialist{' ' + name_suffix if name_suffix else ''}",
        classifier_type="composite",
        classifier_config={
            'momentum': {'rsi_period': 14, 'momentum_period': 10, 'roc_period': 10},
            'volatility': {'atr_period': 14, 'bb_period': 20, 'adx_period': 14},
            'oscillator': {'period': 14},
            'volume': {'cmf_period': 14},
            'weights': {
                'momentum': 0.35,
                'volatility': 0.30,  # Gold is volatility-sensitive
                'oscillator': 0.20,
                'volume': 0.15
            }
        },
        symbol='XAUUSD',
        timeframe='15m',
        lookback_window=500,
        decay_factor=0.97,
    )


def create_btc_sphere(name_suffix: str = "") -> SphereConfig:
    """
    Bitcoin-optimized sphere configuration.
    
    BTC characteristics:
    - 24/7 trading
    - Highly momentum-driven
    - Faster regime changes
    """
    return SphereConfig(
        name=f"BTC Specialist{' ' + name_suffix if name_suffix else ''}",
        classifier_type="composite",
        classifier_config={
            'momentum': {'rsi_period': 10, 'momentum_period': 7, 'roc_period': 7},
            'volatility': {'atr_period': 10, 'bb_period': 14, 'adx_period': 10},
            'oscillator': {'period': 10},
            'volume': {'cmf_period': 10},
            'weights': {
                'momentum': 0.40,  # BTC is momentum-driven
                'volatility': 0.25,
                'oscillator': 0.20,
                'volume': 0.15
            }
        },
        symbol='BTCUSD',
        timeframe='15m',
        lookback_window=300,
        decay_factor=0.95,  # Faster adaptation for crypto
    )


def create_nasdaq_sphere(name_suffix: str = "") -> SphereConfig:
    """
    NASDAQ-optimized sphere configuration.
    
    NASDAQ characteristics:
    - Session-based (US market hours)
    - Gap-sensitive
    - Volume important at open/close
    """
    return SphereConfig(
        name=f"NASDAQ Specialist{' ' + name_suffix if name_suffix else ''}",
        classifier_type="composite",
        classifier_config={
            'momentum': {'rsi_period': 14, 'momentum_period': 14, 'roc_period': 14},
            'volatility': {'atr_period': 14, 'bb_period': 20, 'adx_period': 14},
            'oscillator': {'period': 14},
            'volume': {'cmf_period': 14},
            'weights': {
                'momentum': 0.30,
                'volatility': 0.25,
                'oscillator': 0.25,
                'volume': 0.20  # Volume matters for indices
            }
        },
        symbol='NAS100',
        timeframe='15m',
        lookback_window=500,
        decay_factor=0.97,
    )


def create_oil_sphere(name_suffix: str = "") -> SphereConfig:
    """
    Oil-optimized sphere configuration.
    
    Oil characteristics:
    - Highly volatile
    - News-driven spikes
    - Trend-following works well
    """
    return SphereConfig(
        name=f"Oil Specialist{' ' + name_suffix if name_suffix else ''}",
        classifier_type="composite",
        classifier_config={
            'momentum': {'rsi_period': 10, 'momentum_period': 7, 'roc_period': 7},
            'volatility': {'atr_period': 14, 'bb_period': 14, 'adx_period': 14},
            'oscillator': {'period': 10},
            'volume': {'cmf_period': 10},
            'weights': {
                'momentum': 0.35,
                'volatility': 0.35,  # Oil is very volatile
                'oscillator': 0.15,
                'volume': 0.15
            }
        },
        symbol='USOIL',
        timeframe='15m',
        lookback_window=400,
        decay_factor=0.95,
    )


# ═══════════════════════════════════════════════════════════════════════════
# DEFAULT SPHERE SETS
# ═══════════════════════════════════════════════════════════════════════════

# Core set of spheres for any symbol
DEFAULT_SPHERE_CONFIGS = [
    MOMENTUM_FAST,
    MOMENTUM_SLOW,
    MOMENTUM_ADAPTIVE,
    VOLATILITY_BREAKOUT,
    VOLATILITY_SQUEEZE,
    OSCILLATOR_CONFLUENCE,
    OSCILLATOR_FAST,
    RSI_MULTI_PERIOD,
    VOLUME_CONFIRMATION,
    COMPOSITE_BALANCED,
    COMPOSITE_MOMENTUM_HEAVY,
    COMPOSITE_VOLATILITY_AWARE,
    COMPOSITE_MEAN_REVERSION,
]

# Symbol-specific defaults
GOLD_SPHERE_CONFIGS = [
    create_gold_sphere("Momentum"),
    create_gold_sphere("Volatility"),
    create_gold_sphere("Balanced"),
]

BTC_SPHERE_CONFIGS = [
    create_btc_sphere("Momentum"),
    create_btc_sphere("Volatility"),
    create_btc_sphere("Balanced"),
]

NASDAQ_SPHERE_CONFIGS = [
    create_nasdaq_sphere("Momentum"),
    create_nasdaq_sphere("Volatility"),
    create_nasdaq_sphere("Balanced"),
]

OIL_SPHERE_CONFIGS = [
    create_oil_sphere("Momentum"),
    create_oil_sphere("Volatility"),
    create_oil_sphere("Balanced"),
]

# ═══════════════════════════════════════════════════════════════════════════
# HIGH SUCCESS PROBABILITY CONFIGURATIONS
# These are the recommended starting point
# ═══════════════════════════════════════════════════════════════════════════

HIGH_SUCCESS_CONFIGS = [
    MOMENTUM_ADAPTIVE,        # Multi-period momentum detection
    RSI_MULTI_PERIOD,         # Multi-period RSI for divergence
    OSCILLATOR_CONFLUENCE,    # Multiple oscillators agreeing
    COMPOSITE_BALANCED,       # Best all-around performer
    COMPOSITE_VOLATILITY_AWARE,  # For volatile markets
]
