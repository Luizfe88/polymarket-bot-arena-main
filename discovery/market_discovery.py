import os
import logging
import json
import base64
import time
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)

class MarketDiscovery:
    """
    Motor de descoberta de mercados consolidado (v3.1+)
    Usa Gamma API para mercados longos + CLOB API para Up or Down de curto prazo.
    """

    def __init__(self,
                 enable_crypto: bool = True,
                 enable_finance: bool = True,
                 enable_politics: bool = False,
                 enable_sports: bool = False,
                 min_volume: float = None,
                 min_liquidity: float = None,
                 max_spread: float = None):

        self.enable_crypto   = enable_crypto
        self.enable_finance  = enable_finance
        self.enable_politics = enable_politics
        self.enable_sports   = enable_sports

        self.min_volume    = min_volume    if min_volume    is not None else getattr(config, "MIN_MARKET_VOLUME",  50000)
        self.min_liquidity = min_liquidity if min_liquidity is not None else getattr(config, "MIN_LIQUIDITY",       0.0)
        self.max_spread    = max_spread    if max_spread    is not None else getattr(config, "MAX_MARKET_SPREAD",   0.05)

        self.KEYWORDS = {
            "crypto": [
                "bitcoin", "btc", "ethereum", "eth", "solana", "sol",
                "crypto", "token", "nft", "defi", "xrp", "ripple",
                "bnb", "avax", "doge", "matic", "up or down", "updown"
            ],
            "finance": ["fed", "inflation", "interest rate", "cpi", "gdp", "recession",
                        "treasury", "s&p 500", "nasdaq", "dow jones", "stock", "ipo",
                        "oil", "gold", "silver", "eur", "usd", "yield"],
            "politics": ["trump", "biden", "harris", "election", "poll", "vote",
                         "senate", "house", "president", "democrat", "republican"],
            "sports": ["nba", "nfl", "nhl", "mlb", "soccer", "cup",
                       "game", "league", "tournament", "champion"]
        }

        self.BLOCK_KEYWORDS = [
            "israel", "gaza", "hamas", "ukraine", "russia", "war", "death", "kill",
            "trump", "biden", "harris", "election", "president", "senate", "house",
            "taylor swift", "kanye", "drake", "movie", "box office", "song", "album",
            "weather", "temperature", "earthquake", "hurricane"
        ]

    # ------------------------------------------------------------------
    # CLOB API — mercados Up or Down de curto prazo
    # ------------------------------------------------------------------

    def _normalize_clob_market(self, m: Dict[str, Any]) -> Dict[str, Any]:
        """Normaliza campos da CLOB API para o formato do filtro"""
        m["slug"]    = m.get("market_slug", m.get("slug", ""))
        m["endDate"] = m.get("end_date_iso", "")
        m["active"]  = m.get("active", False)
        m["closed"]  = m.get("closed", False)
        m.setdefault("volume", 0)
        m.setdefault("liquidity", 0)

        # Spread implícito via preços dos tokens (Up + Down deve somar ~1.0)
        tokens = m.get("tokens", [])
        if len(tokens) == 2:
            try:
                p0 = float(tokens[0].get("price", 0) or 0)
                p1 = float(tokens[1].get("price", 0) or 0)
                total = p0 + p1
                m["spread"] = abs(1.0 - total) if total > 0 else 1.0
            except Exception:
                m["spread"] = 1.0
        else:
            m["spread"] = 1.0

        return m

    def _find_active_clob_offset(self, headers: Dict) -> Optional[int]:
        """
        Busca binária para achar o offset com mercados Up or Down ativos.
        Em fev/2026 os mercados ficam por volta de offset 400k-600k.
        Usa busca binária para encontrar rapidamente (max ~10 requests).
        """
        # Primeiro acha o teto (último offset com dados válidos)
        lo, hi = 300000, 1000000
        last_valid = None

        # Passo 1: acha o fim dos dados com passos grandes
        logger.info("  Localizando limite superior dos dados CLOB...")
        for offset in range(300000, 1000000, 100000):
            cursor = base64.b64encode(str(offset).encode()).decode()
            try:
                r = requests.get("https://clob.polymarket.com/markets", params={
                    "limit": 10, "next_cursor": cursor
                }, headers=headers, timeout=10)
                data = r.json().get("data", []) if r.status_code == 200 else []
                if not data:
                    hi = offset
                    logger.info(f"  Fim dos dados em offset ~{offset}")
                    break
                last_valid = offset
                lo = offset
            except Exception:
                break

        if last_valid is None:
            return None

        # Passo 2: busca binária entre lo e hi para achar mercados accepting_orders=True
        logger.info(f"  Busca binária entre {lo} e {hi}...")
        best = None
        for _ in range(12):  # max 12 iterações = suficiente para qualquer range
            mid = (lo + hi) // 2
            cursor = base64.b64encode(str(mid).encode()).decode()
            try:
                r = requests.get("https://clob.polymarket.com/markets", params={
                    "limit": 200, "next_cursor": cursor
                }, headers=headers, timeout=15)
                if r.status_code != 200:
                    hi = mid
                    continue
                data = r.json().get("data", [])
                if not data:
                    hi = mid
                    continue

                accepting = [m for m in data
                             if m.get("accepting_orders")
                             and "up or down" in (m.get("question") or "").lower()]
                logger.info(f"  Offset {mid}: {len(data)} mercados, {len(accepting)} up/down aceitando ordens")

                if accepting:
                    best = mid
                    hi = mid  # tenta achar ainda mais cedo
                else:
                    # Sem ativos aqui — pode estar antes ou depois
                    # Checa se os mercados são do passado ou futuro pelo endDate
                    sample_date = data[0].get("end_date_iso", "") if data else ""
                    if sample_date and sample_date < datetime.now(timezone.utc).strftime("%Y-%m-%d"):
                        lo = mid  # mercados aqui são do passado, vai para frente
                    else:
                        hi = mid

            except Exception as e:
                logger.warning(f"  Busca binária erro offset {mid}: {e}")
                hi = mid

            if hi - lo < 1000:
                break

        # Se não achou com accepting_orders, retorna o melhor offset com dados recentes
        if best is None:
            best = lo
            logger.info(f"  Nenhum up/down ativo encontrado na busca binária, usando offset {best}")

        return best

    def fetch_clob_updown_markets(self) -> List[Dict[str, Any]]:
        """
        Busca mercados 'Up or Down' ativos na CLOB API.
        A Gamma API não indexa esses mercados — eles só existem aqui.
        """
        headers = {"User-Agent": "PolymarketBotArena/3.0"}
        found = []

        logger.info("Buscando mercados Up or Down na CLOB API...")

        start_offset = self._find_active_clob_offset(headers)
        if start_offset is None:
            logger.warning("  Não foi possível localizar offset ativo na CLOB. Tente ajustar probe_offsets.")
            return []

        logger.info(f"  Varrendo a partir do offset {start_offset}...")

        cursor = base64.b64encode(str(start_offset).encode()).decode()
        pages_scanned = 0
        MAX_PAGES = 8  # 8 * 1000 = 8000 mercados máximo

        while pages_scanned < MAX_PAGES:
            try:
                r = requests.get("https://clob.polymarket.com/markets", params={
                    "limit": 1000, "next_cursor": cursor
                }, headers=headers, timeout=20)
                if r.status_code != 200:
                    break
                resp = r.json()
                data = resp.get("data", [])
                next_cursor = resp.get("next_cursor", "")

                updown_active = [
                    m for m in data
                    if "up or down" in (m.get("question") or "").lower()
                    and m.get("accepting_orders", False)
                    and not m.get("closed", True)
                ]

                for m in updown_active:
                    found.append(self._normalize_clob_market(m))

                logger.info(f"  Página {pages_scanned+1}: {len(data)} mercados, {len(updown_active)} up/down aceitando ordens")

                if not next_cursor or next_cursor == cursor or not data:
                    break
                cursor = next_cursor
                pages_scanned += 1

            except Exception as e:
                logger.warning(f"  Erro ao coletar página CLOB: {e}")
                break

        logger.info(f"  Total Up or Down ativos (CLOB): {len(found)}")
        return found

    # ------------------------------------------------------------------
    # Gamma API — mercados de longo prazo
    # ------------------------------------------------------------------

    def fetch_active_markets(self, max_pages: int = 20) -> List[Dict[str, Any]]:
        """Busca mercados ativos: Gamma API (longo prazo) + CLOB API (Up or Down)"""
        all_markets = []
        page = 0
        headers = {"User-Agent": "PolymarketBotArena/3.0"}

        try:
            logger.info("Fetching active markets from Gamma Markets API...")
            now = datetime.now(timezone.utc)
            start_date  = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            future_date = (now + timedelta(days=180)).strftime("%Y-%m-%dT%H:%M:%SZ")

            while page < max_pages:
                url = "https://gamma-api.polymarket.com/markets"
                params = {
                    "limit": 100,
                    "offset": page * 100,
                    "endDateMin": start_date,
                    "endDateMax": future_date,
                    "active": "true",
                    "closed": "false",
                    "archived": "false",
                    "orderBy": "liquidity",
                    "orderDirection": "desc"
                }
                response = requests.get(url, params=params, headers=headers, timeout=15)
                response.raise_for_status()
                data = response.json()
                if not data:
                    break
                all_markets.extend(data)
                if len(data) < 100:
                    break
                page += 1

            logger.info(f"Gamma API: {len(all_markets)} mercados buscados.")

            # CLOB API — Up or Down de curto prazo
            if self.enable_crypto:
                clob_markets = self.fetch_clob_updown_markets()
                existing_slugs = {m.get("slug", "") for m in all_markets}
                added = 0
                for m in clob_markets:
                    slug = m.get("slug", "")
                    if slug not in existing_slugs:
                        all_markets.append(m)
                        existing_slugs.add(slug)
                        added += 1
                logger.info(f"CLOB: adicionados {added} mercados Up or Down.")

            logger.info(f"Successfully fetched {len(all_markets)} raw markets.")
            return all_markets

        except Exception as e:
            logger.error(f"Failed to fetch markets: {e}")
            return []

    # ------------------------------------------------------------------
    # Classificação e filtros
    # ------------------------------------------------------------------

    def calculate_spread(self, market: Dict[str, Any]) -> float:
        api_spread = market.get("spread")
        if api_spread is not None:
            try:
                return float(api_spread)
            except (ValueError, TypeError):
                pass
        try:
            best_bid = float(market.get("bestBid", 0) or 0)
            best_ask = float(market.get("bestAsk", 0) or 0)
            if best_bid > 0 and best_ask > 0:
                return (best_ask - best_bid) / best_ask
        except (ValueError, TypeError):
            pass
        return 1.0

    def classify_market(self, market: Dict[str, Any]) -> str:
        question = (market.get("question") or "").lower()
        category = (market.get("category") or "").lower()
        tags     = [t.lower() for t in (market.get("tags_list") or market.get("tags") or [])]

        for cat, keywords in self.KEYWORDS.items():
            if any(k in question for k in keywords):
                return cat
            if any(k in category for k in keywords):
                return cat
            if tags and any(k in " ".join(tags) for k in keywords):
                return cat
        return "unknown"

    def is_short_term_crypto(self, market: Dict[str, Any]) -> bool:
        title    = (market.get("question") or market.get("title") or "").lower()
        slug     = (market.get("slug") or market.get("market_slug") or "").lower()
        tags     = [t.lower() for t in (market.get("tags_list") or market.get("tags") or [])]
        combined = title + " " + slug + " " + " ".join(tags)

        short_term_kws = [
            '5 min', '5 minutes', '15 min', '15 minutes', '5m', '15m',
            '1h', '4h', 'next 5', 'next 15', 'up or down', 'updown', 'up-or-down',
            'recurring'
        ]
        crypto_kws = [
            'bitcoin', 'btc', 'ethereum', 'eth', 'solana', 'sol',
            'xrp', 'ripple', 'bnb', 'avax', 'doge', 'matic', 'crypto'
        ]

        has_short_term = any(kw in combined for kw in short_term_kws)
        has_crypto     = any(c  in combined for c  in crypto_kws)
        return has_short_term and has_crypto

    def filter_markets(self, markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        qualified = []
        short_term_count = 0

        logger.info("Filtering markets with criteria:")
        logger.info(f"  - Crypto: {self.enable_crypto}, Finance: {self.enable_finance}, "
                    f"Politics: {self.enable_politics}, Sports: {self.enable_sports}")
        logger.info(f"  - Min Vol: ${self.min_volume:,.0f}, Min Liq: ${self.min_liquidity:,.0f}, "
                    f"Max Spread: {self.max_spread:.2%}")

        for market in markets:
            try:
                question = (market.get("question") or "").lower()

                # Blocklist (exceto mercados up or down)
                if "up or down" not in question:
                    if any(k in question for k in self.BLOCK_KEYWORDS):
                        continue

                volume    = float(market.get("volume",    0) or 0)
                liquidity = float(market.get("liquidity") or market.get("liquidityNum") or
                                  market.get("liquidityClob") or 0)
                spread    = self.calculate_spread(market)
                category  = self.classify_market(market)

                # Mercados Up or Down da CLOB: aceitando ordens = filtro relaxado
                if self.is_short_term_crypto(market):
                    accepting = market.get("accepting_orders", False)
                    if accepting:
                        # Já filtrado na coleta — aceita direto
                        market["mapped_category"] = "crypto"
                        qualified.append(market)
                        short_term_count += 1
                        logger.info(f"✅ Up or Down ativo: {question[:60]}")
                        continue
                    else:
                        # Veio da Gamma API com volume/liquidity conhecidos
                        if volume >= 300 and liquidity >= 30 and spread <= 0.25:
                            market["mapped_category"] = "crypto"
                            qualified.append(market)
                            short_term_count += 1
                            continue
                        else:
                            logger.debug(f"❌ Short-term rejeitado: '{question[:55]}' "
                                         f"Vol:{volume:.0f} Liq:{liquidity:.0f} Spread:{spread:.2%}")
                            continue

                # Filtros padrão
                if volume    < self.min_volume:    continue
                if liquidity < self.min_liquidity: continue
                if spread    > self.max_spread:    continue

                is_allowed = (
                    (category == "crypto"   and self.enable_crypto)   or
                    (category == "finance"  and self.enable_finance)  or
                    (category == "politics" and self.enable_politics) or
                    (category == "sports"   and self.enable_sports)
                )
                if is_allowed:
                    market["mapped_category"] = category
                    qualified.append(market)

            except Exception as e:
                logger.error(f"Error filtering market: {e}")
                continue

        qualified.sort(key=lambda x: float(x.get("liquidity", 0) or 0), reverse=True)
        logger.info(f"Qualificados: {len(qualified)} total ({short_term_count} Up or Down curto prazo)")
        return qualified

    def run(self) -> List[Dict[str, Any]]:
        raw_markets = self.fetch_active_markets()
        qualified   = self.filter_markets(raw_markets)
        logger.info(f"Found {len(qualified)} qualified markets.")
        return qualified


def save_markets(markets: List[Dict[str, Any]], filename: str = "qualified_markets.json"):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(markets, f, indent=2)
        logger.info(f"Saved to {filename}")
    except Exception as e:
        logger.error(f"Failed to save: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    print("Starting market discovery...")
    discovery = MarketDiscovery()
    markets = discovery.run()
    save_markets(markets)
    print(f"Done. Found {len(markets)} markets.")
