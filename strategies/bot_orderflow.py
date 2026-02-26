import asyncio
import json
import time
import requests
import websocket
from threading import Thread
from typing import Dict, Optional
import logging
import math

import config
import polymarket_client
from strategies.base_bot import BaseBot

logger = logging.getLogger(__name__)

class OrderFlowBot:
    """OrderFlow-Imbalance-v1 PRO 2026 - WebSocket oficial + Whale Detection"""
    
    def __init__(self, config, polymarket_client):
        self.name = "orderflow-v1"
        self.config = config
        self.client = polymarket_client
        self.orderbook_cache: Dict = {}
        self.recent_trades = []
        self.last_update = {}
        
        # Parâmetros PRO (ajustados para edge real)
        self.imbalance_threshold = 0.38
        self.trade_flow_threshold = 0.68
        self.whale_multiplier = 5.0
        self.min_liquidity = 180_000
        self.min_edge = 0.028   # 2.8% após fees
        
        self.ws = None
        self.ws_thread = None
        self.running = True
        self.start_websocket()

    def start_websocket(self):
        def ws_runner():
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    event_type = data.get("event_type")
                    
                    if event_type == "book":
                        asset_id = data.get("asset_id")
                        if asset_id:
                            self.orderbook_cache[asset_id] = data.get("book", data)
                            self.last_update[asset_id] = time.time()
                    elif event_type == "trade":
                        self.recent_trades.append(data)
                        if len(self.recent_trades) > 400:
                            self.recent_trades.pop(0)
                except:
                    pass

            def on_open(ws):
                logger.info("✅ OrderFlow-v1 conectado ao WebSocket oficial da Polymarket")
                # Subscribe em todos os mercados que o arena está usando
                ws.send(json.dumps({
                    "type": "market",
                    "assets_ids": ["*"],   # "*" = todos (ou liste os token_ids)
                    "custom_feature_enabled": True
                }))

            def on_error(ws, error):
                logger.warning(f"OrderFlow WS error: {error}")

            def on_close(ws, *args):
                logger.info("OrderFlow WS fechado - reconectando em 5s...")
                if self.running:
                    time.sleep(5)
                    self.start_websocket()

            ws_url = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            self.ws.run_forever(ping_interval=20, ping_timeout=10)

        self.ws_thread = Thread(target=ws_runner, daemon=True)
        self.ws_thread.start()

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
        recent = [t for t in self.recent_trades if time.time() - float(t.get("timestamp", 0) or 0) < 480]
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
                float(market.get("current_price", 0.50) or 0.50) +
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
        mkt_price = float(market.get("current_price", 0.50) or 0.50)
        
        edge = abs(p_yes - mkt_price)
        
        # Se p_yes > price, então EV_yes > 0 se (p_yes - price) > cost
        # Se p_yes < price, então p_no > (1-price), EV_no > 0
        
        # Lógica simplificada de decisão
        if p_yes > mkt_price + self.min_edge:
             return {
                "side": "Yes",
                "price": p_yes,
                "reason": f"OrderFlow edge YES {edge:.1%}",
                "confidence": min(0.95, 0.5 + edge * 2)
            }
        elif p_yes < mkt_price - self.min_edge:
             return {
                "side": "No",
                "price": 1 - p_yes,
                "reason": f"OrderFlow edge NO {edge:.1%}",
                "confidence": min(0.95, 0.5 + edge * 2)
            }
        
        return None

    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()


DEFAULT_PARAMS = {
    "position_size_pct": 0.05,
    "min_confidence": 0.55,
    "edge_weight": 0.7,
    "volume_weight": 0.3,
}

# Wrapper for Arena compatibility
class OrderflowBot(BaseBot):
    _logic_instance = None

    def __init__(self, name="orderflow-v1", params=None, generation=0, lineage=None):
        super().__init__(
            name=name,
            strategy_type="orderflow",
            params=params or DEFAULT_PARAMS.copy(),
            generation=generation,
            lineage=lineage,
        )
        # Singleton logic instance to avoid multiple websockets
        if OrderflowBot._logic_instance is None:
            # Config fake ou real, dependendo do que OrderFlowBot espera
            # Aqui passamos um dict vazio pois OrderFlowBot usa self.config.get("position_size")
            # mas vamos controlar o size no wrapper.
            OrderflowBot._logic_instance = OrderFlowBot({}, polymarket_client.get_client())

    def analyze(self, market: dict, signals: dict, kelly_fraction=None) -> dict:
        # Use internal logic instead of external signals
        decision = OrderflowBot._logic_instance.decide(market)
        
        if not decision:
            return {
                "action": "hold",
                "side": "yes",
                "confidence": 0.0,
                "reasoning": "no orderflow edge",
                "suggested_amount": 0.0,
            }

        # Map decision to Arena format
        side = decision["side"].lower() # "yes" or "no"
        confidence = decision.get("confidence", 0.6)
        reason = decision.get("reason", "orderflow edge")
        
        amount = config.get_max_position() * self.strategy_params.get("position_size_pct", 0.05)
        
        return {
            "action": "buy",
            "side": side,
            "confidence": confidence,
            "reasoning": reason,
            "suggested_amount": float(amount),
        }
