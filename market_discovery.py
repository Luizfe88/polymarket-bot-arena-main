import json
import logging
import time
import argparse
import requests
from datetime import datetime, timedelta, timezone

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def fetch_all_markets(max_pages=20):
    """Busca mercados ativos, priorizando futuros"""
    all_markets = []
    page = 0

    try:
        logging.info("Fetching active markets from Gamma Markets API...")

        now = datetime.now(timezone.utc)
        # Buscar mercados que ainda não expiraram (a partir de hoje)
        start_date = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        future_date = (now + timedelta(days=180)).strftime("%Y-%m-%dT%H:%M:%SZ")

        while page < max_pages:
            url = "https://gamma-api.polymarket.com/markets"
            params = {
                "limit": 100,
                "offset": page * 100,
                "endDateMin": start_date,  # Mercados futuros
                "endDateMax": future_date,
                "active": "true",
                "closed": "false",
                "archived": "false",
                "orderBy": "liquidity",  # Ordenar por liquidez atual
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

        logging.info(f"Successfully fetched a total of {len(all_markets)} active markets from Gamma API.")
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
    """Rejeita mercados de crypto com janelas muito curtas (5min)"""
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

def _map_category_to_priority(category, question=''):
    """Mapeia categorias do Polymarket para nossas categorias prioritárias"""
    # Se não houver categoria ou for "unknown", inferir pela pergunta
    if not category or category == "unknown":
        question_lower = question.lower() if question else ''
        
        # FINANCEIROS/MACRO (PRIORIDADE MÁXIMA)
        if any(word in question_lower for word in [
            'fed', 'federal reserve', 'interest rate', 'inflation', 'gdp', 'unemployment', 'recession',
            'stock market', 'dow jones', 'nasdaq', 'sp500', 's&p 500', 'oil', 'gold', 'silver',
            'dollar', 'euro', 'yuan', 'trade war', 'tariff', 'bond', 'yield', 'treasury', 'fomc',
            'rate', 'economic', 'economy', 'market crash', 'bull market', 'bear market', 'deflation',
            'quantitative easing', 'qe', 'mortgage', 'housing', 'real estate', 'commodity', 'forex',
            'currency', 'exchange rate', 'central bank', 'monetary', 'fiscal', 'budget', 'debt',
            'stock', 'shares', 'equity', 'dividend', 'earnings', 'revenue', 'profit', 'loss'
        ]):
            return "finance"
        
        # Política
        elif any(word in question_lower for word in ['trump', 'biden', 'election', 'president', 'senate', 'house', 'republican', 'democrat', 'vote', 'candidate', 'primary', 'impeach', 'resign', 'minister', 'prime minister', 'parliament', 'congress']):
            return "politics"
        
        # Crypto
        elif any(word in question_lower for word in ['bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'cryptocurrency', 'blockchain', 'defi', 'nft']):
            return "crypto"
        
        # Esportes
        elif any(word in question_lower for word in ['nba', 'nfl', 'mlb', 'soccer', 'football', 'basketball', 'baseball', 'champions league', 'premier league', 'la liga', 'serie a', 'bundesliga', 'world cup', 'olympics', 'mvp', 'win', 'champion', 'tournament', 'masters', 'golf']):
            return "sports"
        
        # Tecnologia
        elif any(word in question_lower for word in ['gpt', 'ai', 'artificial intelligence', 'tesla', 'spacex', 'meta', 'facebook', 'google', 'apple', 'microsoft', 'amazon', 'tech', 'technology', 'silicon valley', 'startup']):
            return "tech"
        
        # Geopolítica/Guerra (muitas vezes categorizada como política)
        elif any(word in question_lower for word in ['war', 'invasion', 'china', 'russia', 'ukraine', 'taiwan', 'ceasefire', 'peace', 'nato', 'un', 'security council']):
            return "politics"
        
        return "unknown"
    
    category = category.lower()
    
    # Mapeamento direto - FINANCEIROS PRIMEIRO
    if "finance" in category or "financial" in category or "economic" in category or "economy" in category:
        return "finance"
    elif "macro" in category or "markets" in category or "trading" in category:
        return "finance"
    elif "politics" in category or "us-politics" in category or "election" in category:
        return "politics"
    elif "crypto" in category or "bitcoin" in category or "ethereum" in category:
        return "crypto"
    elif "sports" in category or "sport" in category:
        return "sports"
    elif "tech" in category or "technology" in category:
        return "tech"
    
    # Categorias que podem conter política
    elif "affairs" in category or "news" in category or "current" in category:
        return "politics"
    
    # Categorias que podem conter tech
    elif "business" in category or "companies" in category:
        return "tech"
    
    # Categorias que podem conter macro (agora mapeadas para finance)
    elif "economy" in category or "macro" in category:
        return "finance"
    
    return category

def filter_markets(markets):
    """Filtra mercados com base em whitelist/blacklist de texto - apenas ativos financeiros reais"""
    qualified_markets = []
    now = datetime.now(timezone.utc)

    # Usar valores do config
    min_volume = getattr(config, "MIN_MARKET_VOLUME", 50000)
    max_spread = getattr(config, "MAX_MARKET_SPREAD", 0.05)
    min_liquidity = getattr(config, "MIN_LIQUIDITY", 0.0)

    # Definir whitelist e blacklist baseadas em texto
    whitelist_crypto = ["bitcoin", "btc", "ethereum", "eth", "solana", "sol"]
    whitelist_macro = ["fed", "inflation", "interest rate", "cpi", "gdp", "recession", "treasury"]
    whitelist_tradfi = ["s&p 500", "nasdaq", "dow jones", "stock", "ipo", "oil", "gold", "silver", "eur", "usd"]

    # LISTA NEGRA: Se tiver uma destas, morre na hora (Segurança extra)
    BLOCK_KEYWORDS = [
        # Política
        'trump', 'biden', 'harris', 'election', 'poll', 'vote',
        # Desporto
        'nba', 'nfl', 'nhl', 'mlb', 'soccer', 'cup', 'game',
        # Pop Culture (Onde o Ethan Hawke mora)
        'actor', 'oscar', 'academy award', 'best picture',
        # Macro (Se quiser tirar os Juros do Fed que travam o RSI)
        'fed rate', 'cut', 'happen in', 'recession'
    ]

    logging.info("Filtering markets with financial whitelist/blacklist criteria:")
    logging.info(f"  - Min Volume: ${min_volume:,.0f}")
    logging.info(f"  - Max Spread: {max_spread:.2%}")
    logging.info(f"  - Min Liquidity: ${min_liquidity:,.0f}")

    for market in markets:
        try:
            volume = float(market.get("volume", 0))
            liquidity = market.get("liquidity")
            if liquidity is None:
                liquidity = market.get("liquidityNum")
            if liquidity is None:
                liquidity = market.get("liquidityClob")
            try:
                liquidity = float(liquidity or 0)
            except Exception:
                liquidity = 0.0
            
            end_date_str = market.get("endDate")
            question = market.get("question", "").lower()

            if not end_date_str:
                continue

            # Aplicar filtros de qualidade básicos primeiro
            spread = calculate_spread(market)
            
            volume_ok = volume >= min_volume
            liquidity_ok = liquidity >= min_liquidity
            spread_ok = spread <= max_spread
            
            if not (volume_ok and liquidity_ok and spread_ok):
                continue

            # Aplicar blacklist de segurança (rejeitar imediatamente se contiver)
            if any(term in question for term in BLOCK_KEYWORDS):
                logging.debug(f"  [REJECTED] blacklist match: {market.get('question')}")
                continue

            # Verificar whitelist - precisa ter pelo menos um termo financeiro
            whitelist_terms = whitelist_crypto + whitelist_macro + whitelist_tradfi
            has_financial_term = any(term in question for term in whitelist_terms)
            
            if not has_financial_term:
                logging.debug(f"  [REJECTED] no financial whitelist match: {market.get('question')}")
                continue

            # Se passou todos os filtros, adicionar à lista qualificada
            market["mapped_category"] = "financial_asset"
            qualified_markets.append(market)
            logging.info(f"  [QUALIFIED] {market.get('question')} (Vol ${volume:,.0f}, Liq ${liquidity:,.0f}, Spread {spread:.2%})")

        except Exception as e:
            logging.warning(f"Could not process market {market.get('id', 'N/A')}: {e}")
            continue

    # Ordenar por liquidez decrescente
    qualified_markets.sort(key=lambda x: float(x.get("liquidity", 0) or 0), reverse=True)
    
    logging.info(f"Found {len(qualified_markets)} qualified financial markets out of {len(markets)}.")
    return qualified_markets

def save_qualified_markets(markets, filename="qualified_markets.json"):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(markets, f, indent=2)
        logging.info(f"Successfully saved {len(markets)} qualified markets to {filename}")
    except Exception as e:
        logging.error(f"Failed to save qualified markets to {filename}: {e}")

def run_scan_and_save():
    all_markets = fetch_all_markets()
    if not all_markets:
        logging.error("No markets were fetched. Cannot proceed with filtering.")
        return False
    qualified = filter_markets(all_markets)
    save_qualified_markets(qualified)
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Market Discovery v3.0")
    parser.add_argument("--scan", action="store_true", help="Executa uma varredura única e salva mercados qualificados")
    parser.add_argument("--watch", action="store_true", help="Executa automaticamente a cada 60 minutos")
    parser.add_argument("--interval", type=int, default=3600, help="Intervalo em segundos para modo watch")
    args = parser.parse_args()

    logging.info("Starting Polymarket Bot Arena v3.0 - Market Discovery Engine")

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
