"""Direct Polymarket CLOB client for live trading."""

import json
import logging
from pathlib import Path

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY

import config

logger = logging.getLogger(__name__)

_client = None


def _load_private_key():
    with open(config.POLYMARKET_KEY_PATH) as f:
        return json.load(f)["private_key"]


def get_client() -> ClobClient:
    """Get or create the CLOB client singleton."""
    global _client
    if _client is None:
        pk = None
        try:
            pk = _load_private_key()
        except FileNotFoundError:
            logger.warning("Key file not found. Initializing client in read-only mode.")
        
        _client = ClobClient(
            host=config.POLYMARKET_HOST,
            key=pk,
            chain_id=config.POLYMARKET_CHAIN_ID,
        )
        
        if pk:
            # Derive API credentials from the wallet only if a key is present
            _client.set_api_creds(_client.create_or_derive_api_creds())
            logger.info("Polymarket CLOB client initialized with signing capabilities.")
        else:
            logger.info("Polymarket CLOB client initialized in read-only mode.")
            
    return _client


def get_balance() -> dict:
    """Get wallet USDC balance info."""
    try:
        client = get_client()
        # The CLOB client doesn't have a direct balance method,
        # but we can check via the allowances/collateral
        return {"connected": True}
    except Exception as e:
        logger.error(f"Balance check failed: {e}")
        return {"connected": False, "error": str(e)}


def get_market_info(token_id: str) -> dict:
    """Get current market/book info for a token."""
    try:
        client = get_client()
        book = client.get_order_book(token_id)
        return {
            "bids": book.bids if book.bids else [],
            "asks": book.asks if book.asks else [],
            "best_bid": float(book.bids[0].price) if book.bids else 0,
            "best_ask": float(book.asks[0].price) if book.asks else 1,
        }
    except Exception as e:
        logger.error(f"Market info error: {e}")
        return {}


def place_market_order(token_id: str, side: str, amount: float, 
                      order_type: str = "GTC", price: float = None) -> dict:
    """Place a market/limit order on Polymarket with enhanced functionality.

    Args:
        token_id: The YES or NO token ID from the market
        side: "yes" or "no"
        amount: USDC amount to spend
        order_type: "GTC", "IOC", "FOK"
        price: Limit price (if None, uses market price)
    """
    try:
        client = get_client()

        # Get the best price from the order book
        book = client.get_order_book(token_id)

        if side.lower() == "yes":
            # Buying YES tokens
            if not book.asks:
                return {"success": False, "error": "No asks in order book"}
            market_price = float(book.asks[0].price)
        else:
            # Buying NO tokens
            if not book.bids:
                return {"success": False, "error": "No bids in order book"}
            market_price = float(book.bids[0].price)

        # Use specified price or market price
        use_price = price if price is not None else market_price
        
        # Ensure price is within reasonable bounds
        use_price = max(0.01, min(0.99, use_price))

        # Build and sign the order
        order_args = OrderArgs(
            price=use_price,
            size=round(amount / use_price, 2),  # Convert USDC to shares
            side=BUY,
            token_id=token_id,
        )

        # Map order type string to CLOB OrderType
        clob_order_type = {
            "GTC": OrderType.GTC,
            "IOC": OrderType.IOC,
            "FOK": OrderType.FOK
        }.get(order_type.upper(), OrderType.GTC)

        signed_order = client.create_order(order_args)
        result = client.post_order(signed_order, clob_order_type)

        logger.info(f"Polymarket order placed: {side} ${amount} at {use_price} (type: {order_type})")
        return {
            "success": True,
            "order_id": result.get("orderID"),
            "price": use_price,
            "market_price": market_price,
            "size": order_args.size,
            "order_type": order_type,
            "result": result,
        }

    except Exception as e:
        logger.error(f"Polymarket order failed: {e}")
        return {"success": False, "error": str(e)}


def place_post_only_order(token_id: str, side: str, amount: float, target_price: float = None) -> dict:
    """Place a post-only order that adds liquidity to the book.
    
    Args:
        token_id: The YES or NO token ID from the market
        side: "yes" or "no"
        amount: USDC amount to spend
        target_price: Target price (if None, calculates optimal price)
    """
    try:
        client = get_client()
        book = client.get_order_book(token_id)
        
        if not book.bids or not book.asks:
            return {"success": False, "error": "Insufficient order book depth"}
        
        best_bid = float(book.bids[0].price)
        best_ask = float(book.asks[0].price)
        
        if target_price is None:
            # Calculate optimal post-only price
            if side.lower() == "yes":
                # For YES, place just below best bid to add liquidity
                target_price = max(0.01, best_bid - 0.001)
            else:
                # For NO, place just above best ask to add liquidity  
                target_price = min(0.99, best_ask + 0.001)
        
        # Ensure we're adding liquidity (not crossing the spread)
        if side.lower() == "yes" and target_price >= best_ask:
            return {"success": False, "error": "Post-only order would cross spread"}
        if side.lower() == "no" and target_price <= best_bid:
            return {"success": False, "error": "Post-only order would cross spread"}
        
        # Build and sign the order
        order_args = OrderArgs(
            price=target_price,
            size=round(amount / target_price, 2),  # Convert USDC to shares
            side=BUY,
            token_id=token_id,
        )
        
        signed_order = client.create_order(order_args)
        result = client.post_order(signed_order, OrderType.GTC)
        
        logger.info(f"Polymarket post-only order placed: {side} ${amount} at {target_price}")
        return {
            "success": True,
            "order_id": result.get("orderID"),
            "price": target_price,
            "size": order_args.size,
            "order_type": "POST_ONLY",
            "result": result,
        }
        
    except Exception as e:
        logger.error(f"Polymarket post-only order failed: {e}")
        return {"success": False, "error": str(e)}


def cancel_order(order_id: str) -> dict:
    """Cancel an existing order."""
    try:
        client = get_client()
        result = client.cancel_order(order_id)
        
        logger.info(f"Polymarket order cancelled: {order_id}")
        return {
            "success": True,
            "order_id": order_id,
            "result": result,
        }
        
    except Exception as e:
        logger.error(f"Polymarket order cancellation failed: {e}")
        return {"success": False, "error": str(e)}


def get_open_orders() -> list:
    """Get all open orders."""
    try:
        client = get_client()
        orders = client.get_orders()
        
        return [
            {
                "order_id": order.get("id"),
                "market": order.get("market"),
                "side": order.get("side"),
                "price": float(order.get("price", 0)),
                "size": float(order.get("size", 0)),
                "status": order.get("status"),
                "created_at": order.get("createdAt"),
            }
            for order in orders
        ]
        
    except Exception as e:
        logger.error(f"Failed to get open orders: {e}")
        return []


def verify_connection() -> dict:
    """Verify the Polymarket CLOB connection works."""
    try:
        client = get_client()
        # Try to fetch server time as a connectivity check
        ok = client.get_ok()
        return {"connected": True, "status": ok}
    except Exception as e:
        return {"connected": False, "error": str(e)}
