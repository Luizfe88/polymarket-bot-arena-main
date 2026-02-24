import json
import logging
import time
import argparse
import requests
from datetime import datetime, timedelta, timezone

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def fetch_future_markets(max_pages=5):
    """Busca apenas mercados futuros válidos"""
    all_markets = []
    page = 0

    try:
        logging.info("Fetching future markets from Gamma Markets API...")

        now = datetime.now(timezone.utc)
        # Buscar mercados que começam a partir de amanhã
        tomorrow = (now + timedelta(days=1)).isoformat()
        # Limite de 45 dias no futuro
        future_date = (now + timedelta(days=45)).isoformat()

        while page < max_pages:
            url = "https://gamma-api.polymarket.com/markets"
            params = {
                "limit": 100,
                "offset": page * 100,
                "endDateMin": tomorrow,  # Mercados futuros
                "endDateMax": future_date,
                "active": "true",
                "closed": "false",
                "orderBy": "volume",  # Ordenar por volume
                "orderDirection": "desc"  # Maior volume primeiro
            }

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            response = requests.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()

            markets_on_page = response.json()
            if not markets_on_page:
                logging.info("No more markets found. Stopping.")
                break

            all_markets.extend(markets_on_page)
            logging.info(f"Fetched {len(markets_on_page)} markets. Total fetched: {len(all_markets)}")

            if len(markets_on_page) < 100:
                logging.info("Reached end of available markets.")
                break

            page += 1

        logging.info(f"Successfully fetched a total of {len(all_markets)} future markets from Gamma API.")
        return all_markets

    except Exception as e:
        logging.error(f"Failed to fetch markets from Gamma API: {e}")
        return []

def calculate_spread(market):
    """Calcula o spread do mercado"""
    try:
        best_bid = float(market.get("bestBid", 0))
        best_ask = float(market.get("bestAsk", 0))
        if best_bid > 0 and best_ask > 0:
            return (best_ask - best_bid) / best_ask
        return 1.0
    except Exception:
        return 1.0

def _is_rejected_short_crypto(market, now):
    """Rejeita mercados de crypto com janelas muito curtas"""
    q = (market.get("question") or "").lower()
    assets = ["bitcoin", "btc", "ethereum", "eth", "solana", "sol", "crypto"]
    short_kw = ["up or down", "up/down", "5 min", "5-min", "5min", "next hour", "next 60 minutes"]
    has_asset = any(a in q for a in assets)
    has_short = any(k in q for k in short_kw)
    end_date_str = market.get("endDate")
    if not end_date_str:
        return False
    try:
        end_dt = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
    except Exception:
        return False
    tte_seconds = max(0, int((end_dt - now).total_seconds()))
    return has_asset and has_short and tte_seconds <= 3600

def _map_category_to_priority(category):
    """Mapeia categorias do Polymarket para nossas categorias prioritárias"""
    if not category:
        return "unknown"
    
    category = category.lower()
    
    # Mapeamento direto
    if "politics" in category or "us-politics" in category or "election" in category:
        return "politics"
    elif "crypto" in category or "bitcoin" in category or "ethereum" in category:
        return "crypto"
    elif "sports" in category or "sport" in category:
        return "sports"
    elif "tech" in category or "technology" in category:
        return "tech"
    elif "economy" in category or "macro" in category or "finance" in category:
        return "macro"
    
    # Categorias que podem conter política
    elif "affairs" in category or "news" in category or "current" in category:
        return "politics"
    
    # Categorias que podem conter tech
    elif "business" in category or "companies" in category:
        return "tech"
    
    # Categorias que podem conter macro
    elif "markets" in category or "trading" in category:
        return "macro"
    
    return category

