#!/usr/bin/env python3
"""
Debug the professional backtester to understand why no trades are generated
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from professional_backtester import ProfessionalBacktester, BacktestConfig, BacktestMode
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class DebugMockBot:
    """Debug mock bot that always generates signals"""
    
    def __init__(self, name="debug_bot"):
        self.name = name
        self.signal_count = 0
    
    def analyze_market(self, price_data: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Always generate a signal for debugging"""
        self.signal_count += 1
        
        # Simple alternating buy/sell signals
        signal_type = 'buy' if self.signal_count % 2 == 0 else 'sell'
        
        return {
            'type': signal_type,
            'confidence': 0.8,  # High confidence
            'expected_value': 0.02,  # 2% expected return
            'size': 100
        }

def debug_backtester():
    """Debug the backtester step by step"""
    print("🔍 Debugging Professional Backtester v3.0...")
    
    # Create very lenient configuration for debugging
    config = BacktestConfig(
        mode=BacktestMode.WALK_FORWARD,
        train_window_days=30,
        test_window_days=7,
        step_days=7,
        min_trades=1,   # Just 1 trade needed
        confidence_threshold=0.1,  # Very low threshold
        regime_detection=True,
        execution_modeling=True
    )
    
    # Create backtester
    backtester = ProfessionalBacktester(config)
    
    # Create debug bot
    bot = DebugMockBot("debug_bot")
    
    # Generate minimal test data
    print("📊 Generating minimal test data...")
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 2, 1)  # Just 1 month
    
    # Create hourly data
    date_range = pd.date_range(start=start_date, end=end_date, freq='h')
    
    # Simple price data
    prices = [0.5 + np.sin(i/24) * 0.1 + np.random.normal(0, 0.01) for i in range(len(date_range))]
    prices = [max(0.01, min(0.99, p)) for p in prices]
    
    market_data = pd.DataFrame({
        'timestamp': date_range,
        'price': prices,
        'volume': [10000] * len(date_range),
        'spread': [0.01] * len(date_range)
    })
    
    print(f"📈 Generated {len(market_data)} data points")
    
    # Create custom backtester with debug logging
    class DebugBacktester(ProfessionalBacktester):
        def _simulate_bot_signal(self, bot, market_data: pd.Series, historical_data: pd.DataFrame) -> Optional[Dict[str, Any]]:
            """Override with debug logging"""
            logger.debug(f"Getting signal for timestamp: {market_data['timestamp']}")
            logger.debug(f"Historical data length: {len(historical_data)}")
            
            if len(historical_data) < 48:
                logger.debug("Not enough historical data (< 48 hours)")
                return None
            
            signal = bot.analyze_market(historical_data)
            logger.debug(f"Generated signal: {signal}")
            return signal
        
        def _simulate_trade_outcome(self, signal: Dict[str, Any], entry_data: pd.Series, future_data: pd.DataFrame) -> Optional[Dict[str, Any]]:
            """Override with debug logging"""
            logger.debug(f"Simulating trade outcome for signal: {signal['type']} at {entry_data['timestamp']}")
            logger.debug(f"Future data length: {len(future_data)}")
            
            if len(future_data) < 24:
                logger.debug("Not enough future data (< 24 hours)")
                return None
            
            outcome = super()._simulate_trade_outcome(signal, entry_data, future_data)
            logger.debug(f"Trade outcome: {outcome}")
            return outcome
        
        def run_walk_forward_test(self, bot, market_data: pd.DataFrame):
            """Override with debug logging"""
            logger.info("Starting walk-forward test...")
            
            # Check data requirements
            total_days = (market_data['timestamp'].max() - market_data['timestamp'].min()).days
            num_windows = (total_days - self.config.train_window_days) // self.config.step_days + 1
            
            logger.info(f"Total days: {total_days}")
            logger.info(f"Train window: {self.config.train_window_days} days")
            logger.info(f"Test window: {self.config.test_window_days} days")
            logger.info(f"Step days: {self.config.step_days}")
            logger.info(f"Expected windows: {num_windows}")
            
            if num_windows < 1:
                logger.error("Insufficient data for walk-forward test")
                return []
            
            results = []
            
            for window_idx in range(num_windows):
                logger.info(f"Processing window {window_idx + 1}/{num_windows}")
                
                start_offset = window_idx * self.config.step_days
                train_start = market_data['timestamp'].min() + timedelta(days=start_offset)
                train_end = train_start + timedelta(days=self.config.train_window_days)
                test_start = train_end
                test_end = test_start + timedelta(days=self.config.test_window_days)
                
                logger.debug(f"Train: {train_start} to {train_end}")
                logger.debug(f"Test: {test_start} to {test_end}")
                
                if test_end > market_data['timestamp'].max():
                    logger.warning(f"Test end {test_end} exceeds data end {market_data['timestamp'].max()}")
                    break
                
                train_data = market_data[(market_data['timestamp'] >= train_start) & 
                                       (market_data['timestamp'] <= train_end)]
                test_data = market_data[(market_data['timestamp'] >= test_start) & 
                                      (market_data['timestamp'] <= test_end)]
                
                logger.info(f"Train data points: {len(train_data)}")
                logger.info(f"Test data points: {len(test_data)}")
                
                # Simulate trading for this window
                window_result = self._simulate_bot_trading(bot, test_data, {})
                
                if window_result and window_result.total_trades >= self.config.min_trades:
                    logger.info(f"Window {window_idx + 1}: {window_result.total_trades} trades, Sharpe: {window_result.sharpe_ratio:.3f}")
                    results.append(window_result)
                else:
                    logger.warning(f"Window {window_idx + 1}: No valid results (trades: {window_result.total_trades if window_result else 0})")
            
            logger.info(f"Total valid windows: {len(results)}")
            return results
    
    # Use debug backtester
    debug_backtester = DebugBacktester(config)
    
    # Run walk-forward test
    print("\n🏃 Running debug walk-forward backtest...")
    results = debug_backtester.run_walk_forward_test(bot, market_data)
    
    print(f"\n🔍 Debug Results:")
    print(f"   Total windows: {len(results)}")
    print(f"   Bot signal count: {bot.signal_count}")
    
    if results:
        print(f"   First window trades: {results[0].total_trades}")
        print(f"   First window Sharpe: {results[0].sharpe_ratio:.3f}")
    
    print("\n✅ Debug completed!")

if __name__ == "__main__":
    debug_backtester()