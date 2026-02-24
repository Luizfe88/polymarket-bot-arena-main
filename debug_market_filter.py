#!/usr/bin/env python3
"""
Debug detalhado do filtro de mercados para identificar o problema
"""

import json
import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from datetime import datetime, timedelta, timezone
import requests

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def calculate_spread(market):
    """Calcula o spread do mercado"""
    try:
        outcomes = market.get('outcomes', [])
        if len(outcomes) < 2:
            return 1.0
        
        prices = []
        for outcome in outcomes:
            price = float(outcome.get('price', 0))
            if price > 0:
                prices.append(price)
        
        if len(prices) < 2:
            return 1.0
            
        prices.sort()
        best_bid = prices[-1]  # Maior preço (melhor bid)
        best_ask = prices[0]   # Menor preço (melhor ask)
        
        if best_bid <= 0 or best_ask <= 0:
            return 1.0
            
        spread = abs(best_ask - best_bid)
        return spread
        
    except Exception as e:
        logging.error(f"Erro ao calcular spread: {e}")
        return 1.0

def debug_market_filter():
    """Debug detalhado do filtro de mercados"""
    
    # Carregar configurações
    min_volume = getattr(config, "MIN_MARKET_VOLUME", 30000)
    max_spread = getattr(config, "MAX_MARKET_SPREAD", 0.25)
    min_hours = getattr(config, "MIN_TIME_TO_RESOLUTION", 4)
    max_hours = getattr(config, "MAX_TIME_TO_RESOLUTION", 2160)
    priority_categories = getattr(config, "PRIORITY_CATEGORIES", [])
    
    logging.info("=== DEBUG MARKET FILTER ===")
    logging.info(f"Min Volume: ${min_volume:,}")
    logging.info(f"Max Spread: {max_spread:.2%}")
    logging.info(f"Time to Resolution: {min_hours}h - {max_hours}h")
    logging.info(f"Priority Categories: {priority_categories}")
    logging.info("=" * 50)
    
    # Buscar alguns mercados para teste
    try:
        url = "https://gamma-api.polymarket.com/markets"
        params = {
            "limit": 10,
            "offset": 0,
            "active": "true",
            "orderBy": "volume",
            "orderDirection": "desc"
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        markets = response.json()
        
        logging.info(f"Fetched {len(markets)} markets for detailed analysis")
        
        now = datetime.now(timezone.utc)
        qualified_count = 0
        
        for i, market in enumerate(markets):
            logging.info(f"\n=== MARKET {i+1} ===")
            
            # Informações básicas
            question = market.get("question", "N/A")
            volume = float(market.get("volume", 0))
            category = market.get("category", "unknown")
            end_date_str = market.get("endDate")
            is_active = bool(market.get("active", False))
            market_id = market.get("id", "N/A")
            
            logging.info(f"ID: {market_id}")
            logging.info(f"Question: {question}")
            logging.info(f"Volume: ${volume:,.0f}")
            logging.info(f"Category: {category}")
            logging.info(f"Active: {is_active}")
            logging.info(f"End Date: {end_date_str}")
            
            # Verificar se tem end_date
            if not end_date_str:
                logging.info("❌ REJECTED: No end date")
                continue
                
            # Calcular tempo para resolução
            try:
                end_dt = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                time_to_resolution = end_dt - now
                hours_to_resolution = time_to_resolution.total_seconds() / 3600
                logging.info(f"Time to Resolution: {hours_to_resolution:.1f} hours")
            except Exception as e:
                logging.info(f"❌ REJECTED: Invalid end date format: {e}")
                continue
            
            # Verificar volume
            volume_ok = volume >= min_volume
            logging.info(f"Volume OK: {volume_ok} (${volume:,.0f} >= ${min_volume:,})")
            
            # Calcular spread
            spread = calculate_spread(market)
            spread_ok = spread <= max_spread
            logging.info(f"Spread: {spread:.4f} ({spread:.2%})")
            logging.info(f"Spread OK: {spread_ok} ({spread:.2%} <= {max_spread:.2%})")
            
            # Verificar tempo
            time_ok = min_hours <= hours_to_resolution <= max_hours
            logging.info(f"Time OK: {time_ok} ({min_hours} <= {hours_to_resolution:.1f} <= {max_hours})")
            
            # Verificar categoria
            if priority_categories:
                category_ok = category.lower() in [cat.lower() for cat in priority_categories]
            else:
                category_ok = True
            logging.info(f"Category OK: {category_ok} (category: {category}, allowed: {priority_categories})")
            
            # Verificar se é mercado de crypto de curto prazo
            question_lower = question.lower()
            is_crypto_short = False
            crypto_keywords = ['bitcoin', 'ethereum', 'crypto', 'btc', 'eth']
            short_keywords = ['next hour', 'next 60 minutes', '5 min', 'next 30 minutes']
            
            if any(keyword in question_lower for keyword in crypto_keywords) and any(keyword in question_lower for keyword in short_keywords):
                is_crypto_short = True
                logging.info("❌ REJECTED: Short-term crypto market")
            
            # Resultado final
            qualified = volume_ok and spread_ok and time_ok and category_ok and not is_crypto_short
            if qualified:
                logging.info("✅ QUALIFIED")
                qualified_count += 1
            else:
                reasons = []
                if not volume_ok: reasons.append("volume")
                if not spread_ok: reasons.append("spread")
                if not time_ok: reasons.append("time")
                if not category_ok: reasons.append("category")
                if is_crypto_short: reasons.append("crypto-short")
                logging.info(f"❌ REJECTED: {', '.join(reasons)}")
            
            if i >= 4:  # Limitar a 5 mercados para não poluir o log
                break
                
        logging.info(f"\n=== RESULTADO FINAL ===")
        logging.info(f"Mercados analisados: {min(5, len(markets))}")
        logging.info(f"Mercados qualificados: {qualified_count}")
        
    except Exception as e:
        logging.error(f"Erro ao buscar mercados: {e}")
        return

if __name__ == "__main__":
    debug_market_filter()