def filter_markets_v3(markets):
    """Filtra mercados com critérios v3.0 otimizados"""
    qualified_markets = []
    now = datetime.now(timezone.utc)

    # Critérios mais flexíveis para conseguir mercados válidos
    min_volume = getattr(config, "MIN_MARKET_VOLUME", 50000)  # Reduzido de 150k para 50k
    max_spread = getattr(config, "MAX_MARKET_SPREAD", 0.05)  # Aumentado de 2.5% para 5%
    min_hours = getattr(config, "MIN_TIME_TO_RESOLUTION", 6)
    max_hours = getattr(config, "MAX_TIME_TO_RESOLUTION", 45 * 24)
    priority_categories = getattr(config, "PRIORITY_CATEGORIES", ["politics", "crypto", "sports", "macro", "tech"])

    logging.info("Filtering markets with the following criteria:")
    logging.info(f"  - Min Volume: ${min_volume:,.0f}")
    logging.info(f"  - Max Spread: {max_spread:.2%}")
    logging.info(f"  - Time to Resolution: {min_hours}h - {int(max_hours / 24)}d")
    logging.info(f"  - Priority Categories: {priority_categories}")

    for market in markets:
        try:
            volume = float(market.get("volume", 0))
            raw_category = market.get("category", "unknown")
            end_date_str = market.get("endDate")
            is_active = bool(market.get("active", False))

            if not end_date_str or not is_active:
                continue

            # Rejeitar mercados de crypto de curto prazo
            if _is_rejected_short_crypto(market, now):
                logging.debug(f"  [REJECTED] short-window crypto: {market.get('question')}")
                continue

            end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
            time_to_resolution = end_date - now
            spread = calculate_spread(market)
            
            # Mapear categoria
            mapped_category = _map_category_to_priority(raw_category)

            logging.debug(
                f"Market: {market.get('question')} | Volume: ${volume:,.0f} | Spread: {spread:.4f} | "
                f"TTE: {time_to_resolution} | Category: {raw_category} -> {mapped_category} | Active: {is_active}"
            )

            # Verificar se o mercado está dentro dos critérios
            volume_ok = volume >= min_volume
            spread_ok = spread <= max_spread
            tte_ok = timedelta(hours=min_hours) <= time_to_resolution <= timedelta(hours=max_hours)
            category_ok = not priority_categories or mapped_category in priority_categories

            if volume_ok and spread_ok and tte_ok and category_ok:
                # Adicionar categoria mapeada ao mercado para referência
                market["mapped_category"] = mapped_category
                qualified_markets.append(market)
                logging.info(f"  [QUALIFIED] {market.get('question')} (Vol ${volume:,.0f}, Spread {spread:.2%}, Cat {mapped_category})")
            else:
                # Log detalhado do porquê foi rejeitado
                reasons = []
                if not volume_ok: reasons.append(f"volume ${volume:,.0f} < ${min_volume:,.0f}")
                if not spread_ok: reasons.append(f"spread {spread:.2%} > {max_spread:.2%}")
                if not tte_ok: reasons.append(f"TTE {time_to_resolution}")
                if not category_ok: reasons.append(f"category {mapped_category} not in {priority_categories}")
                logging.debug(f"  [REJECTED] {reasons}")

        except Exception as e:
            logging.warning(f"Could not process market {market.get('id', 'N/A')}: {e}")
            continue

    logging.info(f"Found {len(qualified_markets)} qualified markets out of {len(markets)}.")
    return qualified_markets

def save_qualified_markets(markets, filename="qualified_markets.json"):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(markets, f, indent=2)
        logging.info(f"Successfully saved {len(markets)} qualified markets to {filename}")
    except Exception as e:
        logging.error(f"Failed to save qualified markets to {filename}: {e}")

def run_scan_and_save():
    all_markets = fetch_future_markets()
    if not all_markets:
        logging.error("No markets were fetched. Cannot proceed with filtering.")
        return False
    qualified = filter_markets_v3(all_markets)
    save_qualified_markets(qualified)
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Market Discovery v3.0 - Otimizado")
    parser.add_argument("--scan", action="store_true", help="Executa uma varredura única e salva mercados qualificados")
    parser.add_argument("--watch", action="store_true", help="Executa automaticamente a cada 60 minutos")
    parser.add_argument("--interval", type=int, default=3600, help="Intervalo em segundos para modo watch")
    args = parser.parse_args()

    logging.info("Starting Polymarket Bot Arena v3.0 - Market Discovery Engine (Otimizado)")

    if args.watch:
        while True:
            ok = run_scan_and_save()
            if not ok:
                logging.info("Scan failed or no markets fetched.")
            logging.info(f"Sleeping for {args.interval} seconds before next scan...")
            time.sleep(args.interval)
    else:
        run_scan_and_save()
        logging.info("Market Discovery Engine finished.")