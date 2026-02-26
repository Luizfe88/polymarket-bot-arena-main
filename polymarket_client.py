"""Direct Polymarket CLOB client for live trading."""

import json
import logging
import os
import asyncio
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
from threading import Thread
import time

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL

import config

logger = logging.getLogger(__name__)

_client = None

def _load_private_key():
    try:
        with open(config.POLYMARKET_KEY_PATH) as f:
            return json.load(f)["private_key"]
    except Exception:
        return os.environ.get("PRIVATE_KEY")

def get_client() -> ClobClient:
    """Get or create the CLOB client singleton."""
    global _client
    if _client is None:
        pk = None
        try:
            pk = _load_private_key()
        except FileNotFoundError:
            logger.warning("Key file not found. Initializing client in read-only mode.")
        
        # Proxy configuration (SOCKS5 support)
        # py_clob_client uses requests, so we can set env vars
        if os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY"):
            logger.info("Using proxy settings from environment variables")

        _client = ClobClient(
            host=config.POLYMARKET_HOST,
            key=pk,
            chain_id=config.POLYMARKET_CHAIN_ID,
        )
        
        if pk:
            # Derive API credentials from the wallet only if a key is present
            try:
                _client.set_api_creds(_client.create_or_derive_api_creds())
                logger.info("Polymarket CLOB client initialized with signing capabilities.")
            except Exception as e:
                logger.error(f"Failed to derive API creds: {e}")
        else:
            logger.info("Polymarket CLOB client initialized in read-only mode.")
            
    return _client

class WebSocketManager:
    """Manages WebSocket connections for market data."""
    def __init__(self):
        self.callbacks: Dict[str, List[Callable]] = {}
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)

    def subscribe(self, token_id: str, callback: Callable):
        if token_id not in self.callbacks:
            self.callbacks[token_id] = []
        self.callbacks[token_id].append(callback)

    def _run(self):
        # Placeholder for real WS implementation
        # In a real scenario, this would connect to Polymarket WS
        # and dispatch messages to callbacks
        while self.running:
            time.sleep(1) 

_ws_manager = WebSocketManager()

def get_ws_manager():
    return _ws_manager

def get_order_book(token_id: str) -> Dict[str, Any]:
    """Get order book (wrapper for client)."""
    client = get_client()
    try:
        return client.get_order_book(token_id)
    except Exception as e:
        logger.error(f"Error fetching order book for {token_id}: {e}")
        return {}
