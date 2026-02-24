#!/usr/bin/env python3
"""
Advanced Edge Models for Polymarket Bot Arena v3.0

This module provides sophisticated trading signal generation using multiple
advanced techniques including sentiment analysis, whale tracking, Bayesian
updates, and mispricing detection.
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
class EdgeSignal:
    """Represents a trading signal from an edge model"""
    type: str  # 'buy', 'sell', or 'hold'
    confidence: float  # 0.0 to 1.0
    expected_value: float  # Expected return as percentage
    size: int  # Position size
    model_name: str  # Source model
    reasoning: str  # Explanation
    timestamp: datetime
    metadata: Dict[str, Any]  # Additional model-specific data

class BaseEdgeModel(ABC):
    """Base class for all edge models"""
    
    def __init__(self, name: str, min_confidence: float = 0.6):
        self.name = name
        self.min_confidence = min_confidence
        self.is_trained = False
    
    @abstractmethod
    def analyze_market(self, market_data: pd.DataFrame, 
                        news_data: Optional[List[Dict]] = None,
                        social_data: Optional[List[Dict]] = None) -> Optional[EdgeSignal]:
        """Analyze market and generate signal"""
        pass
    
    @abstractmethod
    def train(self, historical_data: pd.DataFrame) -> bool:
        """Train the model on historical data"""
        pass

class AdvancedLLMSentimentEngine(BaseEdgeModel):
    """
    Advanced LLM-based sentiment analysis engine
    
    Analyzes news, social media, and market sentiment to generate
    trading signals with high confidence thresholds.
    """
    
    def __init__(self, min_confidence: float = 0.7):
        super().__init__("AdvancedLLMSentimentEngine", min_confidence)
        self.sentiment_weights = {
            'news': 0.4,
            'social': 0.3,
            'market_sentiment': 0.3
        }
        self.sentiment_cache = {}
    
    def train(self, historical_data: pd.DataFrame) -> bool:
        """Train sentiment model on historical data"""
        logger.info("Training AdvancedLLMSentimentEngine...")
        
        # Simulate training on historical sentiment data
        # In reality, this would process actual news and social media data
        
        # Calculate sentiment-price correlation
        if 'sentiment_score' in historical_data.columns:
            correlation = historical_data['sentiment_score'].corr(historical_data['price_change'])
            logger.info(f"Sentiment-price correlation: {correlation:.3f}")
        
        self.is_trained = True
        logger.info("AdvancedLLMSentimentEngine training completed")
        return True
    
    def analyze_market(self, market_data: pd.DataFrame, 
                        news_data: Optional[List[Dict]] = None,
                        social_data: Optional[List[Dict]] = None) -> Optional[EdgeSignal]:
        """Analyze sentiment and generate signal"""
        
        if not self.is_trained:
            logger.warning("Model not trained, using default parameters")
        
        # Simulate sentiment analysis
        # In reality, this would use actual LLM processing
        
        # Calculate market sentiment from price action
        recent_prices = market_data['price'].tail(24)
        price_change = (recent_prices.iloc[-1] - recent_prices.iloc[0]) / recent_prices.iloc[0]
        volatility = recent_prices.std() / recent_prices.mean()
        
        # Simulate news sentiment
        news_sentiment = self._simulate_news_sentiment(news_data, price_change)
        
        # Simulate social sentiment  
        social_sentiment = self._simulate_social_sentiment(social_data, price_change)
        
        # Calculate market sentiment
        market_sentiment = self._calculate_market_sentiment(price_change, volatility)
        
        # Weighted average sentiment
        total_sentiment = (
            news_sentiment * self.sentiment_weights['news'] +
            social_sentiment * self.sentiment_weights['social'] +
            market_sentiment * self.sentiment_weights['market_sentiment']
        )
        
        # Generate signal if sentiment is strong
        confidence = abs(total_sentiment)
        if confidence >= self.min_confidence:
            signal_type = 'buy' if total_sentiment > 0 else 'sell'
            expected_value = confidence * 0.03  # 3% max expected return
            
            return EdgeSignal(
                type=signal_type,
                confidence=confidence,
                expected_value=expected_value,
                size=int(confidence * 150),  # Size based on confidence
                model_name=self.name,
                reasoning=f"Strong {'positive' if total_sentiment > 0 else 'negative'} sentiment analysis",
                timestamp=datetime.now(),
                metadata={
                    'news_sentiment': news_sentiment,
                    'social_sentiment': social_sentiment,
                    'market_sentiment': market_sentiment,
                    'price_change_24h': price_change
                }
            )
        
        return None
    
    def _simulate_news_sentiment(self, news_data: Optional[List[Dict]], price_change: float) -> float:
        """Simulate news sentiment analysis"""
        if news_data is None:
            # Default sentiment based on price action
            return np.clip(price_change * 5, -1, 1)
        
        # Simulate processing news headlines
        positive_keywords = ['bullish', 'positive', 'up', 'gain', 'surge', 'rally']
        negative_keywords = ['bearish', 'negative', 'down', 'loss', 'crash', 'dump']
        
        sentiment_score = 0
        for news_item in news_data[-5:]:  # Last 5 news items
            text = news_item.get('text', '').lower()
            
            positive_count = sum(1 for word in positive_keywords if word in text)
            negative_count = sum(1 for word in negative_keywords if word in text)
            
            item_sentiment = (positive_count - negative_count) / max(1, len(text.split()))
            sentiment_score += item_sentiment
        
        return np.clip(sentiment_score / max(1, len(news_data[-5:])), -1, 1)
    
    def _simulate_social_sentiment(self, social_data: Optional[List[Dict]], price_change: float) -> float:
        """Simulate social media sentiment analysis"""
        if social_data is None:
            # Default sentiment based on price action
            return np.clip(price_change * 3, -1, 1)
        
        # Simulate processing social media posts
        sentiment_score = 0
        for post in social_data[-10:]:  # Last 10 social posts
            # Simulate engagement-based sentiment
            likes = post.get('likes', 0)
            comments = post.get('comments', 0)
            sentiment = post.get('sentiment', 0)  # -1 to 1
            
            weight = 1 + np.log10(max(1, likes + comments))
            sentiment_score += sentiment * weight
        
        total_weight = sum(1 + np.log10(max(1, post.get('likes', 0) + post.get('comments', 0))) 
                         for post in social_data[-10:])
        
        return np.clip(sentiment_score / max(1, total_weight), -1, 1)
    
    def _calculate_market_sentiment(self, price_change: float, volatility: float) -> float:
        """Calculate market sentiment from price action"""
        # Price momentum sentiment
        momentum_sentiment = np.clip(price_change * 10, -1, 1)
        
        # Volatility sentiment (high volatility = uncertainty = negative sentiment)
        volatility_sentiment = np.clip(1 - volatility * 50, -1, 1)
        
        # Combine (60% momentum, 40% volatility)
        return 0.6 * momentum_sentiment + 0.4 * volatility_sentiment

class WhaleCopyTraderPRO(BaseEdgeModel):
    """
    Professional whale tracking and copy trading system
    
    Identifies large wallet movements and institutional trading patterns
    to generate signals with high probability of success.
    """
    
    def __init__(self, min_confidence: float = 0.65):
        super().__init__("WhaleCopyTraderPRO", min_confidence)
        self.whale_threshold = 100000  # $100k+ transactions
        self.copy_delay_hours = 2  # Delay before copying
        self.confidence_boost = 0.15  # Extra confidence for whale signals
    
    def train(self, historical_data: pd.DataFrame) -> bool:
        """Train whale detection model"""
        logger.info("Training WhaleCopyTraderPRO...")
        
        # Analyze historical whale activity correlation with price
        if 'whale_volume' in historical_data.columns:
            whale_correlation = historical_data['whale_volume'].corr(historical_data['price_change'])
            logger.info(f"Whale activity correlation: {whale_correlation:.3f}")
        
        self.is_trained = True
        logger.info("WhaleCopyTraderPRO training completed")
        return True
    
    def analyze_market(self, market_data: pd.DataFrame,
                        whale_data: Optional[List[Dict]] = None,
                        orderbook_data: Optional[Dict] = None) -> Optional[EdgeSignal]:
        """Analyze whale activity and generate copy signals"""
        
        if not self.is_trained:
            logger.warning("Model not trained, using default parameters")
        
        # Simulate whale detection
        # In reality, this would analyze actual blockchain transactions
        
        whale_signals = self._detect_whale_activity(market_data, whale_data)
        
        if whale_signals:
            # Aggregate whale signals
            total_whale_volume = sum(signal['volume'] for signal in whale_signals)
            avg_whale_confidence = np.mean([signal['confidence'] for signal in whale_signals])
            whale_direction = whale_signals[0]['direction']  # Assume first whale sets direction
            
            # Calculate confidence with whale boost
            confidence = min(0.95, avg_whale_confidence + self.confidence_boost)
            
            if confidence >= self.min_confidence:
                expected_value = confidence * 0.025  # 2.5% expected return
                
                return EdgeSignal(
                    type='buy' if whale_direction == 'bullish' else 'sell',
                    confidence=confidence,
                    expected_value=expected_value,
                    size=int(total_whale_volume / 1000),  # Size proportional to whale volume
                    model_name=self.name,
                    reasoning=f"Detected {len(whale_signals)} whale transactions totaling ${total_whale_volume:,.0f}",
                    timestamp=datetime.now(),
                    metadata={
                        'whale_count': len(whale_signals),
                        'total_volume': total_whale_volume,
                        'avg_confidence': avg_whale_confidence,
                        'direction': whale_direction
                    }
                )
        
        return None
    
    def _detect_whale_activity(self, market_data: pd.DataFrame, 
                                whale_data: Optional[List[Dict]]) -> List[Dict]:
        """Simulate whale activity detection"""
        
        # Simulate whale transactions based on market activity
        recent_volume = market_data['volume'].tail(6).mean()
        recent_price_change = (market_data['price'].iloc[-1] - market_data['price'].iloc[-6]) / market_data['price'].iloc[-6]
        
        whale_signals = []
        
        # Generate whale signals based on volume spikes
        if recent_volume > market_data['volume'].mean() * 1.5:  # Volume spike
            whale_count = np.random.randint(1, 4)  # 1-3 whales
            
            for i in range(whale_count):
                whale_volume = np.random.uniform(self.whale_threshold, self.whale_threshold * 5)
                direction = 'bullish' if recent_price_change > 0 else 'bearish'
                confidence = min(0.9, 0.6 + abs(recent_price_change) * 2)
                
                whale_signals.append({
                    'volume': whale_volume,
                    'direction': direction,
                    'confidence': confidence,
                    'timestamp': datetime.now() - timedelta(hours=i)
                })
        
        return whale_signals

class BayesianProbabilityUpdater(BaseEdgeModel):
    """
    Bayesian probability updating system
    
    Uses Bayesian inference to update probability estimates based on
    new evidence and market conditions.
    """
    
    def __init__(self, min_confidence: float = 0.68):
        super().__init__("BayesianProbabilityUpdater", min_confidence)
        self.prior_probability = 0.5  # Initial 50/50 probability
        self.evidence_weights = {
            'price_action': 0.3,
            'volume': 0.2,
            'volatility': 0.2,
            'external_factors': 0.3
        }
    
    def train(self, historical_data: pd.DataFrame) -> bool:
        """Train Bayesian model on historical data"""
        logger.info("Training BayesianProbabilityUpdater...")
        
        # Calculate historical win rates for different conditions
        if len(historical_data) > 100:
            # Calculate prior probability from historical data
            positive_outcomes = (historical_data['price_change'] > 0).sum()
            total_outcomes = len(historical_data)
            self.prior_probability = positive_outcomes / total_outcomes
            
            logger.info(f"Prior probability updated to: {self.prior_probability:.3f}")
        
        self.is_trained = True
        logger.info("BayesianProbabilityUpdater training completed")
        return True
    
    def analyze_market(self, market_data: pd.DataFrame,
                        external_data: Optional[Dict] = None) -> Optional[EdgeSignal]:
        """Update probabilities using Bayesian inference"""
        
        if not self.is_trained:
            logger.warning("Model not trained, using default parameters")
        
        # Gather evidence
        evidence = self._gather_evidence(market_data, external_data)
        
        # Update probability using Bayes' theorem
        posterior_probability = self._bayesian_update(evidence)
        
        # Generate signal if probability is significantly different from 50%
        probability_deviation = abs(posterior_probability - 0.5)
        confidence = probability_deviation * 2  # Scale to 0-1
        
        if confidence >= self.min_confidence:
            signal_type = 'buy' if posterior_probability > 0.5 else 'sell'
            expected_value = confidence * 0.02  # 2% expected return
            
            return EdgeSignal(
                type=signal_type,
                confidence=confidence,
                expected_value=expected_value,
                size=int(confidence * 120),
                model_name=self.name,
                reasoning=f"Bayesian probability updated to {posterior_probability:.3f} "
                         f"(deviation: {probability_deviation:.3f})",
                timestamp=datetime.now(),
                metadata={
                    'prior_probability': self.prior_probability,
                    'posterior_probability': posterior_probability,
                    'evidence_scores': evidence,
                    'probability_deviation': probability_deviation
                }
            )
        
        return None
    
    def _gather_evidence(self, market_data: pd.DataFrame, 
                        external_data: Optional[Dict]) -> Dict[str, float]:
        """Gather evidence from market data"""
        
        # Price action evidence
        recent_prices = market_data['price'].tail(24)
        price_trend = (recent_prices.iloc[-1] - recent_prices.iloc[0]) / recent_prices.iloc[0]
        price_evidence = np.clip(price_trend * 5, -1, 1)
        
        # Volume evidence
        recent_volume = market_data['volume'].tail(6).mean()
        avg_volume = market_data['volume'].mean()
        volume_evidence = np.clip((recent_volume - avg_volume) / avg_volume, -1, 1)
        
        # Volatility evidence
        recent_volatility = market_data['price'].tail(12).std() / market_data['price'].tail(12).mean()
        avg_volatility = market_data['price'].std() / market_data['price'].mean()
        volatility_evidence = np.clip(1 - (recent_volatility / avg_volatility), -1, 1)
        
        # External factors evidence
        external_evidence = 0
        if external_data:
            # Simulate external factors (news, events, etc.)
            news_sentiment = external_data.get('news_sentiment', 0)
            event_impact = external_data.get('event_impact', 0)
            external_evidence = (news_sentiment + event_impact) / 2
        
        return {
            'price_action': price_evidence,
            'volume': volume_evidence,
            'volatility': volatility_evidence,
            'external_factors': external_evidence
        }
    
    def _bayesian_update(self, evidence: Dict[str, float]) -> float:
        """Apply Bayesian update to probability"""
        
        # Calculate weighted evidence
        weighted_evidence = sum(
            evidence[key] * self.evidence_weights[key] 
            for key in evidence.keys()
        )
        
        # Apply Bayesian update (simplified)
        # P(H|E) = P(E|H) * P(H) / P(E)
        
        # Likelihood of evidence given hypothesis
        likelihood_positive = 0.5 + weighted_evidence * 0.3  # If hypothesis is true
        likelihood_negative = 0.5 - weighted_evidence * 0.3  # If hypothesis is false
        
        # Normalize likelihoods
        total_likelihood = likelihood_positive + likelihood_negative
        if total_likelihood > 0:
            likelihood_positive /= total_likelihood
            likelihood_negative /= total_likelihood
        
        # Apply Bayes' theorem
        prior_positive = self.prior_probability
        prior_negative = 1 - self.prior_probability
        
        # Posterior probability
        posterior_positive = (likelihood_positive * prior_positive) / (
            likelihood_positive * prior_positive + likelihood_negative * prior_negative
        )
        
        return posterior_positive

class MispricingDetector(BaseEdgeModel):
    """
    Market mispricing detection system
    
    Identifies price discrepancies between related markets and
    generates arbitrage-style trading signals.
    """
    
    def __init__(self, min_confidence: float = 0.72):
        super().__init__("MispricingDetector", min_confidence)
        self.mispricing_threshold = 0.02  # 2% price difference
        self.mean_reversion_speed = 0.1  # Speed of price convergence
        self.correlation_threshold = 0.7  # Minimum correlation for comparison
    
    def train(self, historical_data: pd.DataFrame) -> bool:
        """Train mispricing detection model"""
        logger.info("Training MispricingDetector...")
        
        # Calculate historical mispricing patterns
        if len(historical_data) > 50:
            # Analyze mean reversion speed
            price_changes = historical_data['price'].pct_change()
            mean_reversion_periods = []
            
            for i in range(1, len(price_changes) - 10):
                if abs(price_changes.iloc[i]) > 0.02:  # Large price move
                    # Check how long it takes to revert
                    for j in range(1, 11):
                        if i + j < len(price_changes):
                            cumulative_return = price_changes.iloc[i+1:i+j+1].sum()
                            if abs(cumulative_return) < 0.005:  # Reverted to within 0.5%
                                mean_reversion_periods.append(j)
                                break
            
            if mean_reversion_periods:
                avg_reversion_period = np.mean(mean_reversion_periods)
                self.mean_reversion_speed = 1.0 / avg_reversion_period
                logger.info(f"Mean reversion speed: {self.mean_reversion_speed:.3f}")
        
        self.is_trained = True
        logger.info("MispricingDetector training completed")
        return True
    
    def analyze_market(self, market_data: pd.DataFrame,
                        comparison_data: Optional[Dict[str, pd.DataFrame]] = None) -> Optional[EdgeSignal]:
        """Detect mispricing opportunities"""
        
        if not self.is_trained:
            logger.warning("Model not trained, using default parameters")
        
        # Detect mispricing in current market
        current_mispricing = self._detect_current_mispricing(market_data)
        
        # Compare with related markets if available
        comparative_mispricing = None
        if comparison_data:
            comparative_mispricing = self._detect_comparative_mispricing(market_data, comparison_data)
        
        # Use the strongest mispricing signal
        best_signal = self._select_best_mispricing_signal(current_mispricing, comparative_mispricing)
        
        if best_signal and best_signal['confidence'] >= self.min_confidence:
            signal_type = best_signal['direction']
            confidence = best_signal['confidence']
            expected_value = confidence * 0.035  # 3.5% expected return for mispricing
            
            return EdgeSignal(
                type=signal_type,
                confidence=confidence,
                expected_value=expected_value,
                size=int(confidence * 140),  # Larger size for mispricing opportunities
                model_name=self.name,
                reasoning=best_signal['reasoning'],
                timestamp=datetime.now(),
                metadata={
                    'mispricing_type': best_signal['type'],
                    'price_deviation': best_signal['deviation'],
                    'mean_reversion_speed': self.mean_reversion_speed,
                    'expected_convergence_time': best_signal.get('convergence_time', 24)
                }
            )
        
        return None
    
    def _detect_current_mispricing(self, market_data: pd.DataFrame) -> Optional[Dict]:
        """Detect mispricing in current market using statistical methods"""
        
        # Calculate fair value using multiple methods
        recent_prices = market_data['price'].tail(48)
        
        # Method 1: Moving average deviation
        ma_24 = recent_prices.tail(24).mean()
        ma_48 = recent_prices.mean()
        fair_value_ma = (ma_24 + ma_48) / 2
        
        # Method 2: Volume-weighted average
        recent_volume = market_data['volume'].tail(48)
        vwap = (recent_prices * recent_volume).sum() / recent_volume.sum()
        
        # Method 3: Median price (robust to outliers)
        median_price = recent_prices.median()
        
        # Combine methods
        fair_value = (fair_value_ma + vwap + median_price) / 3
        current_price = recent_prices.iloc[-1]
        
        # Calculate deviation
        deviation = (current_price - fair_value) / fair_value
        
        if abs(deviation) > self.mispricing_threshold:
            # Determine direction and confidence
            direction = 'buy' if deviation < 0 else 'sell'
            confidence = min(0.9, abs(deviation) * 20)  # Scale confidence
            
            # Estimate convergence time based on mean reversion speed
            convergence_time = int(abs(deviation) / self.mean_reversion_speed) if self.mean_reversion_speed > 0 else 24
            
            return {
                'type': 'statistical',
                'direction': direction,
                'confidence': confidence,
                'deviation': deviation,
                'convergence_time': min(convergence_time, 72),  # Cap at 72 hours
                'reasoning': f"Price deviation of {deviation:.2%} from fair value (${fair_value:.4f})"
            }
        
        return None
    
    def _detect_comparative_mispricing(self, market_data: pd.DataFrame, 
                                      comparison_data: Dict[str, pd.DataFrame]) -> Optional[Dict]:
        """Detect mispricing by comparing with related markets"""
        
        current_price = market_data['price'].iloc[-1]
        mispricing_signals = []
        
        for market_name, comparison_market in comparison_data.items():
            if len(comparison_market) < 24:
                continue
            
            # Calculate correlation
            correlation = market_data['price'].tail(48).corr(comparison_market['price'].tail(48))
            
            if correlation > self.correlation_threshold:
                # Calculate expected price based on correlation
                comparison_price = comparison_market['price'].iloc[-1]
                comparison_change = (comparison_market['price'].iloc[-1] - 
                                   comparison_market['price'].iloc[-24]) / comparison_market['price'].iloc[-24]
                
                # Expected price based on correlation and comparison market movement
                expected_change = comparison_change * correlation
                expected_price = market_data['price'].iloc[-24] * (1 + expected_change)
                
                # Calculate deviation
                deviation = (current_price - expected_price) / expected_price
                
                if abs(deviation) > self.mispricing_threshold:
                    direction = 'buy' if deviation < 0 else 'sell'
                    confidence = min(0.85, abs(deviation) * 15 + correlation * 0.2)
                    
                    mispricing_signals.append({
                        'type': 'comparative',
                        'direction': direction,
                        'confidence': confidence,
                        'deviation': deviation,
                        'correlation': correlation,
                        'comparison_market': market_name,
                        'reasoning': f"Price deviation of {deviation:.2%} from correlated market ({market_name})"
                    })
        
        # Return the strongest signal
        if mispricing_signals:
            return max(mispricing_signals, key=lambda x: x['confidence'])
        
        return None
    
    def _select_best_mispricing_signal(self, current_mispricing: Optional[Dict], 
                                     comparative_mispricing: Optional[Dict]) -> Optional[Dict]:
        """Select the best mispricing signal"""
        
        signals = []
        if current_mispricing:
            signals.append(current_mispricing)
        if comparative_mispricing:
            signals.append(comparative_mispricing)
        
        if not signals:
            return None
        
        # Return the signal with highest confidence
        return max(signals, key=lambda x: x['confidence'])

class DynamicSignalEnsemble:
    """
    Dynamic ensemble of edge models
    
    Combines signals from multiple edge models using weighted averaging
    and adaptive confidence thresholds.
    """
    
    def __init__(self, models: List[BaseEdgeModel], ensemble_confidence: float = 0.75):
        self.models = models
        self.ensemble_confidence = ensemble_confidence
        self.model_weights = self._initialize_model_weights()
        self.performance_history = {}
    
    def _initialize_model_weights(self) -> Dict[str, float]:
        """Initialize equal weights for all models"""
        n_models = len(self.models)
        return {model.name: 1.0 / n_models for model in self.models}
    
    def train_all_models(self, historical_data: pd.DataFrame) -> bool:
        """Train all edge models"""
        logger.info("Training all edge models...")
        
        success_count = 0
        for model in self.models:
            try:
                if model.train(historical_data):
                    success_count += 1
                    logger.info(f"✅ {model.name} trained successfully")
                else:
                    logger.warning(f"⚠️  {model.name} training failed")
            except Exception as e:
                logger.error(f"❌ {model.name} training error: {e}")
        
        logger.info(f"Training completed: {success_count}/{len(self.models)} models trained")
        return success_count > 0
    
    def generate_ensemble_signal(self, market_data: pd.DataFrame,
                                  **additional_data) -> Optional[EdgeSignal]:
        """Generate ensemble signal from all models"""
        
        # Collect signals from all models
        model_signals = []
        
        for model in self.models:
            try:
                # Get model-specific data
                model_data = additional_data.get(model.name, {})
                
                signal = model.analyze_market(market_data, **model_data)
                if signal:
                    model_signals.append(signal)
                    logger.debug(f"{model.name} generated signal: {signal.type} (confidence: {signal.confidence:.3f})")
            except Exception as e:
                logger.error(f"Error generating signal from {model.name}: {e}")
        
        if not model_signals:
            logger.info("No signals generated by any model")
            return None
        
        # Combine signals using weighted averaging
        ensemble_signal = self._combine_signals(model_signals)
        
        if ensemble_signal and ensemble_signal.confidence >= self.ensemble_confidence:
            logger.info(f"Ensemble signal generated: {ensemble_signal.type} "
                       f"(confidence: {ensemble_signal.confidence:.3f}, "
                       f"models: {len(model_signals)}/{len(self.models)})")
            return ensemble_signal
        
        logger.info(f"Ensemble signal below confidence threshold "
                   f"({ensemble_signal.confidence:.3f} < {self.ensemble_confidence})")
        return None
    
    def _combine_signals(self, signals: List[EdgeSignal]) -> Optional[EdgeSignal]:
        """Combine multiple signals into ensemble signal"""
        
        if not signals:
            return None
        
        # Calculate weighted averages
        total_weight = sum(self.model_weights[signal.model_name] for signal in signals)
        
        # Determine dominant signal type
        buy_signals = [s for s in signals if s.type == 'buy']
        sell_signals = [s for s in signals if s.type == 'sell']
        
        if len(buy_signals) > len(sell_signals):
            signal_type = 'buy'
            relevant_signals = buy_signals
        elif len(sell_signals) > len(buy_signals):
            signal_type = 'sell'
            relevant_signals = sell_signals
        else:
            # Equal number, use confidence-weighted decision
            buy_confidence = sum(s.confidence for s in buy_signals)
            sell_confidence = sum(s.confidence for s in sell_signals)
            
            if buy_confidence > sell_confidence:
                signal_type = 'buy'
                relevant_signals = buy_signals
            else:
                signal_type = 'sell'
                relevant_signals = sell_signals
        
        # Calculate weighted confidence and expected value
        weighted_confidence = sum(
            signal.confidence * self.model_weights[signal.model_name]
            for signal in relevant_signals
        ) / total_weight
        
        weighted_expected_value = sum(
            signal.expected_value * self.model_weights[signal.model_name]
            for signal in relevant_signals
        ) / total_weight
        
        # Calculate weighted size
        weighted_size = int(sum(
            signal.size * self.model_weights[signal.model_name]
            for signal in relevant_signals
        ) / total_weight)
        
        # Create reasoning summary
        model_names = [signal.model_name for signal in relevant_signals]
        reasoning = f"Ensemble of {len(relevant_signals)} models: {', '.join(model_names)}"
        
        return EdgeSignal(
            type=signal_type,
            confidence=weighted_confidence,
            expected_value=weighted_expected_value,
            size=weighted_size,
            model_name="DynamicSignalEnsemble",
            reasoning=reasoning,
            timestamp=datetime.now(),
            metadata={
                'contributing_models': len(relevant_signals),
                'total_models': len(self.models),
                'individual_signals': [
                    {
                        'model': s.model_name,
                        'confidence': s.confidence,
                        'expected_value': s.expected_value
                    } for s in relevant_signals
                ]
            }
        )
    
    def update_model_performance(self, model_name: str, performance: float):
        """Update model weights based on performance"""
        
        if model_name not in self.performance_history:
            self.performance_history[model_name] = []
        
        self.performance_history[model_name].append(performance)
        
        # Keep only recent performance (last 20 trades)
        if len(self.performance_history[model_name]) > 20:
            self.performance_history[model_name] = self.performance_history[model_name][-20:]
        
        # Update weights based on average performance
        self._update_weights_from_performance()
    
    def _update_weights_from_performance(self):
        """Update model weights based on historical performance"""
        
        if not self.performance_history:
            return
        
        # Calculate average performance for each model
        avg_performances = {}
        for model_name, performances in self.performance_history.items():
            if performances:
                avg_performances[model_name] = np.mean(performances)
            else:
                avg_performances[model_name] = 0
        
        # Convert to weights (softmax normalization)
        performance_values = list(avg_performances.values())
        if max(performance_values) > min(performance_values):
            exp_values = np.exp(np.array(performance_values) - max(performance_values))
            weights = exp_values / exp_values.sum()
            
            # Update weights
            for i, model_name in enumerate(avg_performances.keys()):
                self.model_weights[model_name] = weights[i]
        
        logger.info(f"Updated model weights: {self.model_weights}")

# Factory function to create complete ensemble
def create_advanced_edge_ensemble() -> DynamicSignalEnsemble:
    """Create a complete ensemble of all advanced edge models"""
    
    models = [
        AdvancedLLMSentimentEngine(),
        WhaleCopyTraderPRO(),
        BayesianProbabilityUpdater(),
        MispricingDetector()
    ]
    
    return DynamicSignalEnsemble(models)

# Example usage and testing
if __name__ == "__main__":
    """Test the advanced edge models"""
    
    logging.basicConfig(level=logging.INFO)
    
    print("🧪 Testing Advanced Edge Models v3.0...")
    
    # Create sample market data
    dates = pd.date_range(start='2023-01-01', periods=100, freq='h')
    prices = 0.5 + np.cumsum(np.random.normal(0, 0.001, 100)) + np.sin(np.arange(100) * 0.1) * 0.05
    volumes = np.random.lognormal(10, 1, 100)
    spreads = np.random.exponential(0.005, 100)
    
    market_data = pd.DataFrame({
        'timestamp': dates,
        'price': prices,
        'volume': volumes,
        'spread': spreads
    })
    
    # Create ensemble
    ensemble = create_advanced_edge_ensemble()
    
    # Train models
    print("📚 Training models...")
    ensemble.train_all_models(market_data)
    
    # Generate ensemble signal
    print("\n🎯 Generating ensemble signal...")
    
    # Add some sample additional data
    additional_data = {
        'AdvancedLLMSentimentEngine': {
            'news_data': [
                {'text': 'Market shows bullish momentum', 'timestamp': datetime.now()},
                {'text': 'Positive sentiment growing', 'timestamp': datetime.now()}
            ],
            'social_data': [
                {'text': 'Bullish on this market', 'likes': 100, 'comments': 20},
                {'text': 'Great opportunity here', 'likes': 150, 'comments': 30}
            ]
        },
        'WhaleCopyTraderPRO': {
            'whale_data': [
                {'volume': 150000, 'direction': 'bullish', 'timestamp': datetime.now()},
                {'volume': 200000, 'direction': 'bullish', 'timestamp': datetime.now()}
            ]
        },
        'BayesianProbabilityUpdater': {
            'external_data': {
                'news_sentiment': 0.7,
                'event_impact': 0.5
            }
        },
        'MispricingDetector': {
            'comparison_data': {
                'related_market_1': pd.DataFrame({
                    'price': prices * 0.95 + np.random.normal(0, 0.001, 100)
                }),
                'related_market_2': pd.DataFrame({
                    'price': prices * 1.05 + np.random.normal(0, 0.001, 100)
                })
            }
        }
    }
    
    signal = ensemble.generate_ensemble_signal(market_data, **additional_data)
    
    if signal:
        print(f"✅ Signal generated!")
        print(f"   Type: {signal.type}")
        print(f"   Confidence: {signal.confidence:.3f}")
        print(f"   Expected Value: {signal.expected_value:.3f}")
        print(f"   Size: {signal.size}")
        print(f"   Reasoning: {signal.reasoning}")
        print(f"   Contributing Models: {signal.metadata['contributing_models']}")
    else:
        print("❌ No signal generated")
    
    print("\n✅ Advanced Edge Models v3.0 test completed!")