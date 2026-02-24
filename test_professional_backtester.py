#!/usr/bin/env python3
"""
Test the professional backtester with better simulation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from professional_backtester import ProfessionalBacktester, BacktestConfig, BacktestMode
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

class EnhancedMockBot:
    """Enhanced mock bot that generates more realistic signals"""
    
    def __init__(self, name="enhanced_bot"):
        self.name = name
        self.win_rate = 0.65  # 65% win rate
        self.avg_return = 0.02  # 2% average return
        self.volatility = 0.05  # 5% volatility
    
    def analyze_market(self, price_data: pd.DataFrame) -> dict:
        """
        Generate trading signals based on price action
        More sophisticated than the simple simulation
        """
        if len(price_data) < 48:  # Need at least 48 hours of data
            return None
        
        # Calculate technical indicators
        recent_prices = price_data['price'].tail(48)
        current_price = recent_prices.iloc[-1]
        
        # Simple momentum strategy
        short_ma = recent_prices.tail(12).mean()  # 12-hour MA
        long_ma = recent_prices.mean()  # 48-hour MA
        
        # Calculate momentum
        momentum = (short_ma - long_ma) / long_ma
        
        # Generate signal based on momentum with some noise
        if abs(momentum) > 0.001:  # Significant momentum
            # Add some randomness to simulate real market conditions
            signal_strength = abs(momentum) * 10 + np.random.normal(0, 0.1)
            confidence = min(0.9, max(0.1, 0.6 + signal_strength))
            
            if momentum > 0:
                return {
                    'type': 'buy',
                    'confidence': confidence,
                    'expected_value': self.avg_return * confidence,
                    'size': 100
                }
            else:
                return {
                    'type': 'sell', 
                    'confidence': confidence,
                    'expected_value': self.avg_return * confidence,
                    'size': 100
                }
        
        return None

def test_enhanced_backtester():
    """Test the professional backtester with enhanced simulation"""
    print("🧪 Testing Professional Backtester v3.0...")
    
    # Create backtest configuration
    config = BacktestConfig(
        mode=BacktestMode.WALK_FORWARD,
        train_window_days=30,
        test_window_days=7,
        step_days=7,  # Weekly steps for more windows
        min_trades=5,   # Lower threshold for testing
        confidence_threshold=0.5,  # Lower threshold for more signals
        regime_detection=True,
        execution_modeling=True
    )
    
    # Create backtester
    backtester = ProfessionalBacktester(config)
    
    # Create enhanced mock bot
    bot = EnhancedMockBot("test_bot")
    
    # Generate more comprehensive historical data
    print("📊 Generating historical data...")
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2024, 1, 1)
    
    # Create hourly data for a full year
    date_range = pd.date_range(start=start_date, end=end_date, freq='h')
    
    # Generate more realistic price data with trends and volatility clusters
    np.random.seed(42)
    
    # Base parameters
    base_price = 0.5
    volatility = 0.02
    trend = 0.0001  # Slight upward trend
    
    prices = []
    volumes = []
    spreads = []
    
    for i in range(len(date_range)):
        # Add volatility clustering (GARCH-like)
        if i > 24 and len(prices) >= 24:
            recent_prices = prices[-24:]
            recent_returns = [(recent_prices[j] - recent_prices[j-1]) / recent_prices[j-1] 
                             for j in range(1, len(recent_prices))]
            recent_vol = np.std(recent_returns)
            current_vol = volatility + 0.5 * recent_vol
        else:
            current_vol = volatility
        
        # Generate return with trend
        return_shock = np.random.normal(trend, current_vol)
        
        # Add occasional large moves
        if np.random.random() < 0.01:  # 1% chance of large move
            return_shock += np.random.choice([-1, 1]) * 0.05
        
        if i == 0:
            new_price = base_price
        else:
            new_price = prices[-1] * (1 + return_shock)
        
        new_price = max(0.01, min(0.99, new_price))
        prices.append(new_price)
        
        # Volume (higher when volatility is higher)
        volume = np.random.lognormal(10, 1) * (1 + current_vol * 10)
        volumes.append(volume)
        
        # Spread (wider when volatility is higher)
        spread = 0.005 + current_vol * 0.5 + np.random.exponential(0.001)
        spreads.append(spread)
    
    # Create DataFrame
    market_data = pd.DataFrame({
        'timestamp': date_range,
        'price': prices,
        'volume': volumes,
        'spread': spreads
    })
    
    print(f"📈 Generated {len(market_data)} hourly data points")
    print(f"   Price range: ${market_data['price'].min():.3f} - ${market_data['price'].max():.3f}")
    print(f"   Average volume: {market_data['volume'].mean():.0f}")
    print(f"   Average spread: {market_data['spread'].mean():.4f}")
    
    # Override the bot signal simulation in backtester
    def enhanced_simulate_bot_signal(bot, market_data, historical_data):
        """Enhanced signal simulation using our mock bot"""
        return bot.analyze_market(historical_data)
    
    # Monkey patch the backtester with our enhanced simulation
    backtester._simulate_bot_signal = enhanced_simulate_bot_signal
    
    # Run walk-forward test
    print("\n🏃 Running walk-forward backtest...")
    results = backtester.run_walk_forward_test(bot, market_data)
    
    if results:
        print(f"✅ Completed {len(results)} walk-forward windows")
        
        # Generate comprehensive report
        report = backtester.generate_backtest_report(results)
        
        print("\n📋 Backtest Results Summary:")
        print(f"   Total windows: {report['summary']['total_windows']}")
        print(f"   Total trades: {report['summary']['total_trades']}")
        print(f"   Average win rate: {report['summary']['avg_win_rate']:.3f}")
        print(f"   Average Sharpe ratio: {report['summary']['avg_sharpe_ratio']:.3f}")
        print(f"   Average Calmar ratio: {report['summary']['avg_calmar_ratio']:.3f}")
        print(f"   Average profit factor: {report['summary']['avg_profit_factor']:.3f}")
        print(f"   Average max drawdown: {report['summary']['avg_max_drawdown']:.3f}")
        print(f"   Sharpe consistency: {report['summary']['sharpe_consistency']:.3f}")
        print(f"   Win rate consistency: {report['summary']['win_rate_consistency']:.3f}")
        
        print("\n📊 Risk Metrics:")
        print(f"   Average volatility: {report['risk_metrics']['avg_volatility']:.4f}")
        print(f"   Average VaR (95%): {report['risk_metrics']['avg_var_95']:.4f}")
        print(f"   Average CVaR (95%): {report['risk_metrics']['avg_cvar_95']:.4f}")
        print(f"   Average skewness: {report['risk_metrics']['avg_skewness']:.3f}")
        print(f"   Average kurtosis: {report['risk_metrics']['avg_kurtosis']:.3f}")
        
        print("\n💰 Execution Analysis:")
        print(f"   Average execution costs: ${report['execution_analysis']['avg_execution_costs']:.4f}")
        print(f"   Average slippage impact: ${report['execution_analysis']['avg_slippage_impact']:.4f}")
        
        if report['regime_analysis']:
            print("\n🎯 Regime Performance:")
            for regime, stats in report['regime_analysis'].items():
                print(f"   {regime}: {stats['avg_performance']:.4f} avg P&L "
                      f"({stats['frequency']} occurrences, consistency: {stats['consistency']:.3f})")
        
        print("\n💡 Recommendations:")
        for rec in report['recommendations']:
            print(f"   • {rec}")
        
        print("\n✅ Professional backtester v3.0 test completed successfully!")
        
    else:
        print("❌ No backtest results generated - check configuration and data")
        print("   Try adjusting confidence_threshold, min_trades, or step_days")

if __name__ == "__main__":
    test_enhanced_backtester()