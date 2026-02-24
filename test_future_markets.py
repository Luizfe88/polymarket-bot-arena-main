#!/usr/bin/env python3
"""
Buscar mercados futuros para teste
"""

import json
import logging
import requests
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_future_markets():
    """Busca mercados que ainda não expiraram"""
    
    now = datetime.now(timezone.utc)
    future_markets = []
    
    logging.info("Buscando mercados futuros...")
    
    # Buscar com parâmetros diferentes
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "limit": 100,
        "offset": 0,
        "orderBy": "endDate",
        "orderDirection": "asc",  # Mercados mais próximos primeiro
        "active": "true"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        markets = response.json()
        
        logging.info(f"Encontrados {len(markets)} mercados")
        
        future_count = 0
        for i, market in enumerate(markets):
            question = market.get("question", "N/A")
            end_date_str = market.get("endDate")
            volume = float(market.get("volume", 0))
            
            if end_date_str:
                try:
                    end_dt = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                    time_to_resolution = end_dt - now
                    hours_to_resolution = time_to_resolution.total_seconds() / 3600
                    
                    if hours_to_resolution > 0:  # Mercado ainda não expirou
                        future_count += 1
                        logging.info(f"\nMercado Futuro {future_count}:")
                        logging.info(f"  Questão: {question}")
                        logging.info(f"  Volume: ${volume:,.0f}")
                        logging.info(f"  Data de término: {end_date_str}")
                        logging.info(f"  Horas até resolução: {hours_to_resolution:.1f}")
                        
                        future_markets.append(market)
                        
                        if future_count >= 5:  # Limitar para não poluir o log
                            break
                            
                except Exception as e:
                    logging.error(f"Erro ao processar data: {e}")
            
            if i >= 20:  # Limitar busca
                break
        
        logging.info(f"\nTotal de mercados futuros encontrados: {future_count}")
        
        if future_count == 0:
            logging.warning("Nenhum mercado futuro encontrado!")
            
            # Mostrar alguns mercados para debug
            logging.info("\nPrimeiros 3 mercados retornados pela API:")
            for i, market in enumerate(markets[:3]):
                question = market.get("question", "N/A")
                end_date_str = market.get("endDate")
                volume = float(market.get("volume", 0))
                
                if end_date_str:
                    try:
                        end_dt = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                        time_to_resolution = end_dt - now
                        hours_to_resolution = time_to_resolution.total_seconds() / 3600
                        
                        logging.info(f"\nMercado {i+1}:")
                        logging.info(f"  Questão: {question}")
                        logging.info(f"  Volume: ${volume:,.0f}")
                        logging.info(f"  Data de término: {end_date_str}")
                        logging.info(f"  Horas até resolução: {hours_to_resolution:.1f}")
                        
                    except Exception as e:
                        logging.error(f"Erro ao processar data: {e}")
        
        return future_markets
        
    except Exception as e:
        logging.error(f"Erro ao buscar mercados: {e}")
        return []

if __name__ == "__main__":
    fetch_future_markets()