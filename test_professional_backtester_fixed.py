#!/usr/bin/env python3
"""
Test the professional backtester with fixed data generation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from professional_backtester import ProfessionalBacktester, BacktestConfig, BacktestMode
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any

class SimpleMockBot:
    """Simple mock bot that generates signals based on price momentum"""
    
    def __init__(self, name="simple_bot"):
        self.name = name
        self.signal_count = 0
    
    def analyze_market(self, price_data: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Generate simple momentum-based signals"""
        if len(price_data) < 24:  # Need at least 24 hours
            return None
        
        self.signal_count += 1
        
        # Simple momentum: compare current price to 24h ago
        current_price = price_data['price'].iloc[-1]
        price_24h_ago = price_data['price'].iloc[-24]
        momentum = (current_price - price_24h_ago) / price_24h_ago
        
        # Generate signal based on momentum
        if abs(momentum) > 0.005:  # 0.5% threshold
            signal_type = 'buy' if momentum > 0 else 'sell'
            confidence = min(0.9, max(0.3, abs(momentum) * 10))
            
            return {
                'type': signal_type,
                'confidence': confidence,
                'expected_value': abs(momentum),
                'size': 100
            }
        
        return None

def test_fixed_backtester():
    """Test the backtester with properly sized data"""
    print("🧪 Testing Professional Backtester v3.0 (Fixed)...")
    
    # Create configuration
    config = BacktestConfig(
        mode=BacktestMode.WALK_FORWARD,
        train_window_days=30,
        test_window_days=7,
        step_days=7,
        min_trades=1,
        confidence_threshold=0.2,
        regime_detection=True,
        execution_modeling=True
    )
    
    # Create backtester
    backtester = ProfessionalBacktester(config)
    
    # Create mock bot
    bot = SimpleMockBot("test_bot")
    
    # Generate sufficient historical data
    print("📊 Generating historical data...")
    
    # Calculate required data length
    # We need: train_window_days + test_window_days + step_days * (num_windows - 1)
    # For 4 windows: 30 + 7 + 7 * 3 = 58 days minimum
    total_days_needed = 90  # 3 months of data
    
    start_date = datetime(2023, 1, 1)
    end_date = start_date + timedelta(days=total_days_needed)
    
    # Create hourly data
    date_range = pd.date_range(start=start_date, end=end_date, freq='h')
    
    # Generate price data with some trends
    np.random.seed(42)
    
    # Create trending price data
    base_price = 0.5
    prices = []
    
    for i in range(len(date_range)):
        # Add trend and noise
        trend_component = (i / len(date_range)) * 0.2  # Upward trend
        noise = np.random.normal(0, 0.01)
        
        # Add some cycles
        cycle = 0.05 * np.sin(i / 24)  # Daily cycle
        
        price = base_price + trend_component + cycle + noise
        price = max(0.01, min(0.99, price))
        prices.append(price)
    
    # Create DataFrame
    market_data = pd.DataFrame({
        'timestamp': date_range,
        'price': prices,
        'volume': [10000] * len(date_range),
        'spread': [0.01] * len(date_range)
    })
    
    print(f"📈 Generated {len(market_data)} hourly data points")
    print(f"   Date range: {market_data['timestamp'].min()} to {market_data['timestamp'].max()}")
    print(f"   Price range: ${market_data['price'].min():.3f} - ${market_data['price'].max():.3f}")
    
    # Create custom backtester that uses our bot
    class EnhancedBacktester(ProfessionalBacktester):
        def _simulate_bot_signal(self, bot, market_data: pd.Series, historical_data: pd.DataFrame) -> Optional[Dict[str, Any]]:
            """Override to use our bot's analyze_market method"""
            return bot.analyze_market(historical_data)
    
    # Use enhanced backtester
    enhanced_backtester = EnhancedBacktester(config)
    
    # Run walk-forward test
    print("\n🏃 Running walk-forward backtest...")
    results = enhanced_backtester.run_walk_forward_test(bot, market_data)
    
    print(f"\n📊 Results Summary:")
    print(f"   Total windows: {len(results)}")
    print(f"   Bot signal count: {bot.signal_count}")
    
    if results:
        print(f"   ✅ Successfully generated {len(results)} backtest windows")
        
        # Generate comprehensive report
        report = enhanced_backtester.generate_backtest_report(results)
        
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
        
        print("\n💰 Execution Analysis:")
        print(f"   Average execution costs: ${report['execution_analysis']['avg_execution_costs']:.4f}")
        print(f"   Average slippage impact: ${report['execution_analysis']['avg_slippage_impact']:.4f}")
        
        if report['regime_analysis']:
            print("\n🎯 Regime Performance:")
            for regime, stats in report['regime_analysis'].items():
                print(f"   {regime}: {stats['avg_performance']:.4f} avg P&L "
                      f"({stats['frequency']} occurrences)")
        
        print("\n💡 Recommendations:")
        for rec in report['recommendations']:
            print(f"   • {rec}")
        
        print("\n✅ Professional backtester v3.0 test completed successfully!")
        
    else:
        print("❌ No backtest results generated")
        print("   This might indicate:")
        print("   - Insufficient signals from the bot")
        print("   - Data quality issues")
        print("   - Configuration problems")

if __name__ == "__main__":
    test_fixed_backtester()