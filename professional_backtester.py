#!/usr/bin/env python3
"""
Professional Backtester v3.0 for Polymarket Bot Arena

Features:
- 12+ months of historical data
- Walk-forward validation
- Realistic execution modeling
- Advanced performance metrics
- Regime detection
- Correlation analysis
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import sqlite3
import json
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class BacktestMode(Enum):
    WALK_FORWARD = "walk_forward"
    EXPANDING_WINDOW = "expanding_window"
    FIXED_WINDOW = "fixed_window"
    STRICT_SPLIT = "strict_split"  # Train/Val/Test split

@dataclass
class BacktestConfig:
    """Configuration for professional backtesting"""
    mode: BacktestMode = BacktestMode.WALK_FORWARD
    train_window_days: int = 30  # Training window size
    test_window_days: int = 7    # Test window size
    step_days: int = 3           # Step size for walk-forward
    min_trades: int = 20         # Minimum trades for statistical significance
    confidence_threshold: float = 0.6  # Minimum confidence for trades
    max_correlation: float = 0.7     # Maximum correlation between strategies
    regime_detection: bool = True      # Enable regime detection
    execution_modeling: bool = True  # Model execution costs and slippage
    # Strict split ratios (e.g. 8 months train, 2 val, 2 test -> 0.67, 0.17, 0.16)
    split_ratios: Tuple[float, float, float] = (0.66, 0.17, 0.17)

@dataclass
class BacktestResult:
    """Results from a backtest run"""
    total_trades: int
    win_rate: float
    total_pnl: float
    avg_trade_pnl: float
    sharpe_ratio: float
    calmar_ratio: float
    profit_factor: float
    max_drawdown: float
    max_drawdown_duration: int
    volatility: float
    skewness: float
    kurtosis: float
    var_95: float  # Value at Risk (95%)
    cvar_95: float  # Conditional VaR (95%)
    regime_performance: Dict[str, float]  # Performance by market regime
    correlation_matrix: Optional[np.ndarray]  # Strategy correlations
    execution_costs: float  # Total execution costs
    slippage_impact: float  # Slippage impact
    
@dataclass
class MarketRegime:
    """Market regime classification"""
    name: str
    start_date: datetime
    end_date: datetime
    volatility: float
    volume: float
    trend: str  # "bull", "bear", "sideways"
    liquidity: float

class ProfessionalBacktester:
    """Professional backtester with walk-forward validation and regime detection"""
    
    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()
        self.historical_data = {}
        self.regimes = []
        
    def load_historical_data(self, market_id: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Load historical market data for backtesting
        
        Args:
            market_id: Market identifier
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame with historical price data
        """
        # This would connect to a historical data source
        # For now, we'll simulate the structure
        logger.info(f"Loading historical data for {market_id} from {start_date} to {end_date}")
        
        # Simulate 12+ months of data
        date_range = pd.date_range(start=start_date, end=end_date, freq='h')
        
        # Generate realistic price data
        np.random.seed(42)  # For reproducibility
        
        # Base price with trend and volatility
        base_price = 0.5
        returns = np.random.normal(0, 0.02, len(date_range))  # 2% daily volatility
        prices = [base_price]
        
        for i in range(1, len(returns)):
            new_price = prices[-1] * (1 + returns[i])
            # Keep price within reasonable bounds
            new_price = max(0.01, min(0.99, new_price))
            prices.append(new_price)
        
        df = pd.DataFrame({
            'timestamp': date_range,
            'price': prices,
            'volume': np.random.lognormal(10, 1, len(date_range)),  # Log-normal volume
            'spread': np.random.uniform(0.001, 0.01, len(date_range)),  # Bid-ask spread
        })
        
        self.historical_data[market_id] = df
        return df
    
    def detect_market_regimes(self, price_data: pd.DataFrame) -> List[MarketRegime]:
        """
        Detect market regimes using volatility and trend analysis
        
        Args:
            price_data: Historical price data
            
        Returns:
            List of market regimes
        """
        if not self.config.regime_detection:
            return []
        
        # Calculate rolling volatility
        price_data['returns'] = price_data['price'].pct_change()
        price_data['volatility'] = price_data['returns'].rolling(window=24).std() * np.sqrt(24)  # 24h volatility
        
        # Calculate trend using moving averages
        price_data['ma_short'] = price_data['price'].rolling(window=24).mean()
        price_data['ma_long'] = price_data['price'].rolling(window=168).mean()  # 7-day MA
        price_data['trend'] = np.where(price_data['ma_short'] > price_data['ma_long'], 'bull', 'bear')
        
        # Regime detection logic
        regimes = []
        current_regime = None
        
        for i, row in price_data.iterrows():
            volatility = row['volatility']
            trend = row['trend']
            
            # Classify regime based on volatility and trend
            if pd.isna(volatility):
                continue
                
            if volatility < 0.01:  # Low volatility
                regime_name = f"low_vol_{trend}"
            elif volatility < 0.02:  # Medium volatility
                regime_name = f"med_vol_{trend}"
            else:  # High volatility
                regime_name = f"high_vol_{trend}"
            
            if current_regime != regime_name:
                if current_regime is not None:
                    # End previous regime
                    regimes[-1].end_date = row['timestamp']
                
                # Start new regime
                regimes.append(MarketRegime(
                    name=regime_name,
                    start_date=row['timestamp'],
                    end_date=row['timestamp'],
                    volatility=volatility,
                    volume=row['volume'],
                    trend=trend,
                    liquidity=1.0 / row['spread'] if row['spread'] > 0 else 1000
                ))
                current_regime = regime_name
        
        # Set end date for last regime
        if regimes:
            regimes[-1].end_date = price_data['timestamp'].iloc[-1]
        
        self.regimes = regimes
        logger.info(f"Detected {len(regimes)} market regimes")
        return regimes

    def check_data_leakage(self, train_data: pd.DataFrame, test_data: pd.DataFrame) -> bool:
        """
        Verify no data leakage between train and test sets.
        Returns True if safe, raises ValueError if leakage detected.
        """
        train_max = train_data['timestamp'].max()
        test_min = test_data['timestamp'].min()
        
        if train_max >= test_min:
            logger.error(f"🚨 DATA LEAKAGE DETECTED: Train ends {train_max} >= Test starts {test_min}")
            raise ValueError(f"Data leakage: Train set overlaps with Test set")
            
        logger.info(f"✅ Data integrity check passed: Train ends {train_max} < Test starts {test_min}")
        return True

    def run_strict_split_test(self, bot, market_data: pd.DataFrame) -> Dict[str, BacktestResult]:
        """
        Run strict temporal split backtest (Train -> Val -> Test)
        Test set is NEVER used for optimization.
        """
        # Sort by time just in case
        market_data = market_data.sort_values('timestamp')
        
        total_rows = len(market_data)
        ratios = self.config.split_ratios
        
        train_end_idx = int(total_rows * ratios[0])
        val_end_idx = int(total_rows * (ratios[0] + ratios[1]))
        
        train_data = market_data.iloc[:train_end_idx]
        val_data = market_data.iloc[train_end_idx:val_end_idx]
        test_data = market_data.iloc[val_end_idx:]
        
        # Verify integrity
        self.check_data_leakage(train_data, val_data)
        self.check_data_leakage(val_data, test_data)
        
        logger.info(f"Running Strict Split Backtest:")
        logger.info(f"  Train: {len(train_data)} rows ({train_data['timestamp'].min()} - {train_data['timestamp'].max()})")
        logger.info(f"  Val:   {len(val_data)} rows ({val_data['timestamp'].min()} - {val_data['timestamp'].max()})")
        logger.info(f"  Test:  {len(test_data)} rows ({test_data['timestamp'].min()} - {test_data['timestamp'].max()})")
        
        # Detect regimes
        regimes = self.detect_market_regimes(market_data)
        
        results = {}
        
        # 1. Train (Optimization would happen here)
        # For this simulation, we just run the bot to see baseline
        logger.info("Phase 1: Training (Baseline)")
        # train_res = self._simulate_bot_trading(bot, train_data, regimes) # Optional
        
        # 2. Validation (Hyperparameter tuning)
        logger.info("Phase 2: Validation")
        val_res = self._simulate_bot_trading(bot, val_data, regimes)
        results['validation'] = val_res
        
        # 3. Test (Final Evaluation - untouched until now)
        logger.info("Phase 3: Final Test (Hold-out)")
        test_res = self._simulate_bot_trading(bot, test_data, regimes)
        results['test'] = test_res
        
        if test_res:
            logger.info(f"🎯 FINAL TEST RESULT: Sharpe={test_res.sharpe_ratio:.2f}, Return={test_res.total_pnl:.2f}, Trades={test_res.total_trades}")
        else:
            logger.warning("⚠️ FINAL TEST: No trades executed or insufficient data")
            
        return results

    def calculate_execution_costs(self, trade_size: float, market_data: pd.Series) -> Dict[str, float]:
        """
        Calculate realistic execution costs including spread, slippage, and fees
        
        Args:
            trade_size: Size of the trade
            market_data: Market data at trade time
            
        Returns:
            Dictionary with cost breakdown
        """
        if not self.config.execution_modeling:
            return {'spread_cost': 0, 'slippage': 0, 'fees': 0, 'total': 0}
        
        # Spread cost (half of bid-ask spread)
        spread_cost = trade_size * market_data['spread'] * 0.5
        
        # Slippage (increases with trade size and market volatility)
        slippage_factor = min(0.01, trade_size * 0.001)  # 1% max slippage
        slippage = trade_size * slippage_factor
        
        # Trading fees (maker/taker)
        # Use post-only orders by default (maker rebate)
        maker_rebate = -0.0005  # 0.05% rebate
        taker_fee = 0.002  # 0.2% fee
        
        # Assume 80% of orders are maker (post-only)
        fee_rate = 0.8 * maker_rebate + 0.2 * taker_fee
        fees = trade_size * abs(fee_rate)
        
        total_cost = spread_cost + slippage + fees
        
        return {
            'spread_cost': spread_cost,
            'slippage': slippage,
            'fees': fees,
            'total': total_cost
        }
    
    def run_walk_forward_test(self, bot, market_data: pd.DataFrame) -> List[BacktestResult]:
        """
        Run walk-forward backtest on historical data
        
        Args:
            bot: Trading bot to test
            market_data: Historical market data
            
        Returns:
            List of backtest results for each window
        """
        results = []
        
        # Detect market regimes
        regimes = self.detect_market_regimes(market_data)
        
        # Calculate number of windows
        total_days = (market_data['timestamp'].max() - market_data['timestamp'].min()).days
        num_windows = (total_days - self.config.train_window_days) // self.config.step_days + 1
        
        logger.info(f"Running walk-forward test with {num_windows} windows")
        
        for window_idx in range(num_windows):
            # Calculate window dates
            start_offset = window_idx * self.config.step_days
            train_start = market_data['timestamp'].min() + timedelta(days=start_offset)
            train_end = train_start + timedelta(days=self.config.train_window_days)
            test_start = train_end
            test_end = test_start + timedelta(days=self.config.test_window_days)
            
            # Skip if we don't have enough data
            if test_end > market_data['timestamp'].max():
                break
            
            logger.info(f"Window {window_idx + 1}: Train {train_start.date()} to {train_end.date()}, "
                       f"Test {test_start.date()} to {test_end.date()}")
            
            # Get training and test data
            train_data = market_data[(market_data['timestamp'] >= train_start) & 
                                   (market_data['timestamp'] <= train_end)]
            test_data = market_data[(market_data['timestamp'] >= test_start) & 
                                  (market_data['timestamp'] <= test_end)]
            
            # Simulate bot trading on test data
            window_result = self._simulate_bot_trading(bot, test_data, regimes)
            
            if window_result and window_result.total_trades >= self.config.min_trades:
                results.append(window_result)
                logger.info(f"Window {window_idx + 1}: {window_result.total_trades} trades, "
                          f"Sharpe: {window_result.sharpe_ratio:.3f}, "
                          f"Win Rate: {window_result.win_rate:.3f}")
        
        return results
    
    def _simulate_bot_trading(self, bot, test_data: pd.DataFrame, regimes: List[MarketRegime]) -> Optional[BacktestResult]:
        """
        Simulate bot trading on test data
        
        Args:
            bot: Trading bot
            test_data: Test period data
            regimes: Market regimes
            
        Returns:
            Backtest result or None if insufficient trades
        """
        trades = []
        pnl_series = []
        regime_performance = {}
        
        # Simulate trading signals
        for i, row in test_data.iterrows():
            # Get bot signal (simplified simulation)
            # In reality, this would call bot.analyze_market()
            signal = self._simulate_bot_signal(bot, row, test_data.iloc[:i+1])
            
            if signal and signal['confidence'] >= self.config.confidence_threshold:
                # Calculate execution costs
                trade_size = signal['size']
                costs = self.calculate_execution_costs(trade_size, row)
                
                # Simulate trade outcome
                outcome = self._simulate_trade_outcome(signal, row, test_data.iloc[i+1:])
                
                if outcome:
                    # Apply costs to P&L
                    net_pnl = outcome['pnl'] - costs['total']
                    
                    trades.append({
                        'timestamp': row['timestamp'],
                        'size': trade_size,
                        'confidence': signal['confidence'],
                        'expected_value': signal['expected_value'],
                        'outcome': outcome['outcome'],
                        'pnl': net_pnl,
                        'costs': costs['total'],
                        'regime': self._get_regime_at_time(row['timestamp'], regimes)
                    })
        
        if len(trades) < self.config.min_trades:
            return None
        
        # Calculate performance metrics
        return self._calculate_backtest_metrics(trades, regimes)
    
    def _simulate_bot_signal(self, bot, market_data: pd.Series, historical_data: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Simulate bot trading signal
        
        Args:
            bot: Trading bot
            market_data: Current market data
            historical_data: Historical data up to current point
            
        Returns:
            Trading signal or None
        """
        # This is a simplified simulation
        # In reality, this would use the actual bot's analysis logic
        
        # Simulate based on momentum and mean reversion
        price = market_data['price']
        volatility = market_data.get('volatility', 0.02)
        
        # Generate signal based on price action
        if len(historical_data) < 24:
            return None
        
        recent_prices = historical_data['price'].tail(24)
        momentum = (price - recent_prices.mean()) / recent_prices.std()
        
        # Simulate confidence based on signal strength and volatility
        if abs(momentum) > 1.0:  # Strong signal
            confidence = min(0.9, abs(momentum) * 0.3)
            expected_value = momentum * 0.05  # 5% expected return per unit of momentum
            
            return {
                'type': 'buy' if momentum > 0 else 'sell',
                'size': 100,  # Fixed size for simulation
                'confidence': confidence,
                'expected_value': expected_value
            }
        
        return None
    
    def _simulate_trade_outcome(self, signal: Dict[str, Any], entry_data: pd.Series, 
                               future_data: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Simulate trade outcome based on signal and future price action
        
        Args:
            signal: Trading signal
            entry_data: Entry market data
            future_data: Future price data
            
        Returns:
            Trade outcome or None
        """
        if len(future_data) < 24:  # Need at least 24 hours of future data
            return None
        
        # Simulate holding period (1-7 days)
        holding_period = np.random.randint(24, 168)  # 1-7 days in hours
        if len(future_data) < holding_period:
            holding_period = len(future_data)
        
        # Get exit price
        exit_price = future_data.iloc[holding_period-1]['price']
        entry_price = entry_data['price']
        
        # Calculate P&L
        if signal['type'] == 'buy':
            pnl = exit_price - entry_price
        else:
            pnl = entry_price - exit_price
        
        # Determine outcome
        outcome = 'win' if pnl > 0 else 'loss'
        
        return {
            'outcome': outcome,
            'pnl': pnl,
            'holding_period': holding_period
        }
    
    def _get_regime_at_time(self, timestamp: datetime, regimes: List[MarketRegime]) -> str:
        """Get market regime at specific timestamp"""
        for regime in regimes:
            if regime.start_date <= timestamp <= regime.end_date:
                return regime.name
        return 'unknown'
    
    def _calculate_backtest_metrics(self, trades: List[Dict], regimes: List[MarketRegime]) -> BacktestResult:
        """
        Calculate comprehensive backtest metrics
        
        Args:
            trades: List of trade results
            regimes: Market regimes
            
        Returns:
            Backtest result with all metrics
        """
        if not trades:
            return None
        
        # Basic metrics
        total_trades = len(trades)
        wins = [t['pnl'] for t in trades if t['outcome'] == 'win']
        losses = [t['pnl'] for t in trades if t['outcome'] == 'loss']
        
        win_rate = len(wins) / total_trades if total_trades > 0 else 0
        total_pnl = sum(t['pnl'] for t in trades)
        avg_trade_pnl = total_pnl / total_trades if total_trades > 0 else 0
        
        # P&L distribution
        pnl_series = [t['pnl'] for t in trades]
        pnl_array = np.array(pnl_series)
        
        # Sharpe ratio (assuming risk-free rate = 0)
        if len(pnl_series) > 1 and np.std(pnl_array) > 0:
            sharpe_ratio = np.mean(pnl_array) / np.std(pnl_array) * np.sqrt(252)  # Annualized
        else:
            sharpe_ratio = 0
        
        # Calculate drawdown
        cumulative_pnl = np.cumsum(pnl_series)
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdown = running_max - cumulative_pnl
        max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
        
        # Calmar ratio (annualized return / max drawdown)
        calmar_ratio = (total_pnl * 252 / len(trades)) / max_drawdown if max_drawdown > 0 else 0
        
        # Profit factor
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Risk metrics
        volatility = np.std(pnl_array)
        skewness = self._calculate_skewness(pnl_array)
        kurtosis = self._calculate_kurtosis(pnl_array)
        
        # VaR and CVaR (95% confidence)
        var_95 = np.percentile(pnl_array, 5)
        cvar_95 = np.mean(pnl_array[pnl_array <= var_95]) if len(pnl_array[pnl_array <= var_95]) > 0 else var_95
        
        # Regime performance
        regime_performance = {}
        for regime in set(t.get('regime', 'unknown') for t in trades):
            regime_trades = [t['pnl'] for t in trades if t.get('regime') == regime]
            if regime_trades:
                regime_performance[regime] = np.mean(regime_trades)
        
        # Execution costs
        execution_costs = sum(t['costs'] for t in trades)
        slippage_impact = sum(t['costs'] for t in trades)  # Simplified
        
        return BacktestResult(
            total_trades=total_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            avg_trade_pnl=avg_trade_pnl,
            sharpe_ratio=sharpe_ratio,
            calmar_ratio=calmar_ratio,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            max_drawdown_duration=0,  # Simplified
            volatility=volatility,
            skewness=skewness,
            kurtosis=kurtosis,
            var_95=var_95,
            cvar_95=cvar_95,
            regime_performance=regime_performance,
            correlation_matrix=None,  # Would calculate for multiple strategies
            execution_costs=execution_costs,
            slippage_impact=slippage_impact
        )
    
    def _calculate_skewness(self, data: np.ndarray) -> float:
        """Calculate skewness of data distribution"""
        if len(data) < 3:
            return 0
        return ((np.mean((data - np.mean(data))**3)) / (np.std(data)**3))
    
    def _calculate_kurtosis(self, data: np.ndarray) -> float:
        """Calculate kurtosis of data distribution"""
        if len(data) < 4:
            return 0
        return ((np.mean((data - np.mean(data))**4)) / (np.std(data)**4)) - 3
    
    def generate_backtest_report(self, results: List[BacktestResult]) -> Dict[str, Any]:
        """
        Generate comprehensive backtest report
        
        Args:
            results: List of backtest results from walk-forward test
            
        Returns:
            Comprehensive report with statistics and recommendations
        """
        if not results:
            return {'error': 'No backtest results available'}
        
        # Aggregate results
        total_trades = sum(r.total_trades for r in results)
        avg_win_rate = np.mean([r.win_rate for r in results])
        avg_sharpe = np.mean([r.sharpe_ratio for r in results])
        avg_calmar = np.mean([r.calmar_ratio for r in results])
        avg_profit_factor = np.mean([r.profit_factor for r in results])
        avg_max_drawdown = np.mean([r.max_drawdown for r in results])
        
        # Calculate consistency metrics
        sharpe_std = np.std([r.sharpe_ratio for r in results])
        win_rate_std = np.std([r.win_rate for r in results])
        
        # Regime analysis
        all_regime_performance = {}
        for result in results:
            for regime, performance in result.regime_performance.items():
                if regime not in all_regime_performance:
                    all_regime_performance[regime] = []
                all_regime_performance[regime].append(performance)
        
        regime_stats = {}
        for regime, performances in all_regime_performance.items():
            regime_stats[regime] = {
                'avg_performance': np.mean(performances),
                'consistency': 1.0 / (1.0 + np.std(performances)) if len(performances) > 1 else 1.0,
                'frequency': len(performances)
            }
        
        # Generate recommendations
        recommendations = []
        
        if avg_sharpe < 0.5:
            recommendations.append("Sharpe ratio below 0.5 - consider strategy improvements")
        
        if avg_max_drawdown > 0.15:
            recommendations.append("Max drawdown above 15% - consider risk management improvements")
        
        if sharpe_std > 0.5:
            recommendations.append("High Sharpe volatility - strategy may be unstable across market conditions")
        
        if win_rate_std > 0.2:
            recommendations.append("High win rate volatility - strategy consistency needs improvement")
        
        # Best performing regimes
        if regime_stats:
            best_regime = max(regime_stats.items(), key=lambda x: x[1]['avg_performance'])
            recommendations.append(f"Best performing regime: {best_regime[0]} with {best_regime[1]['avg_performance']:.4f} avg P&L")
        
        return {
            'summary': {
                'total_windows': len(results),
                'total_trades': total_trades,
                'avg_win_rate': avg_win_rate,
                'avg_sharpe_ratio': avg_sharpe,
                'avg_calmar_ratio': avg_calmar,
                'avg_profit_factor': avg_profit_factor,
                'avg_max_drawdown': avg_max_drawdown,
                'sharpe_consistency': 1.0 / (1.0 + sharpe_std) if sharpe_std > 0 else 1.0,
                'win_rate_consistency': 1.0 / (1.0 + win_rate_std) if win_rate_std > 0 else 1.0
            },
            'regime_analysis': regime_stats,
            'recommendations': recommendations,
            'risk_metrics': {
                'avg_volatility': np.mean([r.volatility for r in results]),
                'avg_var_95': np.mean([r.var_95 for r in results]),
                'avg_cvar_95': np.mean([r.cvar_95 for r in results]),
                'avg_skewness': np.mean([r.skewness for r in results]),
                'avg_kurtosis': np.mean([r.kurtosis for r in results])
            },
            'execution_analysis': {
                'avg_execution_costs': np.mean([r.execution_costs for r in results]),
                'avg_slippage_impact': np.mean([r.slippage_impact for r in results])
            }
        }

# Example usage and testing
if __name__ == "__main__":
    # Create backtester
    config = BacktestConfig(
        mode=BacktestMode.WALK_FORWARD,
        train_window_days=30,
        test_window_days=7,
        step_days=3,
        min_trades=10,
        confidence_threshold=0.6,
        regime_detection=True,
        execution_modeling=True
    )
    
    backtester = ProfessionalBacktester(config)
    
    # Load historical data (simulated)
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2024, 1, 1)
    
    market_data = backtester.load_historical_data("test_market", start_date, end_date)
    
    # Create mock bot
    class MockBot:
        def __init__(self, name):
            self.name = name
    
    mock_bot = MockBot("test_bot")
    
    # Run walk-forward test
    results = backtester.run_walk_forward_test(mock_bot, market_data)
    
    if results:
        # Generate report
        report = backtester.generate_backtest_report(results)
        
        print("🧪 Professional Backtester v3.0 Test Results")
        print(f"📊 Total windows: {report['summary']['total_windows']}")
        print(f"📈 Average Sharpe: {report['summary']['avg_sharpe_ratio']:.3f}")
        print(f"🎯 Average Win Rate: {report['summary']['avg_win_rate']:.3f}")
        print(f"📉 Average Max DD: {report['summary']['avg_max_drawdown']:.3f}")
        print(f"🔄 Sharpe Consistency: {report['summary']['sharpe_consistency']:.3f}")
        
        print("\n📋 Recommendations:")
        for rec in report['recommendations']:
            print(f"   • {rec}")
    else:
        print("❌ No backtest results generated")