# wizaude_core/state_classifier.py
"""
STATE CLASSIFIERS
Convert 200+ raw indicators into one of 5 Markov states: SB, B, N, BR, SBR

Different classification methods = Different sphere "personalities"
This is what makes spheres unique from each other.
"""

from enum import IntEnum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import numpy as np


class MarketState(IntEnum):
    """
    The 5 Markov states representing market conditions.
    
    These map to the hypersphere's axes:
    - Each state is a point on the 5-dimensional unit sphere
    - Transitions between states are paths on the sphere surface
    """
    STRONG_BULL = 0   # SB - Strong upward momentum
    BULL = 1          # B  - Moderate upward bias
    NEUTRAL = 2       # N  - No clear direction
    BEAR = 3          # BR - Moderate downward bias
    STRONG_BEAR = 4   # SBR - Strong downward momentum
    
    @classmethod
    def from_string(cls, s: str) -> 'MarketState':
        """Convert string abbreviation to MarketState"""
        mapping = {
            'SB': cls.STRONG_BULL,
            'B': cls.BULL,
            'N': cls.NEUTRAL,
            'BR': cls.BEAR,
            'SBR': cls.STRONG_BEAR
        }
        return mapping.get(s.upper(), cls.NEUTRAL)
    
    def to_abbrev(self) -> str:
        """Get short abbreviation"""
        return ['SB', 'B', 'N', 'BR', 'SBR'][self.value]


@dataclass
class StateClassification:
    """Result of state classification"""
    state: MarketState
    confidence: float  # 0-1, how confident in this classification
    components: Dict[str, float]  # Breakdown of what contributed
    
    def to_dict(self) -> Dict:
        return {
            'state': self.state.name,
            'state_abbrev': self.state.to_abbrev(),
            'state_value': self.state.value,
            'confidence': self.confidence,
            'components': self.components
        }


class BaseStateClassifier:
    """
    Abstract base for state classification strategies.
    
    Each classifier creates a different "lens" for viewing the market.
    This is what makes spheres different from each other.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.name = self.__class__.__name__
    
    def classify(self, indicators: Dict[str, float]) -> StateClassification:
        """
        Classify current market state from indicators.
        
        Args:
            indicators: Dict of indicator_name -> value
                       e.g., {'rsi_14': 65.5, 'momentum_7': 0.003, ...}
        
        Returns:
            StateClassification with state, confidence, and breakdown
        """
        raise NotImplementedError


class MomentumStateClassifier(BaseStateClassifier):
    """
    Classifies state based on momentum indicators.
    
    Uses: RSI, Momentum, MACD, Rate of Change
    Best for: Trending markets, momentum-based strategies
    
    HIGH SUCCESS CONFIG:
    - RSI period 7-14 depending on volatility
    - Momentum period 5-10 for responsiveness
    - ROC for confirmation
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.rsi_period = self.config.get('rsi_period', 14)
        self.momentum_period = self.config.get('momentum_period', 10)
        self.roc_period = self.config.get('roc_period', 10)
    
    def classify(self, indicators: Dict[str, float]) -> StateClassification:
        # Get relevant indicators
        rsi = indicators.get(f'rsi_{self.rsi_period}', 50)
        momentum = indicators.get(f'momentum_{self.momentum_period}', 0)
        roc = indicators.get(f'roc_{self.roc_period}', 0)
        macd_hist = indicators.get('macd_histogram_12_26_9', 0)
        
        # Normalize momentum and ROC to comparable scale
        atr = indicators.get('atr_14', 1)
        if atr <= 0:
            atr = 1
        norm_momentum = momentum / atr
        
        # Composite momentum score (-1 to +1)
        rsi_score = (rsi - 50) / 50  # -1 to +1
        mom_score = float(np.clip(norm_momentum * 10, -1, 1))
        roc_score = float(np.clip(roc * 5, -1, 1))
        macd_score = float(np.clip(macd_hist / atr, -1, 1))
        
        # Weighted composite
        weights = {'rsi': 0.3, 'momentum': 0.3, 'roc': 0.2, 'macd': 0.2}
        composite = (
            weights['rsi'] * rsi_score +
            weights['momentum'] * mom_score +
            weights['roc'] * roc_score +
            weights['macd'] * macd_score
        )
        
        # Classify based on composite score
        if composite > 0.6:
            state = MarketState.STRONG_BULL
        elif composite > 0.2:
            state = MarketState.BULL
        elif composite > -0.2:
            state = MarketState.NEUTRAL
        elif composite > -0.6:
            state = MarketState.BEAR
        else:
            state = MarketState.STRONG_BEAR
        
        # Confidence = how far from threshold boundaries
        confidence = min(abs(composite) * 1.5, 1.0)
        
        return StateClassification(
            state=state,
            confidence=confidence,
            components={
                'rsi_score': rsi_score,
                'momentum_score': mom_score,
                'roc_score': roc_score,
                'macd_score': macd_score,
                'composite': composite
            }
        )


