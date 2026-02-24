#!/usr/bin/env python3
"""
LLM Sentiment Engine for Polymarket Bot Arena v3.0

This module provides advanced sentiment analysis using LLM-like techniques
for market prediction based on news, social media, and other text sources.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import re
from collections import Counter
import json

logger = logging.getLogger(__name__)

@dataclass
class SentimentSignal:
    """Represents a sentiment-based signal"""
    sentiment_score: float  # -1 to 1
    confidence: float  # 0 to 1
    source: str  # news, social, etc.
    text_snippet: str  # Sample text
    keywords: List[str]  # Key sentiment words
    timestamp: datetime

class AdvancedLLMSentimentEngine:
    """
    Advanced LLM-like sentiment analysis engine
    
    Analyzes text data using sophisticated sentiment analysis techniques
    similar to what LLMs would use, including context awareness and
    multi-dimensional sentiment scoring.
    """
    
    def __init__(self, confidence_threshold: float = 0.7):
        self.confidence_threshold = confidence_threshold
        self.sentiment_lexicon = self._build_sentiment_lexicon()
        self.context_weights = self._initialize_context_weights()
        self.entity_recognizer = EntityRecognizer()
        self.context_analyzer = ContextAnalyzer()
        self.sentiment_history = []
        self.adaptation_rate = 0.02
        self.max_history_size = 1000
    
    def _build_sentiment_lexicon(self) -> Dict[str, Dict[str, float]]:
        """Build comprehensive sentiment lexicon for prediction markets"""
        
        lexicon = {
            'positive': {
                'bullish': 0.8, 'bull': 0.7, 'rally': 0.8, 'surge': 0.7, 'soar': 0.8,
                'moon': 0.9, 'pump': 0.6, 'green': 0.6, 'up': 0.5, 'rise': 0.6,
                'gain': 0.6, 'profit': 0.7, 'win': 0.8, 'success': 0.8, 'breakthrough': 0.9,
                'milestone': 0.7, 'achievement': 0.8, 'victory': 0.9, 'triumph': 0.9,
                'dominate': 0.7, 'leading': 0.6, 'strong': 0.6, 'robust': 0.7,
                'solid': 0.5, 'healthy': 0.5, 'positive': 0.6, 'optimistic': 0.7,
                'confident': 0.6, 'promising': 0.7, 'bright': 0.6, 'favorable': 0.6,
                'advantage': 0.5, 'benefit': 0.5, 'improve': 0.6, 'enhance': 0.6,
                'boost': 0.7, 'increase': 0.5, 'grow': 0.6, 'expand': 0.6,
                'accelerate': 0.7, 'momentum': 0.7, 'trending': 0.5, 'viral': 0.8,
                'popular': 0.5, 'demand': 0.5, 'interest': 0.4, 'attention': 0.4,
                'buzz': 0.6, 'hype': 0.6, 'excitement': 0.7, 'enthusiasm': 0.7
            },
            'negative': {
                'bearish': -0.8, 'bear': -0.7, 'crash': -0.9, 'dump': -0.7, 'tank': -0.8,
                'plunge': -0.8, 'collapse': -0.9, 'fall': -0.6, 'drop': -0.6, 'decline': -0.6,
                'loss': -0.7, 'lose': -0.7, 'fail': -0.8, 'failure': -0.8, 'disaster': -0.9,
                'catastrophe': -0.9, 'crisis': -0.8, 'problem': -0.6, 'issue': -0.5,
                'concern': -0.5, 'worry': -0.5, 'fear': -0.7, 'panic': -0.8,
                'scared': -0.6, 'anxious': -0.5, 'nervous': -0.5, 'uncertain': -0.6,
                'doubt': -0.5, 'skeptical': -0.5, 'pessimistic': -0.6, 'negative': -0.6,
                'weak': -0.6, 'fragile': -0.7, 'vulnerable': -0.6, 'risky': -0.6,
                'dangerous': -0.7, 'threat': -0.6, 'warning': -0.6, 'caution': -0.5,
                'volatile': -0.5, 'unstable': -0.7, 'erratic': -0.6, 'manipulation': -0.7,
                'scam': -0.9, 'fraud': -0.9, 'fake': -0.8, 'false': -0.6,
                'misleading': -0.7, 'deceptive': -0.7, 'corrupt': -0.8, 'illegal': -0.8
            },
            'uncertainty': {
                'maybe': -0.2, 'perhaps': -0.2, 'possibly': -0.2, 'potentially': -0.1,
                'could': -0.1, 'might': -0.1, 'may': -0.1, 'uncertain': -0.3,
                'unknown': -0.3, 'unclear': -0.3, 'ambiguous': -0.3, 'confusing': -0.3,
                'mixed': -0.2, 'neutral': -0.1, 'sideways': -0.2, 'consolidation': -0.1,
                'waiting': -0.2, 'patience': -0.1, 'hesitation': -0.2, 'delay': -0.1,
                'postpone': -0.1, 'cancel': -0.3, 'postponed': -0.2, 'delayed': -0.1
            },
            'market_specific': {
                'buy': 0.6, 'bought': 0.5, 'purchasing': 0.5, 'accumulate': 0.6,
                'hodl': 0.4, 'hold': 0.2, 'selling': -0.5, 'sell': -0.6, 'sold': -0.5,
                'short': -0.7, 'shorting': -0.7, 'long': 0.6, 'leverage': 0.3,
                'margin': 0.2, 'liquidation': -0.8, 'margin_call': -0.7, 'stop_loss': -0.4,
                'take_profit': 0.5, 'support': 0.5, 'resistance': -0.5, 'breakout': 0.7,
                'breakdown': -0.7, 'reversal': 0.4, 'correction': -0.4, 'pullback': -0.3,
                'bounce': 0.4, 'recovery': 0.6, 'oversold': 0.6, 'overbought': -0.6,
                'divergence': 0.3, 'convergence': 0.3, 'consolidation': -0.1, 'range': -0.1
            }
        }
        
        return lexicon
    
    def _initialize_context_weights(self) -> Dict[str, float]:
        """Initialize context-aware weights"""
        
        return {
            'news_headline': 0.8,      # High impact
            'news_article': 0.7,         # High impact
            'social_tweet': 0.6,         # Medium-high impact
            'social_reddit': 0.5,        # Medium impact
            'social_discord': 0.4,       # Medium impact
            'forum_post': 0.5,           # Medium impact
            'youtube_title': 0.6,        # Medium-high impact
            'youtube_description': 0.5,  # Medium impact
            'blog_post': 0.6,            # Medium impact
            'podcast_title': 0.4,         # Low-medium impact
            'podcast_transcript': 0.5,    # Medium impact
            'telegram_message': 0.7,      # High impact (crypto-specific)
            'whale_alert': 0.9,           # Very high impact
            'official_announcement': 0.9, # Very high impact
            'rumor': 0.3,                # Low impact (unverified)
            'speculation': 0.4            # Low-medium impact
        }
    
    def analyze_text_sentiment(self, text: str, source: str = 'unknown',
                             market_context: Optional[Dict[str, Any]] = None) -> SentimentSignal:
        """
        Analyze sentiment of text using LLM-like techniques
        
        Args:
            text: Text to analyze
            source: Source of the text (news, social, etc.)
            market_context: Additional market context
        
        Returns:
            SentimentSignal object
        """
        
        if not text or not text.strip():
            return SentimentSignal(
                sentiment_score=0.0,
                confidence=0.0,
                source=source,
                text_snippet="",
                keywords=[],
                timestamp=datetime.now()
            )
        
        # Preprocess text
        clean_text = self._preprocess_text(text)
        
        # Extract entities
        entities = self.entity_recognizer.extract_entities(clean_text)
        
        # Analyze context
        context_score = self.context_analyzer.analyze_context(clean_text, entities, market_context)
        
        # Calculate base sentiment scores
        sentiment_scores = self._calculate_sentiment_scores(clean_text, entities)
        
        # Apply context and source weights
        weighted_sentiment = self._apply_weights(sentiment_scores, context_score, source)
        
        # Calculate confidence
        confidence = self._calculate_confidence(clean_text, sentiment_scores, source)
        
        # Extract key sentiment words
        keywords = self._extract_keywords(clean_text, sentiment_scores)
        
        # Create signal
        signal = SentimentSignal(
            sentiment_score=weighted_sentiment,
            confidence=confidence,
            source=source,
            text_snippet=clean_text[:200] + "..." if len(clean_text) > 200 else clean_text,
            keywords=keywords[:10],  # Top 10 keywords
            timestamp=datetime.now()
        )
        
        # Store in history
        self.sentiment_history.append(signal)
        if len(self.sentiment_history) > self.max_history_size:
            self.sentiment_history = self.sentiment_history[-self.max_history_size:]
        
        return signal
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for analysis"""
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove special characters but keep punctuation for context
        text = re.sub(r'[^\w\s.,!?;:\-\'"()]', ' ', text)
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def _calculate_sentiment_scores(self, text: str, entities: List[str]) -> Dict[str, float]:
        """Calculate sentiment scores from text"""
        
        scores = {
            'positive': 0.0,
            'negative': 0.0,
            'uncertainty': 0.0,
            'market_specific': 0.0
        }
        
        words = text.split()
        total_words = len(words)
        
        if total_words == 0:
            return scores
        
        # Count sentiment words
        sentiment_word_counts = Counter()
        
        for category, word_scores in self.sentiment_lexicon.items():
            for word, score in word_scores.items():
                count = text.count(word)
                if count > 0:
                    sentiment_word_counts[category] += count
                    scores[category] += score * count
        
        # Normalize by word count
        for category in scores:
            if sentiment_word_counts[category] > 0:
                scores[category] /= sentiment_word_counts[category]
            else:
                scores[category] = 0.0
        
        # Apply entity-based adjustments
        entity_adjustment = self._apply_entity_adjustments(text, entities)
        for category in scores:
            scores[category] += entity_adjustment.get(category, 0)
        
        return scores
    
    def _apply_entity_adjustments(self, text: str, entities: List[str]) -> Dict[str, float]:
        """Apply adjustments based on recognized entities"""
        
        adjustments = {'positive': 0, 'negative': 0, 'uncertainty': 0, 'market_specific': 0}
        
        # Market-specific entity adjustments
        market_entities = {
            'bullish': {'positive': 0.2, 'market_specific': 0.1},
            'bearish': {'negative': 0.2, 'market_specific': 0.1},
            'pump': {'positive': 0.1, 'market_specific': 0.2},
            'dump': {'negative': 0.1, 'market_specific': 0.2},
            'hodl': {'positive': 0.1, 'market_specific': 0.1},
            'fomo': {'positive': 0.1, 'uncertainty': 0.1},
            'fud': {'negative': 0.1, 'uncertainty': 0.1}
        }
        
        for entity in entities:
            if entity in market_entities:
                entity_adj = market_entities[entity]
                for category, adjustment in entity_adj.items():
                    adjustments[category] += adjustment
        
        return adjustments
    
    def _apply_weights(self, sentiment_scores: Dict[str, float], 
                      context_score: float, source: str) -> float:
        """Apply weights to sentiment scores"""
        
        # Base sentiment calculation
        positive_score = sentiment_scores['positive']
        negative_score = sentiment_scores['negative']
        uncertainty_score = sentiment_scores['uncertainty']
        market_score = sentiment_scores['market_specific']
        
        # Calculate net sentiment
        net_sentiment = positive_score - negative_score - (uncertainty_score * 0.5) + market_score
        
        # Apply context adjustment
        net_sentiment += context_score * 0.3
        
        # Apply source weight
        source_weight = self.context_weights.get(source, 0.5)
        net_sentiment *= source_weight
        
        # Normalize to -1 to 1
        return np.clip(net_sentiment, -1.0, 1.0)
    
    def _calculate_confidence(self, text: str, sentiment_scores: Dict[str, float], source: str) -> float:
        """Calculate confidence in sentiment analysis"""
        
        # Base confidence from text length and clarity
        text_length = len(text.split())
        length_confidence = min(1.0, text_length / 20)  # More words = more confidence
        
        # Confidence from sentiment strength
        max_sentiment_strength = max(abs(sentiment_scores['positive']), 
                                   abs(sentiment_scores['negative']),
                                   abs(sentiment_scores['market_specific']))
        sentiment_confidence = max_sentiment_strength
        
        # Confidence from source reliability
        source_confidence = self.context_weights.get(source, 0.5)
        
        # Combined confidence
        confidence = (length_confidence * 0.3 + 
                     sentiment_confidence * 0.4 + 
                     source_confidence * 0.3)
        
        return np.clip(confidence, 0.0, 1.0)
    
    def _extract_keywords(self, text: str, sentiment_scores: Dict[str, float]) -> List[str]:
        """Extract key sentiment words from text"""
        
        keywords = []
        
        # Find sentiment words in text
        for category, word_scores in self.sentiment_lexicon.items():
            for word, score in word_scores.items():
                if word in text and abs(score) > 0.5:  # Strong sentiment words
                    keywords.append(word)
        
        # Remove duplicates and sort by relevance
        keywords = list(set(keywords))
        keywords.sort(key=lambda x: abs(self._get_word_sentiment_score(x)), reverse=True)
        
        return keywords
    
    def _get_word_sentiment_score(self, word: str) -> float:
        """Get sentiment score for a specific word"""
        
        for category, word_scores in self.sentiment_lexicon.items():
            if word in word_scores:
                return word_scores[word]
        
        return 0.0
    
    def analyze_multiple_sources(self, text_sources: List[Dict[str, Any]], 
                               market_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze sentiment from multiple text sources
        
        Args:
            text_sources: List of {'text': str, 'source': str, 'timestamp': datetime} dicts
            market_context: Market context information
        
        Returns:
            Aggregated sentiment analysis
        """
        
        if not text_sources:
            return {
                'overall_sentiment': 0.0,
                'confidence': 0.0,
                'signals': [],
                'sources_analyzed': 0
            }
        
        signals = []
        
        for source_data in text_sources:
            text = source_data.get('text', '')
            source = source_data.get('source', 'unknown')
            
            signal = self.analyze_text_sentiment(text, source, market_context)
            signals.append(signal)
        
        # Aggregate signals
        aggregated = self._aggregate_signals(signals)
        
        return aggregated
    
    def _aggregate_signals(self, signals: List[SentimentSignal]) -> Dict[str, Any]:
        """Aggregate multiple sentiment signals"""
        
        if not signals:
            return {
                'overall_sentiment': 0.0,
                'confidence': 0.0,
                'signals': [],
                'sources_analyzed': 0
            }
        
        # Calculate weighted average sentiment
        total_weight = sum(signal.confidence for signal in signals)
        
        if total_weight == 0:
            weighted_sentiment = 0.0
            average_confidence = 0.0
        else:
            weighted_sentiment = sum(signal.sentiment_score * signal.confidence 
                                   for signal in signals) / total_weight
            average_confidence = sum(signal.confidence for signal in signals) / len(signals)
        
        # Calculate sentiment strength (how strong the overall sentiment is)
        positive_signals = [s for s in signals if s.sentiment_score > 0]
        negative_signals = [s for s in signals if s.sentiment_score < 0]
        
        sentiment_strength = abs(weighted_sentiment)
        
        # Determine dominant sentiment
        if weighted_sentiment > 0.3:
            dominant_sentiment = 'bullish'
        elif weighted_sentiment < -0.3:
            dominant_sentiment = 'bearish'
        else:
            dominant_sentiment = 'neutral'
        
        return {
            'overall_sentiment': weighted_sentiment,
            'confidence': average_confidence,
            'sentiment_strength': sentiment_strength,
            'dominant_sentiment': dominant_sentiment,
            'positive_signals': len(positive_signals),
            'negative_signals': len(negative_signals),
            'neutral_signals': len(signals) - len(positive_signals) - len(negative_signals),
            'signals': signals,
            'sources_analyzed': len(signals)
        }
    
    def adapt_from_feedback(self, predicted_sentiment: float, actual_outcome: float, 
                          confidence: float):
        """
        Adapt sentiment analysis based on actual outcomes
        
        This is a simplified version - in a real implementation,
        you would use machine learning to adapt the lexicon
        """
        
        # Calculate prediction error
        prediction_error = abs(predicted_sentiment - actual_outcome)
        
        # Only adapt if error is significant and confidence was high
        if prediction_error > 0.5 and confidence > 0.7:
            # Slightly adjust confidence threshold
            adjustment = prediction_error * self.adaptation_rate
            
            if predicted_sentiment > actual_outcome:
                # We were too optimistic, increase threshold
                self.confidence_threshold = min(0.9, self.confidence_threshold + adjustment)
            else:
                # We were too pessimistic, decrease threshold  
                self.confidence_threshold = max(0.5, self.confidence_threshold - adjustment)
            
            logger.info(f"Adapted confidence threshold to {self.confidence_threshold:.3f} "
                       f"based on prediction error {prediction_error:.3f}")
    
    def get_sentiment_trend(self, timeframe: timedelta = timedelta(hours=24)) -> Dict[str, Any]:
        """Get sentiment trend over specified timeframe"""
        
        cutoff_time = datetime.now() - timeframe
        recent_signals = [s for s in self.sentiment_history if s.timestamp >= cutoff_time]
        
        if not recent_signals:
            return {
                'trend': 'insufficient_data',
                'change': 0.0,
                'signals_count': 0,
                'average_sentiment': 0.0
            }
        
        # Calculate trend
        if len(recent_signals) >= 2:
            recent_avg = np.mean([s.sentiment_score for s in recent_signals[-10:]])
            older_avg = np.mean([s.sentiment_score for s in recent_signals[:-10] if len(recent_signals) > 10])
            
            if len(recent_signals) > 10:
                change = recent_avg - older_avg
            else:
                change = recent_avg - np.mean([s.sentiment_score for s in recent_signals[:len(recent_signals)//2]])
            
            if change > 0.1:
                trend = 'increasing_positive'
            elif change < -0.1:
                trend = 'increasing_negative'
            else:
                trend = 'stable'
        else:
            change = 0.0
            trend = 'insufficient_data'
        
        return {
            'trend': trend,
            'change': change,
            'signals_count': len(recent_signals),
            'average_sentiment': np.mean([s.sentiment_score for s in recent_signals]),
            'confidence_trend': np.mean([s.confidence for s in recent_signals[-10:]]) - 
                               np.mean([s.confidence for s in recent_signals[:10]]) if len(recent_signals) >= 20 else 0
        }

class EntityRecognizer:
    """Simple entity recognition for market-related terms"""
    
    def __init__(self):
        self.market_entities = {
            'cryptocurrencies': ['bitcoin', 'btc', 'ethereum', 'eth', 'cardano', 'ada', 'solana', 'sol',
                             'polkadot', 'dot', 'chainlink', 'link', 'polygon', 'matic', 'avalanche', 'avax'],
            'market_terms': ['bull', 'bear', 'bullish', 'bearish', 'pump', 'dump', 'moon', 'hodl', 'fomo', 'fud'],
            'trading_terms': ['buy', 'sell', 'long', 'short', 'leverage', 'margin', 'liquidation', 'stop_loss'],
            'sentiment_terms': ['moon', 'lambo', 'rocket', 'diamond_hands', 'paper_hands', 'ape', 'degen']
        }
    
    def extract_entities(self, text: str) -> List[str]:
        """Extract entities from text"""
        
        text_lower = text.lower()
        entities = []
        
        for category, entity_list in self.market_entities.items():
            for entity in entity_list:
                if entity in text_lower:
                    entities.append(entity)
        
        return entities

class ContextAnalyzer:
    """Analyze context of sentiment expressions"""
    
    def __init__(self):
        self.negation_words = ['not', 'no', 'never', 'nothing', 'nobody', 'nowhere', 'neither', 'none']
        self.intensifiers = ['very', 'extremely', 'really', 'quite', 'rather', 'pretty', 'so', 'too']
        self.diminishers = ['somewhat', 'slightly', 'a_bit', 'kind_of', 'sort_of', 'rather']
    
    def analyze_context(self, text: str, entities: List[str], 
                       market_context: Optional[Dict[str, Any]] = None) -> float:
        """Analyze context and return context score"""
        
        context_score = 0.0
        
        # Check for negations
        negation_count = sum(1 for word in self.negation_words if word in text.lower())
        if negation_count > 0:
            context_score -= 0.1 * negation_count
        
        # Check for intensifiers
        intensifier_count = sum(1 for word in self.intensifiers if word in text.lower())
        if intensifier_count > 0:
            context_score += 0.05 * intensifier_count
        
        # Check for diminishers
        diminisher_count = sum(1 for word in self.diminishers if word in text.lower())
        if diminisher_count > 0:
            context_score -= 0.03 * diminisher_count
        
        # Apply market context if available
        if market_context:
            context_score += self._apply_market_context(text, market_context)
        
        return np.clip(context_score, -0.5, 0.5)
    
    def _apply_market_context(self, text: str, market_context: Dict[str, Any]) -> float:
        """Apply market-specific context adjustments"""
        
        adjustment = 0.0
        
        # Market trend context
        if 'trend' in market_context:
            trend = market_context['trend']
            if trend == 'bullish' and 'bullish' in text.lower():
                adjustment += 0.1
            elif trend == 'bearish' and 'bearish' in text.lower():
                adjustment += 0.1
            elif trend == 'bullish' and 'bearish' in text.lower():
                adjustment -= 0.1
            elif trend == 'bearish' and 'bullish' in text.lower():
                adjustment -= 0.1
        
        # Volatility context
        if 'volatility' in market_context:
            volatility = market_context['volatility']
            if volatility == 'high' and any(word in text.lower() for word in ['volatile', 'unstable', 'erratic']):
                adjustment += 0.05
        
        return adjustment

# Example usage and testing
if __name__ == "__main__":
    """Test the LLM Sentiment Engine"""
    
    logging.basicConfig(level=logging.INFO)
    
    print("🧪 Testing LLM Sentiment Engine v3.0...")
    
    # Create sentiment engine
    engine = AdvancedLLMSentimentEngine(confidence_threshold=0.6)
    
    # Test texts
    test_texts = [
        {
            'text': "Bitcoin is showing strong bullish momentum and could break through resistance levels. The market sentiment is extremely positive with major institutions buying.",
            'source': 'news_article'
        },
        {
            'text': "Major crash incoming! Everyone is selling and the market is in complete panic. This looks like a total disaster for crypto.",
            'source': 'social_tweet'
        },
        {
            'text': "The market is consolidating and showing mixed signals. Some analysts are bullish while others remain bearish. It's unclear which direction we'll go.",
            'source': 'forum_post'
        },
        {
            'text': "BREAKING: Major whale just moved 10,000 BTC to exchange! This could signal an incoming dump. Be careful and consider taking profits.",
            'source': 'telegram_message'
        },
        {
            'text': "Ethereum is mooning! Rocket emojis everywhere! Diamond hands are winning! This is just the beginning of the next bull run! 🚀🚀🚀",
            'source': 'social_reddit'
        }
    ]
    
    print("\n📝 Analyzing test texts...")
    
    # Analyze each text
    signals = []
    for i, test_data in enumerate(test_texts):
        signal = engine.analyze_text_sentiment(
            test_data['text'], 
            test_data['source']
        )
        signals.append(signal)
        
        print(f"\n--- Text {i+1} ---")
        print(f"Source: {signal.source}")
        print(f"Sentiment: {signal.sentiment_score:.3f}")
        print(f"Confidence: {signal.confidence:.3f}")
        print(f"Keywords: {', '.join(signal.keywords[:5])}")
        print(f"Snippet: {signal.text_snippet[:100]}...")
    
    # Test multiple source aggregation
    print("\n📊 Aggregating multiple sources...")
    
    aggregated = engine.analyze_multiple_sources(test_texts)
    
    print(f"Overall sentiment: {aggregated['overall_sentiment']:.3f}")
    print(f"Confidence: {aggregated['confidence']:.3f}")
    print(f"Dominant sentiment: {aggregated['dominant_sentiment']}")
    print(f"Positive signals: {aggregated['positive_signals']}")
    print(f"Negative signals: {aggregated['negative_signals']}")
    print(f"Neutral signals: {aggregated['neutral_signals']}")
    
    # Test sentiment trend
    print("\n📈 Checking sentiment trend...")
    
    trend = engine.get_sentiment_trend(timeframe=timedelta(hours=1))
    print(f"Trend: {trend['trend']}")
    print(f"Average sentiment: {trend['average_sentiment']:.3f}")
    print(f"Signals count: {trend['signals_count']}")
    
    print("\n✅ LLM Sentiment Engine v3.0 test completed!")