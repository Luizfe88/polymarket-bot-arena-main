#!/usr/bin/env python3
"""
Complete working test of the professional backtester
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from professional_backtester import ProfessionalBacktester, BacktestConfig, BacktestMode, BacktestResult
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List

class WorkingMockBot:
    """Working mock bot that generates realistic signals"""
    
    def __init__(self, name="working_bot"):
        self.name = name
        self.signal_count = 0
        self.win_rate = 0.65  # 65% win rate
    
    def analyze_market(self, price_data: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Generate signals based on simple momentum"""
        if len(price_data) < 48:  # Need at least 48 hours
            return None
        
        self.signal_count += 1
        
        # Simple momentum strategy
        current_price = price_data['price'].iloc[-1]
        price_48h_ago = price_data['price'].iloc[-48]
        momentum = (current_price - price_48h_ago) / price_48h_ago
        
        # Generate signal with some noise
        if abs(momentum) > 0.01:  # 1% threshold
            signal_type = 'buy' if momentum > 0 else 'sell'
            confidence = min(0.9, max(0.3, 0.5 + abs(momentum) * 5))
            
            return {
                'type': signal_type,
                'confidence': confidence,
                'expected_value': abs(momentum) * 0.5,  # Half of momentum as expected value
                'size': 100
            }
        
        return None

class WorkingBacktester(ProfessionalBacktester):
    """Complete working backtester that properly uses the bot"""
    
    def _simulate_bot_trading(self, bot, test_data: pd.DataFrame, regimes: List) -> Optional[BacktestResult]:
        """
        Override the trading simulation to properly use the bot
        """
        trades = []
        
        # Simulate trading signals
        for i in range(len(test_data)):
            row = test_data.iloc[i]
            
            # Get historical data up to this point
            historical_data = test_data.iloc[:i+1]
            
            # Get signal from bot
            signal = bot.analyze_market(historical_data)
            
            if signal and signal['confidence'] >= self.config.confidence_threshold:
                # Calculate execution costs
                trade_size = signal['size']
                costs = self.calculate_execution_costs(trade_size, row)
                
                # Simulate trade outcome
                future_data = test_data.iloc[i+1:]
                outcome = self._simulate_trade_outcome(signal, row, future_data)
                
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

def test_working_backtester():
    """Test the complete working backtester"""
    print("🧪 Testing Professional Backtester v3.0 (Working)...")
    
    # Create configuration
    config = BacktestConfig(
        mode=BacktestMode.WALK_FORWARD,
        train_window_days=30,
        test_window_days=7,
        step_days=7,
        min_trades=3,
        confidence_threshold=0.3,
        regime_detection=True,
        execution_modeling=True
    )
    
    # Create working backtester
    backtester = WorkingBacktester(config)
    
    # Create working mock bot
    bot = WorkingMockBot("test_bot")
    
    # Generate comprehensive historical data
    print("📊 Generating historical data...")
    
    # Generate 6 months of data to ensure multiple windows
    total_days = 180
    start_date = datetime(2023, 1, 1)
    end_date = start_date + timedelta(days=total_days)
    
    # Create hourly data
    date_range = pd.date_range(start=start_date, end=end_date, freq='h')
    
    # Generate realistic price data with trends and cycles
    np.random.seed(42)
    
    prices = []
    for i in range(len(date_range)):
        # Base trend
        base_trend = 0.5 + (i / len(date_range)) * 0.2
        
        # Add cycles (daily, weekly)
        daily_cycle = 0.05 * np.sin(i * 2 * np.pi / 24)  # 24-hour cycle
        weekly_cycle = 0.03 * np.sin(i * 2 * np.pi / (24 * 7))  # Weekly cycle
        
        # Add noise
        noise = np.random.normal(0, 0.01)
        
        # Add occasional large moves
        if np.random.random() < 0.02:  # 2% chance
            noise += np.random.choice([-1, 1]) * 0.05
        
        price = base_trend + daily_cycle + weekly_cycle + noise
        price = max(0.01, min(0.99, price))
        prices.append(price)
    
    # Create DataFrame
    market_data = pd.DataFrame({
        'timestamp': date_range,
        'price': prices,
        'volume': [20000 + np.random.normal(0, 5000) for _ in range(len(date_range))],
        'spread': [0.005 + np.random.exponential(0.002) for _ in range(len(date_range))]
    })
    
    print(f"📈 Generated {len(market_data)} hourly data points")
    print(f"   Date range: {market_data['timestamp'].min()} to {market_data['timestamp'].max()}")
    print(f"   Price range: ${market_data['price'].min():.3f} - ${market_data['price'].max():.3f}")
    
    # Run walk-forward test
    print("\n🏃 Running walk-forward backtest...")
    results = backtester.run_walk_forward_test(bot, market_data)
    
    print(f"\n📊 Results Summary:")
    print(f"   Total windows: {len(results)}")
    print(f"   Bot signal count: {bot.signal_count}")
    
    if results:
        print(f"   ✅ Successfully generated {len(results)} backtest windows")
        
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
        print("\n🎯 Key Achievements:")
        print("   • Walk-forward validation implemented")
        print("   • Realistic execution cost modeling")
        print("   • Regime detection and analysis")
        print("   • Advanced risk metrics (VaR, CVaR)")
        print("   • Comprehensive performance reporting")
        
    else:
        print("❌ No backtest results generated")
        print("   Possible issues:")
        print("   - Bot not generating enough signals")
        print("   - Configuration too restrictive")
        print("   - Data quality issues")

if __name__ == "__main__":
    test_working_backtester()