import json
import requests
from datetime import datetime, timedelta, timezone

def debug_markets_v3():
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "limit": 20,
        "offset": 0,
        "active": "true",
        "closed": "false",
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    response = requests.get(url, params=params, headers=headers, timeout=15)
    markets = response.json()
    
    print("=== DEBUG MERCADOS V3 ===")
    now = datetime.now(timezone.utc)
    
    # Critérios
    min_volume = 150000
    max_spread = 0.025
    min_hours = 6
    max_hours = 45 * 24
    priority_categories = ["politics", "crypto", "sports", "macro", "tech"]
    
    print(f"Critérios:")
    print(f"  - Volume mínimo: ${min_volume:,.0f}")
    print(f"  - Spread máximo: {max_spread:.2%}")
    print(f"  - TTE: {min_hours}h - {max_hours/24:.0f}d")
    print(f"  - Categorias: {priority_categories}")
    
    qualified_count = 0
    
    for i, market in enumerate(markets):
        print(f"\n--- Mercado {i+1} ---")
        
        # Informações básicas
        question = market.get('question', 'N/A')
        volume = float(market.get('volume', 0) or 0)
        raw_category = market.get('category', 'unknown')
        end_date_str = market.get('endDate')
        is_active = bool(market.get('active', False))
        
        print(f"Pergunta: {question}")
        print(f"Volume: ${volume:,.0f}")
        print(f"Categoria bruta: '{raw_category}'")
        print(f"Ativo: {is_active}")
        
        # Verificar se é mercado válido
        if not end_date_str or not is_active:
            print("❌ REJEITADO: Sem data fim ou inativo")
            continue
            
        # Calcular TTE
        try:
            end_dt = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
            time_to_resolution = end_dt - now
            tte_hours = time_to_resolution.total_seconds() / 3600
            print(f"TTE: {tte_hours:.1f}h ({time_to_resolution.days}d)")
            
            if tte_hours < 0:
                print("❌ REJEITADO: Mercado já expirou")
                continue
                
        except Exception as e:
            print(f"❌ REJEITADO: Erro ao calcular TTE: {e}")
            continue
        
        # Verificar volume
        volume_ok = volume >= min_volume
        print(f"Volume OK: {volume_ok}")
        
        # Calcular spread
        best_bid = float(market.get('bestBid', 0))
        best_ask = float(market.get('bestAsk', 0))
        if best_bid > 0 and best_ask > 0:
            spread = (best_ask - best_bid) / best_ask
            spread_ok = spread <= max_spread
            print(f"Spread: {spread:.4f} ({spread*100:.2f}%) - OK: {spread_ok}")
        else:
            print(f"❌ REJEITADO: Sem bid/ask válido (bid: {best_bid}, ask: {best_ask})")
            continue
        
        # Verificar TTE
        tte_ok = min_hours <= tte_hours <= max_hours
        print(f"TTE OK: {tte_ok}")
        
        # Mapear categoria
        def map_category(cat):
            if not cat:
                return "unknown"
            cat = cat.lower()
            if "politics" in cat or "us-politics" in cat or "election" in cat or "affairs" in cat:
                return "politics"
            elif "crypto" in cat or "bitcoin" in cat or "ethereum" in cat:
                return "crypto"
            elif "sports" in cat or "sport" in cat:
                return "sports"
            elif "tech" in cat or "technology" in cat or "business" in cat or "companies" in cat:
                return "tech"
            elif "economy" in cat or "macro" in cat or "finance" in cat or "markets" in cat or "trading" in cat:
                return "macro"
            return cat
        
        mapped_category = map_category(raw_category)
        category_ok = mapped_category in priority_categories
        print(f"Categoria mapeada: '{mapped_category}' - OK: {category_ok}")
        
        # Verificar crypto 5min
        q = question.lower()
        assets = ["bitcoin", "btc", "ethereum", "eth", "solana", "sol", "crypto"]
        short_kw = ["up or down", "up/down", "5 min", "5-min", "5min", "next hour"]
        has_asset = any(a in q for a in assets)
        has_short = any(k in q for k in short_kw)
        crypto_short_rejected = has_asset and has_short and tte_hours <= 1
        print(f"Crypto 5min rejeitado: {crypto_short_rejected}")
        
        # Resultado final
        if volume_ok and spread_ok and tte_ok and category_ok and not crypto_short_rejected:
            print("✅ QUALIFICADO!")
            qualified_count += 1
        else:
            reasons = []
            if not volume_ok: reasons.append("volume")
            if not spread_ok: reasons.append("spread")
            if not tte_ok: reasons.append("TTE")
            if not category_ok: reasons.append("categoria")
            if crypto_short_rejected: reasons.append("crypto 5min")
            print(f"❌ REJEITADO: {', '.join(reasons)}")
        
        if i >= 10:  # Limitar a 10 mercados para debug
            break
    
    print(f"\n=== RESUMO ===")
    print(f"Mercados qualificados: {qualified_count}/{min(len(markets), 11)}")

if __name__ == "__main__":
    debug_markets_v3()