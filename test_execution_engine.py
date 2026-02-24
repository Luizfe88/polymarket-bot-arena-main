#!/usr/bin/env python3
"""
Test script for the professional execution engine
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution_engine import ExecutionEngine, OrderType, CostBreakdown
import config

def test_execution_engine():
    """Test the execution engine functionality"""
    print("Testing Professional Execution Engine...")
    
    # Create execution engine
    engine = ExecutionEngine()
    
    # Test market data
    market_data = {
        "bids": [{"price": 0.45, "size": 100}, {"price": 0.44, "size": 200}],
        "asks": [{"price": 0.55, "size": 150}, {"price": 0.56, "size": 250}],
        "current_price": 0.50
    }
    
    print("\n1. Testing optimal price calculation...")
    buy_price = engine.calculate_optimal_order_price(market_data, "buy", 100)
    sell_price = engine.calculate_optimal_order_price(market_data, "sell", 100)
    print(f"   Buy price: {buy_price:.3f}")
    print(f"   Sell price: {sell_price:.3f}")
    
    print("\n2. Testing cost calculation...")
    cost_breakdown = engine.calculate_total_cost(
        size=100, 
        price=0.50, 
        order_type=OrderType.POST_ONLY,
        market_data=market_data
    )
    print(f"   Total cost: ${cost_breakdown.total_cost:.3f}")
    print(f"   Total cost %: {cost_breakdown.total_cost_pct:.2%}")
    print(f"   Spread cost: ${cost_breakdown.spread_cost:.3f}")
    print(f"   Taker fee: ${cost_breakdown.taker_fee:.3f}")
    print(f"   Gas cost: ${cost_breakdown.gas_cost:.3f}")
    
    print("\n3. Testing execution recommendation...")
    recommendation = engine.get_execution_recommendation(market_data, "buy", 150)
    print(f"   Recommended strategy: {recommendation['recommended_strategy']}")
    print(f"   Optimal price: {recommendation['optimal_price']:.3f}")
    print(f"   Estimated cost: {recommendation['estimated_cost_pct']:.2%}")
    print(f"   Market impact: {recommendation['market_impact']}")
    
    print("\n4. Testing trade execution decision...")
    expected_value = 0.06  # 6% expected value
    should_execute = engine.should_execute_trade(expected_value, cost_breakdown)
    print(f"   Expected value: {expected_value:.2%}")
    print(f"   Should execute: {should_execute}")
    print(f"   Net EV: {expected_value - cost_breakdown.total_cost_pct:.2%}")
    
    print("\n5. Testing with different order sizes...")
    for size in [50, 200, 500, 1000]:
        rec = engine.get_execution_recommendation(market_data, "buy", size)
        cost = engine.calculate_total_cost(size, 0.50, OrderType.POST_ONLY, market_data)
        print(f"   Size {size}: Strategy={rec['recommended_strategy']}, Cost={cost.total_cost_pct:.2%}, Impact={rec['market_impact']}")
    
    print("\n✅ Execution engine tests completed successfully!")

if __name__ == "__main__":
    test_execution_engine()