#!/usr/bin/env python3
"""
Bayesian Probability Updater for Polymarket Bot Arena v3.0

This module provides Bayesian inference-based probability updates for
market prediction using multiple evidence sources.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

@dataclass
class BayesianUpdate:
    """Represents a Bayesian probability update"""
    prior_probability: float  # P(H)
    likelihood: float  # P(E|H)
    posterior_probability: float  # P(H|E)
    evidence_strength: float  # How strong is the evidence
    confidence_change: float  # Change in confidence
    timestamp: datetime

class BayesianProbabilityEngine:
    """
    Advanced Bayesian probability updating engine
    
    Uses Bayesian inference to update market probability estimates
    based on multiple evidence sources and historical data.
    """
    
    def __init__(self, prior_probability: float = 0.5, learning_rate: float = 0.1):
        self.prior_probability = prior_probability  # Initial belief
        self.learning_rate = learning_rate  # How fast to update beliefs
        self.evidence_history = []
        self.posterior_history = [prior_probability]
        self.evidence_weights = self._initialize_evidence_weights()
        self.decay_factor = 0.95  # Evidence decay over time
        self.confidence_threshold = 0.68  # Minimum confidence for signals
    
    def _initialize_evidence_weights(self) -> Dict[str, float]:
        """Initialize evidence source weights"""
        return {
            'price_action': 0.25,
            'volume': 0.20,
            'volatility': 0.15,
            'market_microstructure': 0.15,
            'external_sentiment': 0.15,
            'technical_indicators': 0.10
        }
    
    def update_prior_from_historical(self, historical_data: pd.DataFrame) -> float:
        """Update prior probability based on historical win rate"""
        
        if len(historical_data) < 50:
            logger.warning("Insufficient historical data for prior update")
            return self.prior_probability
        
        # Calculate historical win rate
        if 'outcome' in historical_data.columns:
            wins = (historical_data['outcome'] == 'win').sum()
            total_trades = len(historical_data)
            historical_win_rate = wins / total_trades
        elif 'pnl' in historical_data.columns:
            wins = (historical_data['pnl'] > 0).sum()
            total_trades = len(historical_data)
            historical_win_rate = wins / total_trades
        else:
            # Use price direction as proxy
            price_changes = historical_data['price'].pct_change().dropna()
            positive_changes = (price_changes > 0).sum()
            total_changes = len(price_changes)
            historical_win_rate = positive_changes / total_changes
        
        # Smooth update using learning rate
        self.prior_probability = (
            (1 - self.learning_rate) * self.prior_probability + 
            self.learning_rate * historical_win_rate
        )
        
        logger.info(f"Updated prior probability to: {self.prior_probability:.4f}")
        return self.prior_probability
    
    def calculate_evidence_likelihood(self, evidence: Dict[str, float], 
                                      hypothesis: bool = True) -> float:
        """
        Calculate P(E|H) - likelihood of evidence given hypothesis
        
        Args:
            evidence: Dictionary of evidence values (-1 to 1)
            hypothesis: True for positive outcome, False for negative
        
        Returns:
            Likelihood value between 0 and 1
        """
        
        total_likelihood = 0.0
        total_weight = 0.0
        
        for evidence_type, evidence_value in evidence.items():
            if evidence_type not in self.evidence_weights:
                continue
            
            weight = self.evidence_weights[evidence_type]
            total_weight += weight
            
            # Calculate likelihood based on evidence direction and hypothesis
            if hypothesis:  # Positive outcome hypothesis
                # Positive evidence increases likelihood
                if evidence_value > 0:
                    likelihood = 0.5 + (evidence_value * 0.4)  # 0.5 to 0.9
                else:
                    likelihood = 0.5 + (evidence_value * 0.3)  # 0.1 to 0.5
            else:  # Negative outcome hypothesis
                # Negative evidence increases likelihood for negative outcome
                if evidence_value < 0:
                    likelihood = 0.5 + (abs(evidence_value) * 0.4)  # 0.5 to 0.9
                else:
                    likelihood = 0.5 - (evidence_value * 0.3)  # 0.1 to 0.5
            
            # Ensure likelihood stays within bounds
            likelihood = np.clip(likelihood, 0.01, 0.99)
            total_likelihood += weight * likelihood
        
        # Normalize by total weight
        if total_weight > 0:
            total_likelihood /= total_weight
        
        return np.clip(total_likelihood, 0.01, 0.99)
    
    def apply_bayes_update(self, evidence: Dict[str, float]) -> BayesianUpdate:
        """
        Apply Bayesian update using evidence
        
        P(H|E) = P(E|H) * P(H) / P(E)
        
        Where:
        - P(H) is prior probability
        - P(E|H) is likelihood of evidence given hypothesis
        - P(E) is total probability of evidence
        - P(H|E) is posterior probability
        """
        
        # Calculate likelihoods for both hypotheses
        p_e_given_h_positive = self.calculate_evidence_likelihood(evidence, hypothesis=True)
        p_e_given_h_negative = self.calculate_evidence_likelihood(evidence, hypothesis=False)
        
        # Prior probabilities
        p_h_positive = self.prior_probability
        p_h_negative = 1 - self.prior_probability
        
        # Calculate P(E) using law of total probability
        # P(E) = P(E|H₁)P(H₁) + P(E|H₂)P(H₂)
        p_e_total = (p_e_given_h_positive * p_h_positive + 
                    p_e_given_h_negative * p_h_negative)
        
        # Apply Bayes' theorem for positive hypothesis
        # P(H₁|E) = P(E|H₁) * P(H₁) / P(E)
        posterior_positive = (p_e_given_h_positive * p_h_positive) / p_e_total
        
        # Calculate confidence metrics
        confidence_change = abs(posterior_positive - self.prior_probability)
        evidence_strength = np.mean([abs(evidence.get(k, 0)) for k in self.evidence_weights.keys()])
        
        # Create update record
        update = BayesianUpdate(
            prior_probability=self.prior_probability,
            likelihood=p_e_given_h_positive,
            posterior_probability=posterior_positive,
            evidence_strength=evidence_strength,
            confidence_change=confidence_change,
            timestamp=datetime.now()
        )
        
        # Update prior for next iteration
        self.prior_probability = posterior_positive
        self.posterior_history.append(posterior_positive)
        
        return update
    
    def gather_market_evidence(self, market_data: pd.DataFrame,
                              lookback_periods: Optional[Dict[str, int]] = None) -> Dict[str, float]:
        """Gather evidence from market data"""
        
        if lookback_periods is None:
            lookback_periods = {
                'price_action': 24,
                'volume': 12,
                'volatility': 48,
                'market_microstructure': 6,
                'technical_indicators': 20
            }
        
        evidence = {}
        
        # Price action evidence
        if len(market_data) >= lookback_periods['price_action']:
            recent_prices = market_data['price'].tail(lookback_periods['price_action'])
            price_trend = (recent_prices.iloc[-1] - recent_prices.iloc[0]) / recent_prices.iloc[0]
            price_momentum = recent_prices.pct_change().tail(6).mean() * 1000  # Scale
            evidence['price_action'] = np.clip(price_trend * 5 + price_momentum, -1, 1)
        
        # Volume evidence
        if len(market_data) >= lookback_periods['volume']:
            recent_volume = market_data['volume'].tail(lookback_periods['volume']).mean()
            avg_volume = market_data['volume'].mean()
            volume_ratio = (recent_volume - avg_volume) / avg_volume
            evidence['volume'] = np.clip(volume_ratio * 2, -1, 1)
        
        # Volatility evidence
        if len(market_data) >= lookback_periods['volatility']:
            recent_volatility = market_data['price'].tail(lookback_periods['volatility']).std() / market_data['price'].tail(lookback_periods['volatility']).mean()
            avg_volatility = market_data['price'].std() / market_data['price'].mean()
            volatility_ratio = recent_volatility / avg_volatility if avg_volatility > 0 else 1
            # Low volatility is positive evidence (stable market)
            evidence['volatility'] = np.clip(1 - volatility_ratio, -1, 1)
        
        # Market microstructure evidence
        if 'spread' in market_data.columns and len(market_data) >= lookback_periods['market_microstructure']:
            recent_spread = market_data['spread'].tail(lookback_periods['market_microstructure']).mean()
            avg_spread = market_data['spread'].mean()
            spread_ratio = recent_spread / avg_spread if avg_spread > 0 else 1
            # Lower spread is positive evidence (better liquidity)
            evidence['market_microstructure'] = np.clip(1 - spread_ratio, -1, 1)
        
        # Technical indicators evidence
        if len(market_data) >= lookback_periods['technical_indicators']:
            # Simple RSI-like indicator
            recent_prices = market_data['price'].tail(lookback_periods['technical_indicators'])
            gains = recent_prices.pct_change()
            positive_gains = gains[gains > 0].sum()
            negative_gains = abs(gains[gains < 0].sum())
            
            if positive_gains + negative_gains > 0:
                rsi_like = positive_gains / (positive_gains + negative_gains)
                # Convert RSI to evidence (-1 to 1), center around 0.5
                evidence['technical_indicators'] = np.clip((rsi_like - 0.5) * 2, -1, 1)
            else:
                evidence['technical_indicators'] = 0
        
        return evidence
    
    def add_external_evidence(self, evidence: Dict[str, float], 
                            external_data: Dict[str, Any]) -> Dict[str, float]:
        """Add external evidence to market evidence"""
        
        # News sentiment evidence
        if 'news_sentiment' in external_data:
            news_sentiment = external_data['news_sentiment']
            evidence['external_sentiment'] = np.clip(news_sentiment, -1, 1)
        
        # Social media sentiment
        if 'social_sentiment' in external_data:
            social_sentiment = external_data['social_sentiment']
            evidence['external_sentiment'] = evidence.get('external_sentiment', 0) * 0.5 + social_sentiment * 0.5
        
        # Event impact
        if 'event_impact' in external_data:
            event_impact = external_data['event_impact']
            evidence['external_factors'] = np.clip(event_impact, -1, 1)
        
        # Whale activity
        if 'whale_activity' in external_data:
            whale_data = external_data['whale_activity']
            if isinstance(whale_data, dict) and 'net_flow' in whale_data:
                evidence['whale_flow'] = np.clip(whale_data['net_flow'] / 1000000, -1, 1)  # Normalize
        
        return evidence
    
    def apply_time_decay(self, evidence: Dict[str, float], 
                        time_since_last_update: timedelta) -> Dict[str, float]:
        """Apply time decay to evidence strength"""
        
        hours_elapsed = time_since_last_update.total_seconds() / 3600
        decay_factor = self.decay_factor ** hours_elapsed
        
        decayed_evidence = {}
        for key, value in evidence.items():
            decayed_evidence[key] = value * decay_factor
        
        return decayed_evidence
    
    def get_confidence_level(self, posterior_probability: float, 
                           evidence_strength: float) -> float:
        """Calculate confidence level based on posterior and evidence"""
        
        # Base confidence from probability deviation from 50%
        probability_deviation = abs(posterior_probability - 0.5) * 2
        
        # Boost confidence based on evidence strength
        evidence_boost = min(0.3, evidence_strength * 0.5)
        
        # Calculate final confidence
        confidence = probability_deviation + evidence_boost
        
        return np.clip(confidence, 0, 1)
    
    def should_generate_signal(self, posterior_probability: float, 
                             confidence_level: float) -> bool:
        """Determine if signal should be generated based on confidence"""
        
        return (confidence_level >= self.confidence_threshold and 
                abs(posterior_probability - 0.5) > 0.1)  # Significant deviation from 50%
    
    def generate_trading_signal(self, market_data: pd.DataFrame,
                               external_data: Optional[Dict[str, Any]] = None,
                               time_since_last: Optional[timedelta] = None) -> Optional[Dict[str, Any]]:
        """
        Generate trading signal using Bayesian inference
        
        Returns:
            Dictionary with signal information or None
        """
        
        # Gather market evidence
        market_evidence = self.gather_market_evidence(market_data)
        
        # Add external evidence
        if external_data:
            evidence = self.add_external_evidence(market_evidence, external_data)
        else:
            evidence = market_evidence
        
        # Apply time decay if applicable
        if time_since_last:
            evidence = self.apply_time_decay(evidence, time_since_last)
        
        # Apply Bayesian update
        bayesian_update = self.apply_bayes_update(evidence)
        
        # Calculate confidence level
        confidence_level = self.get_confidence_level(
            bayesian_update.posterior_probability,
            bayesian_update.evidence_strength
        )
        
        # Generate signal if confidence is sufficient
        if self.should_generate_signal(bayesian_update.posterior_probability, confidence_level):
            signal_type = 'buy' if bayesian_update.posterior_probability > 0.5 else 'sell'
            expected_value = abs(bayesian_update.posterior_probability - 0.5) * 2 * 0.03  # 3% max return
            
            signal = {
                'type': signal_type,
                'confidence': confidence_level,
                'expected_value': expected_value,
                'size': int(confidence_level * 100),  # Size based on confidence
                'prior_probability': bayesian_update.prior_probability,
                'posterior_probability': bayesian_update.posterior_probability,
                'evidence_strength': bayesian_update.evidence_strength,
                'confidence_change': bayesian_update.confidence_change,
                'evidence': evidence,
                'timestamp': bayesian_update.timestamp,
                'reasoning': f"Bayesian update: {bayesian_update.prior_probability:.4f} → {bayesian_update.posterior_probability:.4f}"
            }
            
            logger.info(f"Bayesian signal generated: {signal_type} "
                       f"(confidence: {confidence_level:.3f}, "
                       f"posterior: {bayesian_update.posterior_probability:.4f})")
            
            return signal
        
        logger.info(f"No signal generated (confidence: {confidence_level:.3f}, "
                   f"posterior: {bayesian_update.posterior_probability:.4f})")
        return None
    
    def get_probability_history(self) -> List[float]:
        """Get history of posterior probabilities"""
        return self.posterior_history.copy()
    
    def reset_to_prior(self, new_prior: Optional[float] = None):
        """Reset to prior probability"""
        if new_prior is not None:
            self.prior_probability = new_prior
        else:
            # Reset to initial prior
            self.prior_probability = 0.5
        
        self.posterior_history = [self.prior_probability]
        self.evidence_history = []
        
        logger.info(f"Reset to prior probability: {self.prior_probability}")

class AdaptiveBayesianUpdater(BayesianProbabilityEngine):
    """
    Adaptive Bayesian updater that learns from its own performance
    """
    
    def __init__(self, prior_probability: float = 0.5, learning_rate: float = 0.1):
        super().__init__(prior_probability, learning_rate)
        self.performance_history = []
        self.adaptation_rate = 0.05  # How fast to adapt weights
        self.min_performance_samples = 10  # Minimum samples before adaptation
    
    def record_performance(self, signal: Dict[str, Any], actual_outcome: float):
        """Record the actual outcome of a signal"""
        
        performance = {
            'timestamp': datetime.now(),
            'signal_type': signal['type'],
            'confidence': signal['confidence'],
            'predicted_probability': signal['posterior_probability'],
            'actual_outcome': actual_outcome,  # 1 for win, 0 for loss
            'expected_value': signal['expected_value']
        }
        
        self.performance_history.append(performance)
        
        # Keep only recent performance
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]
        
        # Adapt if we have enough samples
        if len(self.performance_history) >= self.min_performance_samples:
            self._adapt_evidence_weights()
    
    def _adapt_evidence_weights(self):
        """Adapt evidence weights based on performance history"""
        
        if len(self.performance_history) < self.min_performance_samples:
            return
        
        # Calculate performance by evidence type
        evidence_performance = {}
        
        for performance in self.performance_history:
            # Get the evidence used for this signal (would need to store this)
            # For now, we'll use overall performance to adjust all weights
            
            predicted_prob = performance['predicted_probability']
            actual_outcome = performance['actual_outcome']
            
            # Calculate prediction accuracy
            if actual_outcome == 1:  # Win
                accuracy = predicted_prob  # Higher probability = better prediction
            else:  # Loss
                accuracy = 1 - predicted_prob  # Lower probability = better prediction
            
            # Store performance (aggregate for now)
            if 'overall' not in evidence_performance:
                evidence_performance['overall'] = []
            evidence_performance['overall'].append(accuracy)
        
        # Calculate average performance
        avg_performance = {}
        for evidence_type, performances in evidence_performance.items():
            if performances:
                avg_performance[evidence_type] = np.mean(performances)
        
        # Update weights based on performance (simplified)
        if 'overall' in avg_performance:
            performance_score = avg_performance['overall']
            
            # Adjust all weights slightly based on overall performance
            adjustment = (performance_score - 0.5) * self.adaptation_rate
            
            for evidence_type in self.evidence_weights:
                current_weight = self.evidence_weights[evidence_type]
                new_weight = np.clip(current_weight + adjustment, 0.05, 0.5)
                self.evidence_weights[evidence_type] = new_weight
            
            # Normalize weights to sum to 1
            total_weight = sum(self.evidence_weights.values())
            if total_weight > 0:
                for evidence_type in self.evidence_weights:
                    self.evidence_weights[evidence_type] /= total_weight
            
            logger.info(f"Adapted evidence weights based on performance: {self.evidence_weights}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of model performance"""
        
        if len(self.performance_history) < self.min_performance_samples:
            return {"error": "Insufficient performance data"}
        
        recent_performances = self.performance_history[-20:]  # Last 20 trades
        
        wins = sum(1 for p in recent_performances if p['actual_outcome'] == 1)
        total_signals = len(recent_performances)
        win_rate = wins / total_signals if total_signals > 0 else 0
        
        avg_confidence = np.mean([p['confidence'] for p in recent_performances])
        avg_predicted_probability = np.mean([p['predicted_probability'] for p in recent_performances])
        
        # Calculate calibration (how well predicted probabilities match actual outcomes)
        predicted_probs = [p['predicted_probability'] for p in recent_performances]
        actual_outcomes = [p['actual_outcome'] for p in recent_performances]
        
        # Brier score (lower is better)
        brier_score = np.mean([(p - a) ** 2 for p, a in zip(predicted_probs, actual_outcomes)])
        
        return {
            'total_signals': total_signals,
            'win_rate': win_rate,
            'avg_confidence': avg_confidence,
            'avg_predicted_probability': avg_predicted_probability,
            'brier_score': brier_score,
            'calibration': 'good' if abs(avg_predicted_probability - win_rate) < 0.1 else 'poor',
            'evidence_weights': self.evidence_weights.copy()
        }

