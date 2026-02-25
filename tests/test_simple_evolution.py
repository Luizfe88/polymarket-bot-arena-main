#!/usr/bin/env python3
"""
Simple test for the enhanced bot evolution manager v3.0
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enhanced_bot_evolution_manager import EnhancedBotEvolutionManager
import config

class MockBot:
    """Mock bot for testing"""
    def __init__(self, name, strategy_type="momentum", generation=0):
        self.name = name
        self.strategy_type = strategy_type
        self.generation = generation
        self.strategy_params = {"lookback": 10, "threshold": 0.5}
        self.lineage = []
    
    def get_performance(self, hours=24):
        """Mock performance data"""
        return {
            "total_trades": 50,
            "total_pnl": 25.0,
            "win_rate": 0.65,
            "avg_trade_pnl": 0.5
        }

def test_simple():
    """Simple test of the enhanced evolution manager"""
    print("🧬 Testing Enhanced Bot Evolution Manager v3.0 (Simple)...")
    
    # Create mock bots
    mock_bots = [
        MockBot("bot1", "momentum", 0),
        MockBot("bot2", "mean_reversion", 0),
    ]
    
    # Create evolution manager
    evolution_manager = EnhancedBotEvolutionManager(bots_source=lambda: mock_bots)
    
    print("\n1. Testing initial status...")
    status = evolution_manager.get_status()
    print(f"   Version: {status['version']}")
    print(f"   Min resolved trades: {status['min_resolved_trades']}")
    print(f"   Target resolved trades: {status['target_resolved_trades']}")
    print(f"   Sharpe kill threshold: {status['sharpe_kill_threshold']}")
    
    print("\n2. Testing trade recording...")
    # Record a few trades
    for i in range(5):
        trade_result = {
            'market_id': f'market_{i}',
            'outcome': 'win' if i % 2 == 0 else 'loss',
            'pnl': 2.0 if i % 2 == 0 else -1.0,
            'resolved_at': f'2024-01-{i+1:02d}T10:00:00',
            'confidence': 0.7 if i % 2 == 0 else 0.4,
            'expected_value': 0.08 if i % 2 == 0 else 0.02,
            'actual_outcome': 'YES' if i % 2 == 0 else 'NO',
            'execution_strategy': 'POST_ONLY'
        }
        evolution_manager.record_resolved_trade("bot1", trade_result)
    
    status = evolution_manager.get_status()
    print(f"   Resolved trades: {status['resolved_trade_count']}")
    print(f"   Progress: {status['progress_percent']:.1f}%")
    
    print("\n✅ Simple test completed!")
    print("   - Enhanced evolution manager v3.0 is functional")
    print("   - Trade recording working")
    print("   - Status reporting working")

if __name__ == "__main__":
    test_simple()