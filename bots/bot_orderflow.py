import asyncio
import json
import time
import requests
import websocket
from threading import Thread
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class OrderFlowBot:
    """OrderFlow-Imbalance-v1 PRO - WebSocket + Whale Detection"""
    
    def __init__(self, config, polymarket_client):
        self.name = "orderflow-v1"
        self.config = config
        self.client = polymarket_client
        self.orderbook_cache: Dict = {}
        self.recent_trades = []
        self.last_update = {}
        
        # Parâmetros PRO
        self.imbalance_threshold = 0.38
        self.trade_flow_threshold = 0.68
        self.whale_multiplier = 5.0
        self.min_liquidity = 180_000
        self.min_edge = 0.028  # 2.8% após fees
        
        self.ws_thread = None
        self.running = False
        self.start_websocket()

    def start_websocket(self):
        """Inicia WebSocket em thread separada (não trava o arena)"""
        def ws_runner():
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    if data.get("event_type") == "book":
                        asset_id = data.get("asset_id")
                        if asset_id:
                            self.orderbook_cache[asset_id] = data
                            self.last_update[asset_id] = time.time()
                    elif data.get("event_type") == "trade":
                        self.recent_trades.append(data)
                        if len(self.recent_trades) > 300:
                            self.recent_trades.pop(0)
                except:
                    pass

            def on_error(ws, error):
                logger.warning(f"OrderFlow WS error: {error}")

            def on_close(ws, *args):
                logger.info("OrderFlow WS closed - reconnecting in 5s...")
                time.sleep(5)
                self.start_websocket()

            ws_url = "wss://ws.polymarket.com/market"  # canal oficial 2026
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            self.ws.run_forever(ping_interval=20)

        self.ws_thread = Thread(target=ws_runner, daemon=True)
        self.ws_thread.start()
        logger.info("✅ OrderFlow-v1 WebSocket iniciado (real-time)")

    def get_orderbook(self, token_id: str) -> Optional[Dict]:
        """Fallback REST se WS ainda não recebeu o market"""
        if token_id in self.orderbook_cache:
            return self.orderbook_cache[token_id]
        
        try:
            url = f"https://clob.polymarket.com/book?token_id={token_id}"
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                return r.json()
        except:
            pass
        return None

    def calculate_imbalance(self, book: Dict) -> float:
        """Imbalance do order book (top 8 níveis)"""
        bids = book.get("bids", [])[:8]
        asks = book.get("asks", [])[:8]
        
        bid_depth = sum(float(b["size"]) for b in bids)
        ask_depth = sum(float(a["size"]) for a in asks)
        total = bid_depth + ask_depth
        
        if total == 0:
            return 0.0
        return (bid_depth - ask_depth) / total

    def calculate_trade_flow(self) -> float:
        """% de volume de buys vs sells nos últimos 8 minutos"""
        if not self.recent_trades:
            return 0.5
        recent = [t for t in self.recent_trades if time.time() - t.get("timestamp", 0) < 480]
        if not recent:
            return 0.5
        
        buy_vol = sum(float(t.get("size", 0)) for t in recent if t.get("side") == "BUY")
        total_vol = sum(float(t.get("size", 0)) for t in recent)
        return buy_vol / total_vol if total_vol > 0 else 0.5

    def detect_whale(self, book: Dict) -> float:
        """Bônus se baleia foi absorvida"""
        # (simplificado - detecta ordens >5x média)
        return 0.0  # você pode expandir depois

    def get_probability(self, market: Dict) -> float:
        """Probabilidade final para YES"""
        try:
            yes_token = market.get("clobTokenIds", ["", ""])[0]  # Yes token
            if not yes_token:
                return 0.50
            
            book = self.get_orderbook(yes_token)
            if not book:
                return 0.50

            imbalance = self.calculate_imbalance(book)
            flow = self.calculate_trade_flow()
            whale_bonus = self.detect_whale(book)

            # Fórmula PRO
            p_yes = (
                market.get("current_price", 0.50) +
                (imbalance * 0.42) +
                ((flow - 0.5) * 0.31) +
                (whale_bonus * 0.15)
            )
            
            return max(0.01, min(0.99, p_yes))
            
        except Exception as e:
            logger.error(f"OrderFlow error: {e}")
            return 0.50

    def decide(self, market: Dict):
        """Decisão final (compatível com seu arena)"""
        p_yes = self.get_probability(market)
        mkt_price = market.get("current_price", 0.50)
        
        edge = abs(p_yes - mkt_price)
        ev_yes = (p_yes - mkt_price) * 0.98  # após ~2% fees
        
        if edge > self.min_edge and ev_yes > 0.015:
            size = self.config.get("position_size", 50)  # ajuste no seu RiskManager
            return {
                "side": "Yes",
                "size": size,
                "price": p_yes,
                "reason": f"OrderFlow edge {edge:.1%} | imbalance {self.calculate_imbalance(self.get_orderbook(market.get('clobTokenIds', [''])[0])):.2f}"
            }
        
        # Lógica para NO (simétrica)
        p_no = 1 - p_yes
        ev_no = (p_no - (1 - mkt_price)) * 0.98
        if edge > self.min_edge and ev_no > 0.015:
            return {
                "side": "No",
                "size": self.config.get("position_size", 50),
                "price": p_no,
                "reason": "OrderFlow edge (NO)"
            }
        
        return None  # skip

    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()