class VolatilityStateClassifier(BaseStateClassifier):
    """
    Classifies state based on volatility indicators.
    
    Uses: ATR, Bollinger Band Width, ADX
    Best for: Breakout detection, volatility regime changes
    
    KEY INSIGHT: High volatility + trend = directional moves
                 Low volatility = consolidation/neutral
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.atr_period = self.config.get('atr_period', 14)
        self.bb_period = self.config.get('bb_period', 20)
        self.adx_period = self.config.get('adx_period', 14)
    
    def classify(self, indicators: Dict[str, float]) -> StateClassification:
        # Bollinger Band width as volatility proxy
        bb_width = indicators.get(f'bb_width_{self.bb_period}', 0)
        bb_middle = indicators.get(f'bb_middle_{self.bb_period}', 1)
        
        # Normalized BB width (volatility proxy)
        vol_ratio = (bb_width / bb_middle) if bb_middle > 0 else 0
        
        # ADX for trend strength
        adx = indicators.get(f'adx_{self.adx_period}', 25)
        
        # Direction from DI
        plus_di = indicators.get('plus_di_14', 50)
        minus_di = indicators.get('minus_di_14', 50)
        di_diff = plus_di - minus_di
        
        # Classification logic
        if vol_ratio < 0.01:  # Very low volatility
            state = MarketState.NEUTRAL
            confidence = 0.8
        elif adx < 20:  # No trend
            state = MarketState.NEUTRAL
            confidence = 0.6
        elif adx > 40:  # Strong trend
            if di_diff > 20:
                state = MarketState.STRONG_BULL
            elif di_diff > 5:
                state = MarketState.BULL
            elif di_diff < -20:
                state = MarketState.STRONG_BEAR
            elif di_diff < -5:
                state = MarketState.BEAR
            else:
                state = MarketState.NEUTRAL
            confidence = min(adx / 50, 1.0)
        else:  # Moderate trend
            if di_diff > 10:
                state = MarketState.BULL
            elif di_diff < -10:
                state = MarketState.BEAR
            else:
                state = MarketState.NEUTRAL
            confidence = adx / 40
        
        return StateClassification(
            state=state,
            confidence=confidence,
            components={
                'vol_ratio': vol_ratio,
                'adx': adx,
                'di_diff': di_diff,
                'plus_di': plus_di,
                'minus_di': minus_di
            }
        )


class OscillatorStateClassifier(BaseStateClassifier):
    """
    Classifies state based on oscillator confluence.
    
    Uses: RSI, Stochastic, Williams %R, CCI
    Best for: Overbought/oversold detection, mean reversion
    
    HIGH SUCCESS CONFIG:
    - Look for 3+ oscillators agreeing
    - Period 14 for stability, 7 for responsiveness
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.period = self.config.get('period', 14)
    
    def classify(self, indicators: Dict[str, float]) -> StateClassification:
        period = self.period
        
        # Get oscillators
        rsi = indicators.get(f'rsi_{period}', 50)
        stoch_k = indicators.get(f'stoch_k_{period}', 50)
        williams = indicators.get(f'williams_r_{period}', -50)  # -100 to 0
        cci = indicators.get(f'cci_{period}', 0)
        
        # Normalize all to 0-100 scale
        rsi_norm = rsi
        stoch_norm = stoch_k
        williams_norm = williams + 100  # Convert -100..0 to 0..100
        cci_norm = float(np.clip((cci + 200) / 4, 0, 100))  # CCI -200..+200 to 0..100
        
        # Count how many agree on overbought/oversold
        overbought_count = sum([
            rsi_norm > 70,
            stoch_norm > 80,
            williams_norm > 80,
            cci_norm > 75
        ])
        
        oversold_count = sum([
            rsi_norm < 30,
            stoch_norm < 20,
            williams_norm < 20,
            cci_norm < 25
        ])
        
        # Average oscillator value
        avg_oscillator = (rsi_norm + stoch_norm + williams_norm + cci_norm) / 4
        
        # Classify
        if overbought_count >= 3:
            state = MarketState.STRONG_BULL  # Overbought = was bullish
            confidence = overbought_count / 4
        elif oversold_count >= 3:
            state = MarketState.STRONG_BEAR  # Oversold = was bearish
            confidence = oversold_count / 4
        elif avg_oscillator > 60:
            state = MarketState.BULL
            confidence = (avg_oscillator - 50) / 50
        elif avg_oscillator < 40:
            state = MarketState.BEAR
            confidence = (50 - avg_oscillator) / 50
        else:
            state = MarketState.NEUTRAL
            confidence = 1 - abs(avg_oscillator - 50) / 50
        
        return StateClassification(
            state=state,
            confidence=confidence,
            components={
                'rsi': rsi_norm,
                'stoch': stoch_norm,
                'williams': williams_norm,
                'cci': cci_norm,
                'avg_oscillator': avg_oscillator,
                'overbought_count': overbought_count,
                'oversold_count': oversold_count
            }
        )


