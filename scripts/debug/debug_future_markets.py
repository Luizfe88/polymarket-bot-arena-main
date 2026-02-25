import json
import logging
import time
import argparse
import requests
from datetime import datetime, timedelta, timezone

import config

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

def debug_future_markets():
    """Debug detalhado dos mercados futuros"""
    
    try:
        logging.info("=== DEBUG FUTURE MARKETS v3.0 ===")
        
        now = datetime.now(timezone.utc)
        tomorrow = (now + timedelta(days=1)).isoformat()
        future_date = (now + timedelta(days=45)).isoformat()
        
        logging.info(f"Data atual: {now}")
        logging.info(f"Data mínima (amanhã): {tomorrow}")
        logging.info(f"Data máxima (45 dias): {future_date}")
        
        # Buscar apenas 20 mercados futuros para debug
        url = "https://gamma-api.polymarket.com/markets"
        params = {
            "limit": 20,
            "offset": 0,
            "endDateMin": tomorrow,
            "endDateMax": future_date,
            "active": "true",
            "closed": "false",
            "orderBy": "volume",
            "orderDirection": "desc"
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        markets = response.json()
        
        logging.info(f"Fetched {len(markets)} future markets for analysis")
        
        # Critérios do config
        min_volume = getattr(config, "MIN_MARKET_VOLUME", 50000)
        max_spread = getattr(config, "MAX_MARKET_SPREAD", 0.05)
        min_hours = getattr(config, "MIN_TIME_TO_RESOLUTION", 6)
        max_hours = getattr(config, "MAX_TIME_TO_RESOLUTION", 45 * 24)
        priority_categories = getattr(config, "PRIORITY_CATEGORIES", ["politics", "crypto", "sports", "macro", "tech"])
        
        logging.info(f"\n=== CRITÉRIOS DE FILTRAGEM ===")
        logging.info(f"Volume mínimo: ${min_volume:,.0f}")
        logging.info(f"Spread máximo: {max_spread:.2%}")
        logging.info(f"Tempo para resolução: {min_hours}h - {int(max_hours/24)}d")
        logging.info(f"Categorias prioritárias: {priority_categories}")
        
        qualified_count = 0
        
        for i, market in enumerate(markets):
            try:
                logging.info(f"\n=== MERCADO FUTURO {i+1} ===")
                
                # Informações básicas
                question = market.get("question", "N/A")
                volume = float(market.get("volume", 0))
                category = market.get("category", "unknown")
                end_date_str = market.get("endDate")
                is_active = bool(market.get("active", False))
                is_closed = bool(market.get("closed", False))
                
                logging.info(f"Questão: {question}")
                logging.info(f"Volume: ${volume:,.0f}")
                logging.info(f"Categoria original: {category}")
                logging.info(f"Ativo: {is_active}")
                logging.info(f"Fechado: {is_closed}")
                
                if not end_date_str:
                    logging.info("❌ REJEITADO: Sem data de término")
                    continue
                
                # Calcular TTE
                end_dt = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                tte_seconds = max(0, int((end_dt - now).total_seconds()))
                tte_hours = tte_seconds / 3600
                tte_days = tte_hours / 24
                
                logging.info(f"Data de término: {end_dt}")
                logging.info(f"Tempo até resolução: {tte_hours:.1f}h ({tte_days:.1f}d)")
                
                if tte_hours < 0:
                    logging.info("❌ REJEITADO: Mercado já expirou")
                    continue
                
                # Calcular spread
                best_bid = float(market.get("bestBid", 0))
                best_ask = float(market.get("bestAsk", 0))
                
                if best_bid > 0 and best_ask > 0:
                    spread = (best_ask - best_bid) / best_ask
                else:
                    spread = 1.0
                
                logging.info(f"Best Bid: {best_bid}")
                logging.info(f"Best Ask: {best_ask}")
                logging.info(f"Spread: {spread:.4f} ({spread:.2%})")
                
                # Verificar se é crypto de curto prazo
                q = question.lower()
                assets = ["bitcoin", "btc", "ethereum", "eth", "solana", "sol", "crypto"]
                short_kw = ["up or down", "up/down", "5 min", "5-min", "5min", "next hour", "next 60 minutes"]
                has_asset = any(a in q for a in assets)
                has_short = any(k in q for k in short_kw)
                is_short_crypto = has_asset and has_short and tte_seconds <= 3600
                
                if is_short_crypto:
                    logging.info(f"⚠️  DETECTADO: Crypto de curto prazo (asset: {has_asset}, short: {has_short})")
                
                # Mapear categoria
                mapped_category = category.lower()
                if "politics" in mapped_category or "us-politics" in mapped_category or "election" in mapped_category:
                    mapped_category = "politics"
                elif "crypto" in mapped_category or "bitcoin" in mapped_category or "ethereum" in mapped_category:
                    mapped_category = "crypto"
                elif "sports" in mapped_category or "sport" in mapped_category:
                    mapped_category = "sports"
                elif "tech" in mapped_category or "technology" in mapped_category:
                    mapped_category = "tech"
                elif "economy" in mapped_category or "macro" in mapped_category or "finance" in mapped_category:
                    mapped_category = "macro"
                elif "affairs" in mapped_category or "news" in mapped_category or "current" in mapped_category:
                    mapped_category = "politics"
                elif "business" in mapped_category or "companies" in mapped_category:
                    mapped_category = "tech"
                elif "markets" in mapped_category or "trading" in mapped_category:
                    mapped_category = "macro"
                
                logging.info(f"Categoria mapeada: {mapped_category}")
                
                # Verificar critérios
                volume_ok = volume >= min_volume
                spread_ok = spread <= max_spread
                tte_ok = min_hours <= tte_hours <= max_hours
                category_ok = mapped_category in priority_categories
                
                logging.info(f"Critérios:")
                logging.info(f"  Volume OK: {volume_ok} (${volume:,.0f} >= ${min_volume:,.0f})")
                logging.info(f"  Spread OK: {spread_ok} ({spread:.4f} <= {max_spread:.4f})")
                logging.info(f"  TTE OK: {tte_ok} ({min_hours}h <= {tte_hours:.1f}h <= {max_hours}h)")
                logging.info(f"  Category OK: {category_ok} ({mapped_category} in {priority_categories})")
                logging.info(f"  Short crypto: {is_short_crypto}")
                
                if volume_ok and spread_ok and tte_ok and category_ok and not is_short_crypto:
                    logging.info("✅ QUALIFICADO!")
                    qualified_count += 1
                else:
                    reasons = []
                    if not volume_ok: reasons.append("volume")
                    if not spread_ok: reasons.append("spread")
                    if not tte_ok: reasons.append("TTE")
                    if not category_ok: reasons.append("category")
                    if is_short_crypto: reasons.append("crypto_5min")
                    logging.info(f"❌ REJEITADO: {', '.join(reasons)}")
                
            except Exception as e:
                logging.error(f"Erro ao processar mercado {i+1}: {e}")
                continue
        
        logging.info(f"\n=== RESUMO ===")
        logging.info(f"Total de mercados futuros analisados: {len(markets)}")
        logging.info(f"Mercados qualificados: {qualified_count}")
        
        return qualified_count > 0
        
    except Exception as e:
        logging.error(f"Erro geral: {e}")
        return False

if __name__ == "__main__":
    debug_future_markets()