from bots.base_bot import BaseBot
import math

DEFAULT_PARAMS = {
    "position_size_pct": 0.05,
    "min_confidence": 0.55,
    "edge_weight": 0.7,
    "volume_weight": 0.3,
}


class OrderflowBot(BaseBot):
    def __init__(self, name="orderflow-v1", params=None, generation=0, lineage=None):
        super().__init__(
            name=name,
            strategy_type="orderflow",
            params=params or DEFAULT_PARAMS.copy(),
            generation=generation,
            lineage=lineage,
        )

    def analyze(self, market: dict, signals: dict) -> dict:
        of = signals.get("orderflow") or {}
        market_price = market.get("current_price", 0.5) or 0.5
        try:
            market_price = float(market_price)
        except (TypeError, ValueError):
            market_price = 0.5
        p = of.get("current_probability", market_price) or market_price
        try:
            p = float(p)
        except (TypeError, ValueError):
            p = market_price
        p = max(0.01, min(0.99, p))
        edge = p - market_price
        vol24h = of.get("volume_24h", 0) or 0
        try:
            vol24h = float(vol24h)
        except (TypeError, ValueError):
            vol24h = 0.0
        vol_sig = min(0.4, math.log1p(max(0.0, vol24h)) / 10.0)
        warnings = of.get("warnings", []) or []
        penalty = 0.05 * len(warnings)
        w_edge = self.strategy_params.get("edge_weight", 0.7)
        w_vol = self.strategy_params.get("volume_weight", 0.3)
        confidence = max(0.0, min(0.95, (abs(edge) * 2.0) * w_edge + vol_sig * w_vol - penalty))
        side = "yes" if edge > 0 else "no"
        import config
        amount = config.get_max_position() * self.strategy_params.get("position_size_pct", 0.05)
        min_conf = float(self.strategy_params.get("min_confidence", 0.55))
        if confidence < min_conf:
            return {
                "action": "hold",
                "side": side,
                "confidence": confidence,
                "reasoning": "low orderflow confidence",
                "suggested_amount": 0.0,
            }
        return {
            "action": "buy",
            "side": side,
            "confidence": confidence,
            "reasoning": f"orderflow prob={p:.3f} mkt={market_price:.3f} edge={abs(edge):.3f} vol={vol24h:.0f}",
            "suggested_amount": float(amount),
        }
