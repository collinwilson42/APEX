# wizaude_core/sphere.py
"""
HYPERSPHERE
Individual probability model with internal 5x5 Markov transition matrix.

Each sphere is defined by:
1. A state classifier (how it sees the market)
2. A transition matrix (learned from observed transitions)
3. Performance tracking (for North Star ranking)
"""

import numpy as np
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import json
import uuid

from .state_classifier import (
    BaseStateClassifier, 
    MarketState, 
    StateClassification,
    create_classifier
)


@dataclass
class SphereConfig:
    """Configuration for a hypersphere"""
    name: str
    classifier_type: str
    classifier_config: Dict[str, Any] = field(default_factory=dict)
    
    # Learning parameters
    lookback_window: int = 500  # How many transitions to consider
    decay_factor: float = 0.98  # Exponential decay for older transitions
    
    # Symbol specificity
    symbol: Optional[str] = None  # None = cross-symbol
    timeframe: str = '15m'
    
    # Prior (starting belief before any data)
    prior_strength: float = 1.0  # How much to weight prior vs observed
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'classifier_type': self.classifier_type,
            'classifier_config': self.classifier_config,
            'lookback_window': self.lookback_window,
            'decay_factor': self.decay_factor,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'prior_strength': self.prior_strength
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SphereConfig':
        return cls(**data)


@dataclass
class Prediction:
    """A single prediction made by a sphere"""
    timestamp: datetime
    current_state: MarketState
    predicted_distribution: np.ndarray  # [p_SB, p_B, p_N, p_BR, p_SBR]
    predicted_state: MarketState  # argmax of distribution
    confidence: float
    
    # Filled in later when outcome known
    actual_state: Optional[MarketState] = None
    was_correct: Optional[bool] = None
    log_loss: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'current_state': self.current_state.name,
            'predicted_distribution': self.predicted_distribution.tolist(),
            'predicted_state': self.predicted_state.name,
            'confidence': self.confidence,
            'actual_state': self.actual_state.name if self.actual_state else None,
            'was_correct': self.was_correct,
            'log_loss': self.log_loss
        }


