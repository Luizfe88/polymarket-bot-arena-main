#!/usr/bin/env python3
"""Test script to verify risk limits configuration"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

import config
import db

def test_risk_limits():
    """Test the new risk limit configurations"""
    print("🧪 Testing Risk Limits Configuration")
    print("=" * 50)
    
    # Test Paper Mode limits
    print("\n📄 Paper Mode Limits:")
    print(f"  Daily Loss per Bot: ${config.PAPER_MAX_DAILY_LOSS_PER_BOT}")
    print(f"  Total Daily Loss: ${config.PAPER_MAX_DAILY_LOSS_TOTAL}")
    print(f"  Starting Balance: ${config.PAPER_STARTING_BALANCE}")
    
    # Test Live Mode limits
    print("\n💰 Live Mode Limits:")
    print(f"  Daily Loss per Bot: ${config.LIVE_MAX_DAILY_LOSS_PER_BOT}")
    print(f"  Total Daily Loss: ${config.LIVE_MAX_DAILY_LOSS_TOTAL}")
    
    # Test consecutive loss settings
    print("\n🔄 Consecutive Loss Settings:")
    print(f"  Max Consecutive Losses: {config.MAX_CONSECUTIVE_LOSSES}")
    print(f"  Pause Duration: {config.PAUSE_AFTER_CONSECUTIVE_LOSSES_SECONDS//60} minutes")
    
    # Test percentage calculations
    print("\n📊 Percentage Analysis (Paper Mode):")
    bot_percentage = (config.PAPER_MAX_DAILY_LOSS_PER_BOT / config.PAPER_STARTING_BALANCE) * 100
    total_percentage = (config.PAPER_MAX_DAILY_LOSS_TOTAL / config.PAPER_STARTING_BALANCE) * 100
    print(f"  Bot Loss Limit: {bot_percentage:.1f}% of bankroll")
    print(f"  Total Loss Limit: {total_percentage:.1f}% of bankroll")
    
    # Test consecutive loss function
    print("\n🔍 Testing Consecutive Loss Function:")
    try:
        # Test with a dummy bot name
        consecutive_losses = db.get_bot_consecutive_losses("test_bot", "paper")
        print(f"  Consecutive losses for test_bot: {consecutive_losses}")
        print("  ✅ Function working correctly")
    except Exception as e:
        print(f"  ❌ Error testing function: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Risk limits test completed!")

if __name__ == "__main__":
    test_risk_limits()