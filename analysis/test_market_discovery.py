#!/usr/bin/env python3
"""Test script to verify market discovery for BTC, ETH, and SOL."""

import os
import sys
import json
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from arena import discover_markets
from config import SIMMER_API_KEY_PATH

def load_api_key():
    """Load API key from file."""
    try:
        import json
        with open(SIMMER_API_KEY_PATH, "r") as f:
            data = json.load(f)
            return data.get("api_key")
    except:
        return None

def test_market_discovery():
    """Test market discovery for multiple cryptocurrencies."""
    print("🚀 Testing market discovery for BTC, ETH, and SOL...")
    
    api_key = load_api_key()
    if not api_key:
        print("❌ API key not found. Please ensure SIMMER_API_KEY_PATH is configured.")
        return
    
    try:
        markets = discover_markets(api_key)
        
        if not markets:
            print("❌ No markets found!")
            return
        
        print(f"✅ Found {len(markets)} markets total")
        
        # Categorize markets by crypto type
        btc_markets = []
        eth_markets = []
        sol_markets = []
        
        for market in markets:
            question = market.get("question", "").lower()
            
            if any(term in question for term in ["eth", "ethereum"]):
                eth_markets.append(market)
            elif any(term in question for term in ["sol", "solana"]):
                sol_markets.append(market)
            elif any(term in question for term in ["btc", "bitcoin"]):
                btc_markets.append(market)
        
        print(f"\n📊 Market Breakdown:")
        print(f"  🟡 Bitcoin (BTC): {len(btc_markets)} markets")
        print(f"  🔷 Ethereum (ETH): {len(eth_markets)} markets")
        print(f"  🟢 Solana (SOL): {len(sol_markets)} markets")
        
        # Show sample markets
        if btc_markets:
            print(f"\n🟡 BTC Sample: {btc_markets[0].get('question', 'No question')}")
        if eth_markets:
            print(f"🔷 ETH Sample: {eth_markets[0].get('question', 'No question')}")
        if sol_markets:
            print(f"🟢 SOL Sample: {sol_markets[0].get('question', 'No question')}")
        
        # Save results to file for inspection
        results = {
            "total_markets": len(markets),
            "btc_count": len(btc_markets),
            "eth_count": len(eth_markets),
            "sol_count": len(sol_markets),
            "markets": [
                {
                    "id": m.get("id"),
                    "question": m.get("question"),
                    "resolves_at": m.get("resolves_at"),
                    "status": m.get("status")
                }
                for m in markets
            ]
        }
        
        with open("market_discovery_test.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Results saved to market_discovery_test.json")
        
    except Exception as e:
        print(f"❌ Error during market discovery: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_market_discovery()