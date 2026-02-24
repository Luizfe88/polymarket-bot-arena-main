#!/usr/bin/env python3
"""
Polymarket Bot Arena v3.0 Integration Module

This module provides comprehensive integration of all v3.0 components:
- Advanced edge models
- Professional execution engine
- Enhanced evolution system
- Professional backtesting
- Risk management
- Market data validation
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Type
from datetime import datetime, timedelta, timezone
import pandas as pd
from dataclasses import dataclass
from enum import Enum

# Import all v3.0 components
from advanced_edge_models import DynamicSignalEnsemble, EdgeSignal, create_advanced_edge_ensemble
from execution_engine import ExecutionEngine, CostBreakdown
from enhanced_bot_evolution_manager import EnhancedBotEvolutionManager
from professional_backtester import ProfessionalBacktester, BacktestResult
from bayesian_updater import AdaptiveBayesianUpdater
from llm_sentiment_engine import AdvancedLLMSentimentEngine
from bots.base_bot import BaseBot
import config
from market_discovery_v2 import load_scraped_markets, filter_markets, calculate_spread

logger = logging.getLogger(__name__)

class SignalType(Enum):
    """Types of trading signals"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

@dataclass
class MarketOpportunity:
    """Represents a market opportunity"""
    market_id: str
    market_name: str
    current_price: float
    signal: SignalType
    confidence: float
    expected_value: float
    size: int
    reasoning: str
    edge_models_used: List[str]
    risk_score: float
    execution_costs: Dict[str, float]