# Example usage and testing
if __name__ == "__main__":
    """Test the Bayesian probability updater"""
    
    logging.basicConfig(level=logging.INFO)
    
    print("🧪 Testing Bayesian Probability Updater v3.0...")
    
    # Create sample market data
    dates = pd.date_range(start='2023-01-01', periods=200, freq='h')
    prices = 0.5 + np.cumsum(np.random.normal(0, 0.001, 200)) + np.sin(np.arange(200) * 0.05) * 0.1
    volumes = np.random.lognormal(10, 1, 200)
    spreads = np.random.exponential(0.005, 200)
    
    market_data = pd.DataFrame({
        'timestamp': dates,
        'price': prices,
        'volume': volumes,
        'spread': spreads
    })
    
    # Create Bayesian updater
    updater = AdaptiveBayesianUpdater(prior_probability=0.5, learning_rate=0.1)
    
    # Train on historical data
    print("📚 Training on historical data...")
    updated_prior = updater.update_prior_from_historical(market_data)
    
    # Generate signals for different time periods
    print("\n🎯 Generating Bayesian signals...")
    signals = []
    
    for i in range(10, len(market_data), 20):  # Every 20 hours
        recent_data = market_data.iloc[max(0, i-50):i]
        
        # Add some external evidence
        external_data = {
            'news_sentiment': np.random.uniform(-0.5, 0.5),
            'social_sentiment': np.random.uniform(-0.3, 0.3),
            'event_impact': np.random.uniform(-0.2, 0.2)
        }
        
        signal = updater.generate_trading_signal(recent_data, external_data)
        
        if signal:
            signals.append(signal)
            print(f"Signal {len(signals)}: {signal['type']} "
                  f"(confidence: {signal['confidence']:.3f}, "
                  f"posterior: {signal['posterior_probability']:.4f})")
    
    print(f"\n📊 Generated {len(signals)} signals out of {len(range(10, len(market_data), 20))} attempts")
    
    # Simulate recording some performance
    print("\n📈 Simulating performance tracking...")
    for i, signal in enumerate(signals[:5]):  # First 5 signals
        # Simulate actual outcome (win with probability based on confidence)
        actual_outcome = 1 if np.random.random() < signal['confidence'] else 0
        updater.record_performance(signal, actual_outcome)
        print(f"Signal {i+1}: Predicted confidence {signal['confidence']:.3f}, "
              f"Actual outcome: {'Win' if actual_outcome else 'Loss'}")
    
    # Get performance summary
    print("\n📋 Performance Summary:")
    summary = updater.get_performance_summary()
    if 'error' not in summary:
        print(f"   Total signals: {summary['total_signals']}")
        print(f"   Win rate: {summary['win_rate']:.3f}")
        print(f"   Average confidence: {summary['avg_confidence']:.3f}")
        print(f"   Average predicted probability: {summary['avg_predicted_probability']:.3f}")
        print(f"   Brier score: {summary['brier_score']:.4f}")
        print(f"   Calibration: {summary['calibration']}")
        print(f"   Evidence weights: {summary['evidence_weights']}")
    
    print("\n✅ Bayesian Probability Updater v3.0 test completed!")