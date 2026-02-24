import json
import requests
from datetime import datetime, timedelta, timezone

def debug_markets():
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "limit": 10,
        "offset": 0,
        "active": "true",
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    response = requests.get(url, params=params, headers=headers, timeout=15)
    markets = response.json()
    
    print("=== DEBUG MERCADOS ===")
    now = datetime.now(timezone.utc)
    
    for i, market in enumerate(markets[:5]):
        print(f"\n--- Mercado {i+1} ---")
        print(f"Pergunta: {market.get('question', 'N/A')}")
        volume = float(market.get('volume', 0) or 0)
        print(f"Volume: ${volume:,.0f}")
        print(f"Categoria: {market.get('category', 'N/A')}")
        print(f"Ativo: {market.get('active', 'N/A')}")
        print(f"EndDate: {market.get('endDate', 'N/A')}")
        print(f"BestBid: {market.get('bestBid', 'N/A')}")
        print(f"BestAsk: {market.get('bestAsk', 'N/A')}")
        
        # Calcular spread
        best_bid = float(market.get('bestBid', 0))
        best_ask = float(market.get('bestAsk', 0))
        if best_bid > 0 and best_ask > 0:
            spread = (best_ask - best_bid) / best_ask
            print(f"Spread: {spread:.4f} ({spread*100:.2f}%)")
        
        # Calcular TTE
        end_date_str = market.get('endDate')
        if end_date_str:
            try:
                end_dt = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                tte = end_dt - now
                print(f"TTE: {tte.days}d {tte.seconds//3600}h")
                
                # Verificar rejeição crypto 5min
                q = (market.get('question') or "").lower()
                assets = ["bitcoin", "btc", "ethereum", "eth", "solana", "sol"]
                short_kw = ["up or down", "up/down", "5 min", "5-min", "5min"]
                has_asset = any(a in q for a in assets)
                has_short = any(k in q for k in short_kw)
                tte_seconds = max(0, int((end_dt - now).total_seconds()))
                rejected = has_asset and has_short and tte_seconds <= 3600
                print(f"Rejeitado (crypto 5min): {rejected}")
                print(f"  - Tem asset crypto: {has_asset}")
                print(f"  - Tem keyword curta: {has_short}")
                print(f"  - TTE <= 3600s: {tte_seconds <= 3600}")
                
            except Exception as e:
                print(f"Erro TTE: {e}")
        
        # Verificar categoria
        category = (market.get('category') or 'unknown').lower()
        priority_categories = ["politics", "crypto", "sports", "macro", "tech"]
        has_priority = any(cat in category for cat in priority_categories)
        print(f"Categoria prioritaria: {has_priority}")
        print(f"  - Categoria: '{category}'")
        print(f"  - Prioridades: {priority_categories}")

if __name__ == "__main__":
    debug_markets()