class MultiPeriodStateClassifier(BaseStateClassifier):
    """
    Classifies state by looking at multiple periods of same indicator.
    
    Uses: RSI 1-14, Momentum 1-14, etc.
    Best for: Detecting period-specific signals, multi-timeframe confluence
    
    KEY INSIGHT: When RSI_3 and RSI_14 diverge, something interesting is happening
    
    HIGH SUCCESS CONFIG:
    - Short: 1-4 (noise but fast)
    - Medium: 5-9 (balanced)
    - Long: 10-14 (stable but lagging)
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.indicator = self.config.get('indicator', 'rsi')
        self.short_periods = self.config.get('short_periods', [1, 2, 3])
        self.medium_periods = self.config.get('medium_periods', [5, 6, 7, 8])
        self.long_periods = self.config.get('long_periods', [10, 12, 14])
    
    def classify(self, indicators: Dict[str, float]) -> StateClassification:
        ind = self.indicator
        
        # Get values for each period group
        short_vals = [indicators.get(f'{ind}_{p}', 50) for p in self.short_periods]
        medium_vals = [indicators.get(f'{ind}_{p}', 50) for p in self.medium_periods]
        long_vals = [indicators.get(f'{ind}_{p}', 50) for p in self.long_periods]
        
        short_avg = float(np.mean(short_vals)) if short_vals else 50
        medium_avg = float(np.mean(medium_vals)) if medium_vals else 50
        long_avg = float(np.mean(long_vals)) if long_vals else 50
        
        # Normalize to -1..+1 (assuming RSI-like 0-100 scale)
        short_score = (short_avg - 50) / 50
        medium_score = (medium_avg - 50) / 50
        long_score = (long_avg - 50) / 50
        
        # Check for alignment vs divergence
        all_scores = [short_score, medium_score, long_score]
        alignment = float(1 - np.std(all_scores))  # High if all agree
        
        # Weighted average (short-term slightly more weight)
        composite = 0.4 * short_score + 0.35 * medium_score + 0.25 * long_score
        
        # Classify
        if composite > 0.4 and alignment > 0.7:
            state = MarketState.STRONG_BULL
        elif composite > 0.15:
            state = MarketState.BULL
        elif composite < -0.4 and alignment > 0.7:
            state = MarketState.STRONG_BEAR
        elif composite < -0.15:
            state = MarketState.BEAR
        else:
            state = MarketState.NEUTRAL
        
        # Confidence based on alignment
        confidence = alignment * min(abs(composite) * 2, 1.0)
        
        return StateClassification(
            state=state,
            confidence=confidence,
            components={
                'short_avg': short_avg,
                'medium_avg': medium_avg,
                'long_avg': long_avg,
                'alignment': alignment,
                'composite': composite
            }
        )


class VolumeStateClassifier(BaseStateClassifier):
    """
    Classifies state based on volume patterns.
    
    Uses: OBV, Volume MA ratios, CMF
    Best for: Confirming price moves, detecting accumulation/distribution
    
    KEY INSIGHT: High volume confirms direction
                 Low volume suggests reversal potential
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.cmf_period = self.config.get('cmf_period', 14)
    
    def classify(self, indicators: Dict[str, float]) -> StateClassification:
        # Volume ratio (current vs average)
        vol_ma_5 = indicators.get('volume_ma_5', 1)
        vol_ma_20 = indicators.get('volume_ma_20', 1)
        vol_ratio = vol_ma_5 / vol_ma_20 if vol_ma_20 > 0 else 1
        
        # Chaikin Money Flow
        cmf = indicators.get(f'cmf_{self.cmf_period}', 0)
        
        # Classification logic
        if vol_ratio < 0.7:  # Low volume
            state = MarketState.NEUTRAL
            confidence = 0.5
        elif cmf > 0.15 and vol_ratio > 1.2:
            state = MarketState.STRONG_BULL
            confidence = min(cmf * 3, 1.0)
        elif cmf > 0.05:
            state = MarketState.BULL
            confidence = min(cmf * 5, 0.8)
        elif cmf < -0.15 and vol_ratio > 1.2:
            state = MarketState.STRONG_BEAR
            confidence = min(abs(cmf) * 3, 1.0)
        elif cmf < -0.05:
            state = MarketState.BEAR
            confidence = min(abs(cmf) * 5, 0.8)
        else:
            state = MarketState.NEUTRAL
            confidence = 0.6
        
        return StateClassification(
            state=state,
            confidence=confidence,
            components={
                'vol_ratio': vol_ratio,
                'cmf': cmf
            }
        )


