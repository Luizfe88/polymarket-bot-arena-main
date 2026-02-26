"""Real-time BTC/SOL price data from Binance WebSocket."""

import json
import time
import threading
import logging
import requests
from collections import deque

logger = logging.getLogger(__name__)

# Mapeamento interno (nossas chaves) -> Símbolos Binance
# Agora suportamos BTC, ETH, SOL, XRP
SYMBOLS_MAP = {
    "btc": "btcusdt",
    "eth": "ethusdt",
    "sol": "solusdt",
    "xrp": "xrpusdt"
}

BINANCE_WS_BASE = "wss://stream.binance.com:9443/ws"

class PriceFeed:
    def __init__(self, max_candles=100):
        # Inicializa estruturas para todos os símbolos suportados
        self.prices = {sym: deque(maxlen=max_candles) for sym in SYMBOLS_MAP}
        self.volumes = {sym: deque(maxlen=max_candles) for sym in SYMBOLS_MAP}
        self.latest = {sym: 0.0 for sym in SYMBOLS_MAP}
        self._last_update = {sym: 0.0 for sym in SYMBOLS_MAP}
        self._running = False
        self._thread = None
        self.lock = threading.Lock()

    def start(self):
        if self._running:
            return
        
        self._running = True
        
        # Carrega histórico inicial via REST
        self._load_historical_data()
        
        # Inicia thread do WebSocket
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info(f"Price feed started for {list(SYMBOLS_MAP.keys())}")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self):
        import websocket

        # Constrói URL com streams para todos os símbolos
        # Formato: <symbol>@kline_1m
        streams_list = [f"{s}@kline_1m" for s in SYMBOLS_MAP.values()]
        streams_str = "/".join(streams_list)
        url = f"{BINANCE_WS_BASE}/{streams_str}"

        while self._running:
            try:
                ws = websocket.WebSocket()
                ws.settimeout(10)
                ws.connect(url)
                logger.info(f"Connected to Binance WS: {url}")

                while self._running:
                    try:
                        raw = ws.recv()
                        if not raw:
                            break
                        
                        msg = json.loads(raw)
                        # Payload de kline:
                        # { "e": "kline", "E": 123456789, "s": "BTCUSDT", "k": { ... } }
                        kline = msg.get("k", {})
                        if not kline:
                            continue

                        symbol_raw = msg.get("s", "").lower() # ex: btcusdt
                        
                        # Identifica qual chave interna corresponde a este símbolo
                        internal_key = None
                        for k, v in SYMBOLS_MAP.items():
                            if v == symbol_raw:
                                internal_key = k
                                break
                        
                        if not internal_key:
                            continue

                        close_price = float(kline.get("c", 0))
                        volume = float(kline.get("v", 0))
                        is_closed = kline.get("x", False)

                        with self.lock:
                            self.latest[internal_key] = close_price
                            self._last_update[internal_key] = time.time()
                            
                            if is_closed:
                                self.prices[internal_key].append(close_price)
                                self.volumes[internal_key].append(volume)

                    except (json.JSONDecodeError, ValueError, KeyError):
                        continue
                    except Exception as e:
                        logger.error(f"WS error loop: {e}")
                        break

                ws.close()
            except Exception as e:
                logger.error(f"Price feed connection error: {e}")
                time.sleep(5)

    def _load_historical_data(self):
        """Load 100 candles of historical data from Binance REST API for ALL symbols."""
        for internal_key, binance_sym in SYMBOLS_MAP.items():
            try:
                url = f"https://api.binance.com/api/v3/klines?symbol={binance_sym.upper()}&interval=1m&limit=100"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    klines = response.json()
                    with self.lock:
                        # Limpa dados anteriores para evitar duplicação se chamado novamente
                        self.prices[internal_key].clear()
                        self.volumes[internal_key].clear()
                        
                        for kline in klines:
                            close_price = float(kline[4])
                            volume = float(kline[5])
                            self.prices[internal_key].append(close_price)
                            self.volumes[internal_key].append(volume)
                        
                        if self.prices[internal_key]:
                            self.latest[internal_key] = self.prices[internal_key][-1]
                            self._last_update[internal_key] = time.time()
                            
                    logger.info(f"Loaded {len(klines)} historical candles for {internal_key.upper()}")
                else:
                    logger.warning(f"Failed to load history for {internal_key}: HTTP {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Error loading history for {internal_key}: {e}")

    def get_signals(self, symbol="btc"):
        """Retorna sinais formatados para o bot."""
        sym = symbol.lower()
        if sym not in self.prices:
            # Fallback ou erro
            return {"prices": [], "volumes": [], "latest": 0.0}
            
        with self.lock:
            return {
                "prices": list(self.prices[sym]),
                "volumes": list(self.volumes[sym]),
                "latest": self.latest[sym]
            }

# Helper global
_feed = None

def get_feed():
    global _feed
    if _feed is None:
        _feed = PriceFeed()
    return _feed
