import sys
import os
import logging

# Ensure project root is in path
sys.path.append(os.getcwd())

from discovery.market_discovery import MarketDiscovery

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")

def test_discovery():
    print("\n🔎 Iniciando teste de Market Discovery (Crypto Only)...")
    print("-------------------------------------------------------")
    
    # Force enable crypto, disable others
    discovery = MarketDiscovery(
        enable_crypto=True,
        enable_finance=False,
        enable_politics=False,
        enable_sports=False,
        min_liquidity=25,      # ← bem baixo só para teste 
        min_volume=150,        # ← bem baixo só para teste 
        max_spread=35.0        # ← aumentado
    )
    
    # Override keywords temporarily to include specific "up or down" check explicitly if needed,
    # but the class already has "crypto" keywords. 
    # Let's see what it finds with default crypto keywords + logic.
    
    markets = discovery.run()
    
    print(f"\n✅ Encontrados {len(markets)} mercados qualificados.")
    print("-------------------------------------------------------")
    
    # Filter for "up or down" specifically to show the user
    up_down_markets = [m for m in markets if "up or down" in m.get("question", "").lower()]
    
    print(f"📊 Mercados 'Up or Down' (5min/15min): {len(up_down_markets)}")
    for m in up_down_markets[:10]: # Show top 10
        print(f"  - {m.get('question')} (Liq: ${float(m.get('liquidity', 0)):.2f})")
        
    print("\n📊 Outros Mercados Crypto (Top 5):")
    other_crypto = [m for m in markets if m not in up_down_markets]
    for m in other_crypto[:5]:
         print(f"  - {m.get('question')} (Liq: ${float(m.get('liquidity', 0)):.2f})")

if __name__ == "__main__":
    test_discovery()
