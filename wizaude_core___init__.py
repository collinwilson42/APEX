# wizaude_core/__init__.py
"""
WIZAUDE HYPERSPHERE SYSTEM
The Ring of Spheres: Competitive Model Architecture

This module implements the hypersphere probability system:
- State Classifiers: Convert 200+ indicators to 5 Markov states
- Hyperspheres: Individual probability models
- Ring: Collection of competing spheres
- Oracle: Meta-selector that chooses which sphere to trust
- North Star: Ranking metric for sphere performance
"""

from .state_classifier import (
    MarketState,
    StateClassification,
    BaseStateClassifier,
    MomentumStateClassifier,
    VolatilityStateClassifier,
    OscillatorStateClassifier,
    MultiPeriodStateClassifier,
    VolumeStateClassifier,
    CompositeStateClassifier,
    create_classifier,
    CLASSIFIER_REGISTRY
)

from .sphere import (
    SphereConfig,
    Prediction,
    Hypersphere
)

from .sphere_configs import (
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
    DEFAULT_SPHERE_CONFIGS,
    GOLD_SPHERE_CONFIGS,
    BTC_SPHERE_CONFIGS,
    create_gold_sphere,
    create_btc_sphere,
    create_nasdaq_sphere
)

__version__ = "1.0.0"
__all__ = [
    # States
    'MarketState',
    'StateClassification',
    
    # Classifiers
    'BaseStateClassifier',
    'MomentumStateClassifier',
    'VolatilityStateClassifier',
    'OscillatorStateClassifier',
    'MultiPeriodStateClassifier',
    'VolumeStateClassifier',
    'CompositeStateClassifier',
    'create_classifier',
    'CLASSIFIER_REGISTRY',
    
    # Spheres
    'SphereConfig',
    'Prediction',
    'Hypersphere',
    
    # Configs
    'DEFAULT_SPHERE_CONFIGS',
    'GOLD_SPHERE_CONFIGS',
    'BTC_SPHERE_CONFIGS',
    'create_gold_sphere',
    'create_btc_sphere',
    'create_nasdaq_sphere',
]