class Hypersphere:
    """
    A complete probability model for market state transitions.
    
    Each sphere is defined by:
    1. A state classifier (how it sees the market)
    2. A transition matrix (learned from observed transitions)
    3. Performance tracking (for North Star ranking)
    
    The hypersphere geometry:
    - 5 states = 5 axes in 5D space
    - Each row of transition matrix = point on 4-simplex
    - Probability distributions live on the hypersphere surface
    """
    
    def __init__(self, config: SphereConfig):
        self.id = str(uuid.uuid4())
        self.config = config
        self.name = config.name
        
        # State classifier
        self.classifier = create_classifier(
            config.classifier_type,
            config.classifier_config
        )
        
        # Transition matrix (5x5)
        # Initialize with slight diagonal preference (states tend to persist)
        self.transition_counts = np.ones((5, 5)) * config.prior_strength
        np.fill_diagonal(self.transition_counts, config.prior_strength * 3)
        
        # Weights for exponential decay
        self.transition_weights = np.ones((5, 5)) * config.prior_strength
        
        # Recent transitions for decay calculation
        self.recent_transitions: List[tuple] = []  # [(from_state, to_state, timestamp), ...]
        
        # Predictions for performance tracking
        self.predictions: List[Prediction] = []
        
        # Performance metrics
        self.north_star_score = 0.0
        self.rank: Optional[int] = None
        
        # Metadata
        self.created_at = datetime.now()
        self.last_updated = datetime.now()
    
    @property
    def transition_matrix(self) -> np.ndarray:
        """
        Compute normalized transition matrix from counts.
        Each row sums to 1.0 (valid probability distribution).
        """
        # Apply exponential decay to old transitions
        matrix = self._apply_decay()
        
        # Normalize rows
        row_sums = matrix.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1  # Avoid division by zero
        return matrix / row_sums
    
    def _apply_decay(self) -> np.ndarray:
        """Apply exponential decay to transition counts based on recency"""
        # Start with base counts
        matrix = self.transition_counts.copy()
        
        # Add weighted recent transitions
        return matrix + self.transition_weights
    
    def classify_state(self, indicators: Dict[str, float]) -> StateClassification:
        """Classify current market state from indicators"""
        return self.classifier.classify(indicators)
    
    def predict_next_state(
        self, 
        current_state: MarketState,
        context: Optional[Dict] = None
    ) -> Prediction:
        """
        Predict probability distribution over next states.
        
        Args:
            current_state: The current market state
            context: Optional context (regime, time, etc.)
        
        Returns:
            Prediction object with distribution and confidence
        """
        # Get transition probabilities from current state
        distribution = self.transition_matrix[current_state].copy()
        
        # Predicted state = most likely
        predicted_state = MarketState(int(np.argmax(distribution)))
        
        # Confidence = probability of predicted state
        confidence = float(distribution[predicted_state])
        
        prediction = Prediction(
            timestamp=datetime.now(),
            current_state=current_state,
            predicted_distribution=distribution,
            predicted_state=predicted_state,
            confidence=confidence
        )
        
        self.predictions.append(prediction)
        return prediction
    
    def observe_transition(
        self, 
        from_state: MarketState, 
        to_state: MarketState,
        timestamp: Optional[datetime] = None
    ):
        """
        Observe an actual transition and update the model.
        
        Args:
            from_state: The state we transitioned from
            to_state: The state we transitioned to
            timestamp: When this occurred
        """
        ts = timestamp or datetime.now()
        
        # Update counts
        self.transition_counts[from_state][to_state] += 1
        
        # Track for decay
        self.recent_transitions.append((int(from_state), int(to_state), ts))
        
        # Prune old transitions beyond lookback window
        if len(self.recent_transitions) > self.config.lookback_window:
            self.recent_transitions = self.recent_transitions[-self.config.lookback_window:]
        
        # Update the most recent prediction's outcome
        self._update_last_prediction(to_state)
        
        self.last_updated = datetime.now()
    
    def _update_last_prediction(self, actual_state: MarketState):
        """Update the most recent prediction with actual outcome"""
        if not self.predictions:
            return
        
        # Find most recent prediction that doesn't have an outcome
        for pred in reversed(self.predictions):
            if pred.actual_state is None:
                pred.actual_state = actual_state
                pred.was_correct = (pred.predicted_state == actual_state)
                
                # Log loss: -log(probability assigned to actual state)
                prob_of_actual = pred.predicted_distribution[actual_state]
                pred.log_loss = float(-np.log(max(prob_of_actual, 1e-10)))
                break
    
    def get_accuracy(self, window: int = 50) -> float:
        """
        Get prediction accuracy over recent predictions.
        
        Args:
            window: Number of recent predictions to consider
        
        Returns:
            Accuracy as float 0-1
        """
        if len(self.predictions) < 10:
            return 0.5  # Not enough data
        
        recent = self.predictions[-window:]
        with_outcomes = [p for p in recent if p.was_correct is not None]
        
        if not with_outcomes:
            return 0.5
        
        return sum(1 for p in with_outcomes if p.was_correct) / len(with_outcomes)
    
    def get_confidence(self) -> float:
        """
        Overall confidence of this sphere based on recent performance.
        """
        return self.get_accuracy(50)
    
    def get_state_embedding(self, state: MarketState) -> np.ndarray:
        """
        Get the embedding (position on hypersphere) for a state.
        
        The embedding is derived from the transition probabilities:
        - A state that strongly transitions to bullish states has a "bullish" embedding
        - The transition row IS the embedding (after normalization)
        
        This maps the Markov model onto a geometric structure.
        """
        # Get transition probabilities from this state
        probs = self.transition_matrix[state]
        
        # This is already on the probability simplex
        # To map to unit hypersphere, take square root
        embedding = np.sqrt(probs)
        
        # Normalize to unit length
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding
    
    def get_current_position(self, state_distribution: np.ndarray) -> np.ndarray:
        """
        Get position on hypersphere given a distribution over states.
        
        Used for visualization - shows where "the market" currently sits
        relative to the sphere's geometry.
        
        Args:
            state_distribution: [p_SB, p_B, p_N, p_BR, p_SBR]
        
        Returns:
            5D unit vector representing position on hypersphere
        """
        # Weighted combination of state embeddings
        position = np.zeros(5)
        for state in MarketState:
            embedding = self.get_state_embedding(state)
            position += state_distribution[state] * embedding
        
        # Normalize to stay on unit sphere
        norm = np.linalg.norm(position)
        if norm > 0:
            position = position / norm
        
        return position
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics about this sphere"""
        total_predictions = len(self.predictions)
        with_outcomes = [p for p in self.predictions if p.was_correct is not None]
        
        if with_outcomes:
            accuracy = sum(1 for p in with_outcomes if p.was_correct) / len(with_outcomes)
            avg_confidence = np.mean([p.confidence for p in with_outcomes])
            avg_log_loss = np.mean([p.log_loss for p in with_outcomes if p.log_loss is not None])
        else:
            accuracy = 0.5
            avg_confidence = 0.5
            avg_log_loss = None
        
        return {
            'id': self.id,
            'name': self.name,
            'classifier_type': self.config.classifier_type,
            'symbol': self.config.symbol,
            'timeframe': self.config.timeframe,
            'total_predictions': total_predictions,
            'predictions_with_outcomes': len(with_outcomes),
            'accuracy': accuracy,
            'avg_confidence': avg_confidence,
            'avg_log_loss': avg_log_loss,
            'north_star_score': self.north_star_score,
            'rank': self.rank,
            'total_transitions': int(self.transition_counts.sum()),
            'created_at': self.created_at.isoformat(),
            'last_updated': self.last_updated.isoformat()
        }
    
    def to_dict(self) -> Dict:
        """Serialize sphere to dictionary"""
        return {
            'id': self.id,
            'config': self.config.to_dict(),
            'transition_counts': self.transition_counts.tolist(),
            'transition_weights': self.transition_weights.tolist(),
            'north_star_score': self.north_star_score,
            'rank': self.rank,
            'created_at': self.created_at.isoformat(),
            'last_updated': self.last_updated.isoformat(),
            'prediction_count': len(self.predictions),
            'recent_transitions_count': len(self.recent_transitions)
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Hypersphere':
        """Deserialize sphere from dictionary"""
        config = SphereConfig.from_dict(data['config'])
        sphere = cls(config)
        sphere.id = data['id']
        sphere.transition_counts = np.array(data['transition_counts'])
        sphere.transition_weights = np.array(data['transition_weights'])
        sphere.north_star_score = data.get('north_star_score', 0.0)
        sphere.rank = data.get('rank')
        sphere.created_at = datetime.fromisoformat(data['created_at'])
        sphere.last_updated = datetime.fromisoformat(data['last_updated'])
        return sphere
    
    def __repr__(self) -> str:
        return f"Hypersphere(name='{self.name}', rank={self.rank}, accuracy={self.get_accuracy():.2%})"
