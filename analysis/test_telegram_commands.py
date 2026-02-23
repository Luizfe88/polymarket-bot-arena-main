#!/usr/bin/env python3
"""
Test script for Telegram commands

This script tests the Telegram command handlers without needing to run the full bot.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from telegram_commands import commands_handler

def test_commands():
    """Test all Telegram commands."""
    print("🧪 Testing Telegram Commands...")
    print("=" * 50)
    
    test_user_id = "123456789"
    
    # Test commands
    commands_to_test = [
        "/start",
        "/help",
        "/bots",
        "/status", 
        "/trades",
        "/evolucao",
        "/evolução",  # Alternative spelling
        "/reset",
        "/ranking",
        "/performance",
        "/resumo",
        "/unknown_command",  # Should show help
    ]
    
    for command in commands_to_test:
        print(f"\n📡 Testing: {command}")
        print("-" * 30)
        
        try:
            response = commands_handler.process_command(command, test_user_id)
            print(f"Response length: {len(response)} characters")
            print(f"First 200 chars: {response[:200]}...")
            
            # Check for error indicators
            if "❌" in response:
                print("⚠️  Error detected in response")
            elif "✅" in response or "🟢" in response:
                print("✅ Positive indicators found")
            else:
                print("ℹ️  Neutral response")
                
        except Exception as e:
            print(f"❌ Error processing command: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("✅ Command testing complete!")

if __name__ == "__main__":
    test_commands()