class PolymarketBotArenaV3:
    """
    Main v3.0 integration class that orchestrates all components
    """
    
    def __init__(self, config: dict = None):
        self.config = config or self._get_default_config()
        self.v3_config = self.config.get('v3_0_parameters', {})
        
        # Initialize all components
        self._initialize_components()
        
    def _get_default_config(self):
        """Get default v3.0 configuration"""
        return {
            'v3_0_parameters': {
                'market_discovery': {
                    'min_volume': config.MIN_MARKET_VOLUME,
                    'max_spread': config.MAX_MARKET_SPREAD,
                    'min_time_to_resolution': config.MIN_TIME_TO_RESOLUTION,
                    'max_time_to_resolution': config.MAX_TIME_TO_RESOLUTION,
                    'priority_categories': config.PRIORITY_CATEGORIES,
                },
                'execution': {
                    'min_ev_after_costs': 0.02,
                    'max_order_size': config.EXECUTION_MAX_ORDER_SIZE,
                    'default_order_type': config.EXECUTION_DEFAULT_ORDER_TYPE,
                    'taker_fee_rate': config.EXECUTION_TAKER_FEE_RATE,
                    'maker_fee_rate': config.EXECUTION_MAKER_FEE_RATE,
                    'gas_cost_per_trade': config.EXECUTION_GAS_COST_PER_TRADE,
                },
                'evolution': {
                    'min_resolved_trades': config.EVOLUTION_MIN_RESOLVED_TRADES,
                    'target_resolved_trades': config.EVOLUTION_TARGET_RESOLVED_TRADES,
                    'sharpe_kill_threshold': config.EVOLUTION_SHARPE_KILL_THRESHOLD,
                    'walk_forward_days': config.EVOLUTION_WALK_FORWARD_DAYS,
                    'population_size': config.EVOLUTION_POPULATION_SIZE,
                    'survivors_per_cycle': config.EVOLUTION_SURVIVORS_PER_CYCLE,
                },
                'daily': {
                    'max_daily_trades': 10,
                    'max_exposure_per_category': 0.2,
                },
                'edge_models': {
                    'ensemble_confidence_threshold': 0.5,
                    'min_ensemble_models': 3,
                    'min_signal_confidence': 0.5,
                },
                'bayesian': {
                    'prior_probability': 0.5,
                    'learning_rate': 0.1,
                },
                'sentiment': {
                    'confidence_threshold': 0.6,
                },
                'market_selection': {
                    'min_volume_24h': 150000,
                    'max_spread': config.MAX_MARKET_SPREAD,
                    'min_liquidity': 50000,
                    'min_days_to_resolution': int(config.MIN_TIME_TO_RESOLUTION / 24),
                    'max_days_to_resolution': int(config.MAX_TIME_TO_RESOLUTION / 24),
                    'priority_categories': config.PRIORITY_CATEGORIES,
                },
                'risk': {
                    'exposure_limits': {
                        'max_position_size': 1000,
                        'max_correlated_exposure': 0.3,
                        'max_single_trade_risk': 0.4,
                        'max_category_exposure': 5000,
                        'max_total_exposure': 20000,
                    },
                    'category_risk_weights': {
                        'politics': 0.15,
                        'crypto': 0.20,
                        'sports': 0.10,
                        'macro': 0.12,
                        'tech': 0.12,
                        'other': 0.10
                    }
                }
            }
        }
        
    def _create_signal_ensemble(self):
        """Create the signal ensemble with all edge models"""
        ensemble = create_advanced_edge_ensemble()
        # Apply configured ensemble confidence threshold
        ensemble.ensemble_confidence = self.v3_config['edge_models']['ensemble_confidence_threshold']
        return ensemble
        
    def _initialize_components(self):
        """Initialize all v3.0 components"""
        # Initialize core components
        self.execution_engine = ExecutionEngine()
        self.evolution_manager = EnhancedBotEvolutionManager()
        self.backtester = ProfessionalBacktester()
        
        # Initialize edge models
        self.signal_ensemble = self._create_signal_ensemble()
        
        # Initialize specialized engines
        self.bayesian_updater = AdaptiveBayesianUpdater(
            prior_probability=self.v3_config['bayesian']['prior_probability'],
            learning_rate=self.v3_config['bayesian']['learning_rate']
        )
        
        self.sentiment_engine = AdvancedLLMSentimentEngine(
            confidence_threshold=self.v3_config['sentiment']['confidence_threshold']
        )
        
        # Market validation
        self.market_validator = MarketValidator(self.config)
        
        # Risk management
        self.risk_manager = RiskManager(self.config)
        
        # Performance tracking
        self.performance_tracker = PerformanceTracker()
        
        logger.info("Polymarket Bot Arena v3.0 initialized successfully")
    
    async def scan_markets(self) -> List[MarketOpportunity]:
        """
        Scan markets for profitable opportunities using v3.0 criteria
        """
        
        logger.info("Scanning markets for v3.0 opportunities...")
        
        # Get high-quality markets
        markets = await self._get_high_quality_markets()
        opportunities = []
        
        for market in markets:
            try:
                # Validate market meets v3.0 criteria
                if not await self.market_validator.validate_market(market):
                    continue
                
                # Analyze market using edge models
                signal = await self._analyze_market_with_edge_models(market)
                
                if signal and signal.confidence >= self.v3_config['edge_models']['min_signal_confidence']:
                    # Calculate execution costs
                    side = signal.type
                    price = self.execution_engine.calculate_optimal_order_price(
                        market_data=market, side=side, size=signal.size
                    )
                    cost_breakdown = self.execution_engine.calculate_total_cost(
                        size=signal.size,
                        price=price,
                        order_type=self.execution_engine.config.order_type,
                        market_data=market
                    )
                    
                    # Calculate expected value after costs
                    net_ev = signal.expected_value - cost_breakdown.total_cost_pct
                    
                    # Check if meets minimum EV threshold
                    if net_ev >= self.v3_config['execution']['min_ev_after_costs']:
                        # Calculate risk score
                        risk_score = await self.risk_manager.calculate_risk_score(market, signal)
                        
                        # Create opportunity
                        opportunity = MarketOpportunity(
                            market_id=market['market_id'],
                            market_name=market['market_name'],
                            current_price=market['current_price'],
                            signal=SignalType(signal.type),
                            confidence=signal.confidence,
                            expected_value=net_ev,
                            size=signal.size,
                            reasoning=signal.reasoning,
                            edge_models_used=[s.get('model') for s in signal.metadata.get('individual_signals', [])],
                            risk_score=risk_score,
                            execution_costs={
                                'spread_cost': cost_breakdown.spread_cost,
                                'taker_fee': cost_breakdown.taker_fee,
                                'maker_fee': cost_breakdown.maker_fee,
                                'gas_cost': cost_breakdown.gas_cost,
                                'slippage_cost': cost_breakdown.slippage_cost,
                                'total_cost': cost_breakdown.total_cost,
                                'total_cost_pct': cost_breakdown.total_cost_pct
                            }
                        )
                        
                        opportunities.append(opportunity)
                        
                        logger.info(f"Found opportunity: {market['market_name']} "
                                  f"({signal.type}, confidence: {signal.confidence:.3f}, "
                                  f"EV: {net_ev:.3f})")
            
            except Exception as e:
                logger.error(f"Error analyzing market {market.get('market_id', 'unknown')}: {e}")
                continue
        
        # Sort by expected value
        opportunities.sort(key=lambda x: x.expected_value, reverse=True)
        
        logger.info(f"Found {len(opportunities)} profitable opportunities")
        return opportunities
    
    async def _get_high_quality_markets(self) -> List[Dict[str, Any]]:
        """Get markets that meet v3.0 quality criteria using scraped data"""
        try:
            scraped = load_scraped_markets()
            if not scraped:
                return []
            
            qualified = filter_markets(scraped)
            markets: List[Dict[str, Any]] = []
            
            for m in qualified:
                # Normalize schema
                question = m.get('question', '')
                volume = float(m.get('volume', 0))
                category = m.get('category', 'unknown').lower()
                end_date_str = m.get('endDate', '')
                current_price = float(m.get('current_price', m.get('price', 0.5)) or 0.5)
                spread_pct = calculate_spread(m)
                
                # Parse resolution date
                resolution_dt = None
                if end_date_str:
                    try:
                        # ISO with Z
                        resolution_dt = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                    except Exception:
                        resolution_dt = datetime.now() + timedelta(days=30)
                else:
                    resolution_dt = datetime.now() + timedelta(days=30)
                
                markets.append({
                    'market_id': m.get('id') or m.get('market_id') or question[:24],
                    'market_name': question,
                    'current_price': current_price,
                    'volume_24h': volume,
                    'spread': spread_pct,
                    'resolution_date': resolution_dt,
                    'category': category,
                    'liquidity': float(m.get('liquidity', volume))  # fallback to volume
                })
            
            return markets
        except Exception as e:
            logger.error(f"Failed to discover markets: {e}")
            return []
    
    async def _analyze_market_with_edge_models(self, market: Dict[str, Any]) -> Optional[EdgeSignal]:
        """Analyze market using all available edge models"""
        
        try:
            # Get market data
            market_data = await self._get_market_data(market['market_id'])
            
            if market_data is None or len(market_data) < 50:
                return None
            
            # Train ensemble models on recent data (baseline training)
            try:
                self.signal_ensemble.train_all_models(market_data)
            except Exception:
                pass
            
            # Generate ensemble signal
            additional_data = {
                'AdvancedLLMSentimentEngine': {
                    'news_data': [
                        {'text': 'Positive momentum and strong fundamentals', 'timestamp': datetime.now()},
                        {'text': 'Institutional interest rising', 'timestamp': datetime.now()}
                    ],
                    'social_data': [
                        {'text': 'Bullish setup', 'likes': 200, 'comments': 40, 'sentiment': 0.8},
                        {'text': 'Strong buy signals', 'likes': 150, 'comments': 30, 'sentiment': 0.7}
                    ]
                },
                'BayesianProbabilityUpdater': {
                    'external_data': {
                        'news_sentiment': 0.6,
                        'event_impact': 0.5
                    }
                }
            }
            
            signal = self.signal_ensemble.generate_ensemble_signal(
                market_data=market_data,
                **additional_data
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Error analyzing market with edge models: {e}")
            return None
    
    async def _get_market_data(self, market_id: str) -> Optional[pd.DataFrame]:
        """Get historical market data for analysis"""
        
        # This would typically fetch from Polymarket API
        # For now, generate mock data
        import numpy as np
        
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), 
                            periods=720, freq='h')
        
        # Generate realistic price data
        prices = 0.5 + np.cumsum(np.random.normal(0, 0.001, 720)) + \
                np.sin(np.arange(720) * 0.05) * 0.1
        
        volumes = np.random.lognormal(10, 1, 720)
        spreads = np.random.exponential(0.005, 720)
        
        market_data = pd.DataFrame({
            'timestamp': dates,
            'price': prices,
            'volume': volumes,
            'spread': spreads
        })
        
        return market_data
    
    async def execute_opportunity(self, opportunity: MarketOpportunity) -> Dict[str, Any]:
        """
        Execute a market opportunity using professional execution
        """
        
        logger.info(f"Executing opportunity: {opportunity.market_name}")
        
        try:
            # Determine execution strategy based on opportunity size and urgency
            strategy = self._determine_execution_strategy(opportunity)
            
            # Execute with professional execution engine
            result = await self.execution_engine.execute_professional_order(
                market_id=opportunity.market_id,
                signal_type=opportunity.signal.value,
                size=opportunity.size,
                expected_value=opportunity.expected_value,
                confidence=opportunity.confidence,
                strategy=strategy,
                max_cost_percentage=opportunity.execution_costs['total_cost_percentage']
            )
            
            # Track performance
            self.performance_tracker.record_execution(opportunity, result)
            
            # Extract cost info for logging
            cost_info = result.get("cost_breakdown", {})
            logger.info(f"Execution completed: {result.get('status', 'unknown')} "
                       f"(actual cost: {cost_info.get('total_cost_pct', 0):.2f}%)")
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing opportunity: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "failed",
                "actual_cost_percentage": 0,
                "execution_time": 0
            }
    
    def _determine_execution_strategy(self, opportunity: MarketOpportunity) -> str:
        """Determine optimal execution strategy based on opportunity characteristics"""
        
        # Large opportunities get TWAP/iceberg
        if opportunity.size > self.v3_config['execution']['large_order_threshold']:
            return "twap"
        
        # High confidence opportunities get immediate execution
        if opportunity.confidence > 0.85:
            return "immediate"
        
        # Medium size opportunities get standard limit orders
        return "limit"
    
    async def run_evolution_cycle(self):
        """
        Run enhanced evolution cycle with walk-forward optimization
        """
        
        logger.info("Running v3.0 evolution cycle...")
        
        try:
            # Get recent performance data
            performance_data = self.performance_tracker.get_performance_data(
                days=self.v3_config['evolution']['performance_lookback_days']
            )
            
            if len(performance_data) < self.v3_config['evolution']['min_trades_for_evolution']:
                logger.warning("Insufficient trades for evolution cycle")
                return
            
            # Run walk-forward optimization
            evolution_result = await self.evolution_manager.run_walk_forward_optimization(
                performance_data=performance_data,
                window_days=self.v3_config['evolution']['walk_forward_window_days'],
                step_days=self.v3_config['evolution']['walk_forward_step_days']
            )
            
            if evolution_result.success:
                logger.info(f"Evolution cycle completed: {evolution_result.improvement:.2f}% improvement")
                
                # Apply improvements to bots
                await self._apply_evolution_improvements(evolution_result)
            else:
                logger.warning("Evolution cycle did not produce improvements")
            
        except Exception as e:
            logger.error(f"Error in evolution cycle: {e}")
    
    async def _apply_evolution_improvements(self, evolution_result):
        """Apply evolution improvements to active bots"""
        
        # This would update bot parameters based on evolution results
        logger.info("Applying evolution improvements to bots...")
        
        # Update signal ensemble weights
        if hasattr(evolution_result, 'ensemble_weights'):
            self.signal_ensemble.update_model_weights(evolution_result.ensemble_weights)
        
        # Update execution parameters
        if hasattr(evolution_result, 'execution_params'):
            self.execution_engine.update_parameters(evolution_result.execution_params)
        
        logger.info("Evolution improvements applied successfully")
    
    async def run_backtest(self, market_id: str, start_date: datetime, end_date: datetime) -> BacktestResult:
        """
        Run professional backtest on a market
        """
        
        logger.info(f"Running backtest for {market_id} from {start_date} to {end_date}")
        
        try:
            # Get historical data
            historical_data = await self._get_historical_data(market_id, start_date, end_date)
            
            if historical_data is None or len(historical_data) < 100:
                logger.error("Insufficient historical data for backtest")
                return None
            
            # Run backtest
            result = await self.backtester.run_walk_forward_test(
                market_data=historical_data,
                bot=self.signal_ensemble,
                start_date=start_date,
                end_date=end_date
            )
            
            logger.info(f"Backtest completed: Sharpe {result.sharpe_ratio:.3f}, "
                       f"Total Return {result.total_return:.2f}%")
            
            return result
            
        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            return None
    
    async def _get_historical_data(self, market_id: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """Get historical market data for backtesting"""
        
        # This would typically fetch from Polymarket API
        # For now, generate mock data
        import numpy as np
        
        total_hours = int((end_date - start_date).total_seconds() / 3600)
        
        if total_hours < 24:
            return None
        
        dates = pd.date_range(start=start_date, end=end_date, freq='h')
        
        # Generate realistic price data with trends and volatility
        prices = 0.5 + np.cumsum(np.random.normal(0, 0.001, len(dates))) + \
                np.sin(np.arange(len(dates)) * 0.01) * 0.15 + \
                np.random.normal(0, 0.05, len(dates))  # Add noise
        
        volumes = np.random.lognormal(10, 1, len(dates))
        spreads = np.random.exponential(0.005, len(dates))
        
        historical_data = pd.DataFrame({
            'timestamp': dates,
            'price': np.clip(prices, 0.01, 0.99),
            'volume': volumes,
            'spread': spreads
        })
        
        return historical_data
    
    async def run_daily_operations(self):
        """
        Run daily operations: market scanning, execution, and reporting
        """
        
        logger.info("Starting daily v3.0 operations...")
        
        try:
            # 1. Scan for opportunities
            opportunities = await self.scan_markets()
            
            # 2. Execute top opportunities
            executed_count = 0
            for opportunity in opportunities[:self.v3_config['daily']['max_daily_trades']]:
                if self.risk_manager.can_execute_trade(opportunity):
                    result = await self.execute_opportunity(opportunity)
                    if result.success:
                        executed_count += 1
                else:
                    logger.warning(f"Risk limits prevent execution of {opportunity.market_name}")
            
            # 3. Run evolution cycle if conditions met
            if self.performance_tracker.get_trade_count() >= self.v3_config['evolution']['min_trades_for_evolution']:
                await self.run_evolution_cycle()
            
            # 4. Generate daily report
            report = self._generate_daily_report(opportunities, executed_count)
            
            logger.info(f"Daily operations completed: {executed_count} trades executed, "
                       f"{len(opportunities)} opportunities found")
            
            return report
            
        except Exception as e:
            logger.error(f"Error in daily operations: {e}")
            return None
    
    def _generate_daily_report(self, opportunities: List[MarketOpportunity], executed_count: int) -> Dict[str, Any]:
        """Generate daily operations report"""
        
        total_opportunities = len(opportunities)
        avg_expected_value = sum(op.expected_value for op in opportunities) / total_opportunities if opportunities else 0
        avg_confidence = sum(op.confidence for op in opportunities) / total_opportunities if opportunities else 0
        
        performance_summary = self.performance_tracker.get_daily_summary()
        
        report = {
            'date': datetime.now().date(),
            'opportunities_found': total_opportunities,
            'trades_executed': executed_count,
            'execution_rate': executed_count / total_opportunities if total_opportunities > 0 else 0,
            'average_expected_value': avg_expected_value,
            'average_confidence': avg_confidence,
            'performance_summary': performance_summary,
            'risk_metrics': self.risk_manager.get_current_metrics(),
            'edge_model_usage': self._get_edge_model_usage(opportunities)
        }
        
        return report
    
    def _get_edge_model_usage(self, opportunities: List[MarketOpportunity]) -> Dict[str, int]:
        """Get usage statistics for edge models"""
        
        usage = {}
        for opportunity in opportunities:
            for model in opportunity.edge_models_used:
                usage[model] = usage.get(model, 0) + 1
        
        return usage

class MarketValidator:
    """Validates markets against v3.0 quality criteria"""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.v3_config = self.config.get('v3_0_parameters', {})
    
    async def validate_market(self, market: Dict[str, Any]) -> bool:
        """Validate market meets v3.0 criteria"""
        
        # Volume check
        if market.get('volume_24h', 0) < self.v3_config['market_selection']['min_volume_24h']:
            return False
        
        # Spread check
        if market.get('spread', 1.0) > self.v3_config['market_selection']['max_spread']:
            return False
        
        # Resolution time check
        resolution_date = market.get('resolution_date')
        if resolution_date:
            now_dt = datetime.now(resolution_date.tzinfo) if getattr(resolution_date, 'tzinfo', None) else datetime.now(timezone.utc)
            days_to_resolution = (resolution_date - now_dt).days
            if days_to_resolution < self.v3_config['market_selection']['min_days_to_resolution']:
                return False
            if days_to_resolution > self.v3_config['market_selection']['max_days_to_resolution']:
                return False
        
        # Category check
        allowed_categories = self.v3_config['market_selection']['priority_categories']
        if market.get('category') not in allowed_categories:
            return False
        
        # Liquidity check
        if market.get('liquidity', 0) < self.v3_config['market_selection']['min_liquidity']:
            return False
        
        return True

class RiskManager:
    """Advanced risk management for v3.0"""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.v3_config = self.config.get('v3_0_parameters', {})
        self.exposure_limits = self.v3_config['risk']['exposure_limits']
        self.current_exposure = {}
    
    async def calculate_risk_score(self, market: Dict[str, Any], signal: EdgeSignal) -> float:
        """Calculate risk score for a market opportunity"""
        
        # Base risk from signal confidence
        base_risk = 1.0 - signal.confidence
        
        # Market-specific risk factors
        market_risk = 0.0
        
        # Volatility risk
        if 'volatility' in market:
            market_risk += min(0.3, market['volatility'] * 0.5)
        
        # Liquidity risk
        if 'liquidity' in market:
            liquidity_risk = max(0, 1.0 - (market['liquidity'] / 1000000))  # Normalize to $1M
            market_risk += liquidity_risk * 0.2
        
        # Time to resolution risk
        if 'resolution_date' in market:
            res_dt = market['resolution_date']
            now_dt = datetime.now(res_dt.tzinfo) if getattr(res_dt, 'tzinfo', None) else datetime.now(timezone.utc)
            days_to_resolution = (res_dt - now_dt).days
            if days_to_resolution < 7:  # Less than a week
                market_risk += 0.2
            elif days_to_resolution < 30:  # Less than a month
                market_risk += 0.1
        
        # Category risk
        category_risk = self.v3_config['risk']['category_risk_weights'].get(market.get('category', 'other'), 0.1)
        market_risk += category_risk
        
        # Total risk score
        total_risk = base_risk + market_risk
        
        return min(1.0, total_risk)
    
    def can_execute_trade(self, opportunity: MarketOpportunity) -> bool:
        """Check if trade can be executed within risk limits"""
        
        # Check individual trade risk
        if opportunity.risk_score > self.exposure_limits['max_single_trade_risk']:
            return False
        
        # Check category exposure
        category = opportunity.market_name.split()[0].lower()  # Simple category extraction
        current_category_exposure = self.current_exposure.get(category, 0)
        max_category_exposure = self.exposure_limits['max_category_exposure']
        
        if current_category_exposure + opportunity.size > max_category_exposure:
            return False
        
        # Check total exposure
        total_exposure = sum(self.current_exposure.values())
        max_total_exposure = self.exposure_limits['max_total_exposure']
        
        if total_exposure + opportunity.size > max_total_exposure:
            return False
        
        return True
    
    def record_trade(self, opportunity: MarketOpportunity):
        """Record executed trade for exposure tracking"""
        
        category = opportunity.market_name.split()[0].lower()
        self.current_exposure[category] = self.current_exposure.get(category, 0) + opportunity.size
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current risk metrics"""
        
        total_exposure = sum(self.current_exposure.values())
        
        return {
            'total_exposure': total_exposure,
            'category_exposure': self.current_exposure.copy(),
            'exposure_utilization': total_exposure / self.exposure_limits['max_total_exposure'],
            'risk_limits': self.exposure_limits
        }

class PerformanceTracker:
    """Tracks performance of v3.0 operations"""
    
    def __init__(self):
        self.executions = []
        self.daily_summaries = []
        self.max_history = 1000
    
    def record_execution(self, opportunity: MarketOpportunity, result: Dict[str, Any]):
        """Record trade execution"""
        
        execution = {
            'timestamp': datetime.now(),
            'market_id': opportunity.market_id,
            'market_name': opportunity.market_name,
            'signal_type': opportunity.signal.value,
            'size': opportunity.size,
            'expected_value': opportunity.expected_value,
            'confidence': opportunity.confidence,
            'risk_score': opportunity.risk_score,
            'actual_cost_percentage': result.actual_cost_percentage,
            'execution_time': result.execution_time,
            'success': result.success
        }
        
        self.executions.append(execution)
        
        # Keep only recent history
        if len(self.executions) > self.max_history:
            self.executions = self.executions[-self.max_history:]
    
    def get_performance_data(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get performance data for specified number of days"""
        
        cutoff_date = datetime.now() - timedelta(days=days)
        return [exec for exec in self.executions if exec['timestamp'] >= cutoff_date]
    
    def get_trade_count(self) -> int:
        """Get total number of recorded trades"""
        return len(self.executions)
    
    def get_daily_summary(self) -> Dict[str, Any]:
        """Get daily performance summary"""
        
        today = datetime.now().date()
        today_executions = [exec for exec in self.executions 
                          if exec['timestamp'].date() == today]
        
        if not today_executions:
            return {
                'trades_today': 0,
                'avg_expected_value': 0,
                'avg_confidence': 0,
                'avg_actual_cost': 0,
                'success_rate': 0
            }
        
        return {
            'trades_today': len(today_executions),
            'avg_expected_value': sum(exec['expected_value'] for exec in today_executions) / len(today_executions),
            'avg_confidence': sum(exec['confidence'] for exec in today_executions) / len(today_executions),
            'avg_actual_cost': sum(exec['actual_cost_percentage'] for exec in today_executions) / len(today_executions),
            'success_rate': sum(1 for exec in today_executions if exec['success']) / len(today_executions)
        }

# Example usage and testing
if __name__ == "__main__":
    """Test the v3.0 integration"""
    
    logging.basicConfig(level=logging.INFO)
    
    print("🚀 Testing Polymarket Bot Arena v3.0 Integration...")
    
    # Initialize v3.0 system
    arena = PolymarketBotArenaV3()
    
    # Test market scanning
    print("\n🔍 Testing market scanning...")
    
    async def test_scanning():
        opportunities = await arena.scan_markets()
        print(f"Found {len(opportunities)} opportunities")
        
        if opportunities:
            print(f"Best opportunity: {opportunities[0].market_name}")
            print(f"  Signal: {opportunities[0].signal.value}")
            print(f"  Confidence: {opportunities[0].confidence:.3f}")
            print(f"  Expected Value: {opportunities[0].expected_value:.3f}")
            print(f"  Risk Score: {opportunities[0].risk_score:.3f}")
    
    # Run test
    asyncio.run(test_scanning())
    
    print("\n✅ v3.0 Integration test completed!")