class CompositeStateClassifier(BaseStateClassifier):
    """
    Combines multiple classifiers with learned weights.
    
    This is the most powerful classifier - it uses all available information.
    The weights can be learned over time based on prediction accuracy.
    
    HIGH SUCCESS CONFIG:
    - Momentum: 30-40% (primary driver)
    - Volatility: 20-30% (regime detection)
    - Oscillator: 20-25% (extreme detection)
    - Volume: 10-20% (confirmation)
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        # Initialize sub-classifiers
        self.classifiers = {
            'momentum': MomentumStateClassifier(self.config.get('momentum', {})),
            'volatility': VolatilityStateClassifier(self.config.get('volatility', {})),
            'oscillator': OscillatorStateClassifier(self.config.get('oscillator', {})),
            'volume': VolumeStateClassifier(self.config.get('volume', {}))
        }
        
        # Weights (can be learned)
        self.weights = self.config.get('weights', {
            'momentum': 0.35,
            'volatility': 0.25,
            'oscillator': 0.25,
            'volume': 0.15
        })
    
    def classify(self, indicators: Dict[str, float]) -> StateClassification:
        # Get classifications from all sub-classifiers
        sub_classifications = {}
        for name, classifier in self.classifiers.items():
            sub_classifications[name] = classifier.classify(indicators)
        
        # Weighted vote
        state_votes = np.zeros(5)
        total_weight = 0
        
        for name, classification in sub_classifications.items():
            weight = self.weights.get(name, 0.25) * classification.confidence
            state_votes[classification.state] += weight
            total_weight += weight
        
        # Normalize
        if total_weight > 0:
            state_probs = state_votes / total_weight
        else:
            state_probs = np.ones(5) / 5
        
        # Winner
        winning_state = MarketState(int(np.argmax(state_probs)))
        confidence = float(state_probs[winning_state])
        
        return StateClassification(
            state=winning_state,
            confidence=confidence,
            components={
                'state_probs': state_probs.tolist(),
                'sub_classifications': {
                    name: {'state': c.state.name, 'confidence': c.confidence}
                    for name, c in sub_classifications.items()
                }
            }
        )


# Registry of all classifier types
CLASSIFIER_REGISTRY = {
    'momentum': MomentumStateClassifier,
    'volatility': VolatilityStateClassifier,
    'oscillator': OscillatorStateClassifier,
    'multi_period': MultiPeriodStateClassifier,
    'volume': VolumeStateClassifier,
    'composite': CompositeStateClassifier
}


def create_classifier(classifier_type: str, config: Dict[str, Any] = None) -> BaseStateClassifier:
    """Factory function to create classifiers by type"""
    if classifier_type not in CLASSIFIER_REGISTRY:
        raise ValueError(f"Unknown classifier type: {classifier_type}. Available: {list(CLASSIFIER_REGISTRY.keys())}")
    return CLASSIFIER_REGISTRY[classifier_type](config or {})
