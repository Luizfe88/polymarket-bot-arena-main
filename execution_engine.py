"""
Professional Execution Engine for Polymarket Bot Arena v3.0
Implements intelligent limit orders, TWAP/iceberg strategies, and real cost modeling.
"""

import logging
import math
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import config

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order execution types"""
    MARKET = "market"
    LIMIT = "limit"
    POST_ONLY = "post_only"
    TWAP = "twap"
    ICEBERG = "iceberg"


@dataclass
class ExecutionConfig:
    """Configuration for trade execution"""
    order_type: OrderType = OrderType.POST_ONLY
    max_slippage: float = 0.005  # 0.5% max slippage
    time_in_force: str = "GTC"  # Good Till Cancelled
    post_only: bool = True  # Only add liquidity
    twap_slices: int = 4  # Number of slices for TWAP
    twap_interval_seconds: int = 30  # Interval between TWAP slices
    iceberg_visible_size: float = 0.1  # 10% visible for iceberg orders
    max_order_size: float = 1000.0  # Max $1000 per order
    urgency: str = "normal"  # normal, urgent, patient


@dataclass
class CostBreakdown:
    """Detailed cost breakdown for a trade"""
    spread_cost: float = 0.0
    taker_fee: float = 0.0
    maker_fee: float = 0.0
    gas_cost: float = 0.0
    slippage_cost: float = 0.0
    opportunity_cost: float = 0.0
    total_cost: float = 0.0
    total_cost_pct: float = 0.0


class ExecutionEngine:
    """Professional execution engine with intelligent order management"""
    
    def __init__(self, config: ExecutionConfig = None):
        self.config = config or ExecutionConfig()
        self.taker_fee_rate = 0.005  # 0.5% taker fee
        self.maker_fee_rate = -0.002  # -0.2% maker rebate
        self.gas_cost_per_trade = 0.50  # $0.50 estimated gas per trade
        
    def calculate_optimal_order_price(self, market_data: dict, side: str, size: float) -> float:
        """
        Calculate optimal order price based on market conditions and urgency
        
        Args:
            market_data: Dict with bids/asks from order book
            side: "buy" or "sell"
            size: Order size in shares
            
        Returns:
            Optimal price for the order
        """
        try:
            bids = market_data.get("bids", [])
            asks = market_data.get("asks", [])
            
            if not bids or not asks:
                logger.warning("No order book data available, using mid price")
                return market_data.get("current_price", 0.5)
            
            best_bid = float(bids[0]["price"]) if bids else 0
            best_ask = float(asks[0]["price"]) if asks else 1
            mid_price = (best_bid + best_ask) / 2
            
            # Calculate spread and market impact
            spread = best_ask - best_bid
            
            if side.lower() == "buy":
                if self.config.order_type == OrderType.POST_ONLY:
                    # Place order just below best bid to add liquidity
                    return max(0.01, best_bid - 0.001)
                elif self.config.order_type == OrderType.LIMIT:
                    # Place at or slightly below mid price
                    return max(0.01, mid_price - spread * 0.1)
                else:  # MARKET
                    return best_ask  # Take best ask
                    
            else:  # sell
                if self.config.order_type == OrderType.POST_ONLY:
                    # Place order just above best ask to add liquidity
                    return min(0.99, best_ask + 0.001)
                elif self.config.order_type == OrderType.LIMIT:
                    # Place at or slightly above mid price
                    return min(0.99, mid_price + spread * 0.1)
                else:  # MARKET
                    return best_bid  # Take best bid
                    
        except Exception as e:
            logger.error(f"Error calculating optimal price: {e}")
            return market_data.get("current_price", 0.5)
    
    def calculate_total_cost(self, size: float, price: float, order_type: OrderType, 
                           market_data: dict, execution_time: float = 0.0) -> CostBreakdown:
        """
        Calculate comprehensive cost breakdown for a trade
        
        Args:
            size: Trade size in shares
            price: Execution price
            order_type: Type of order executed
            market_data: Market data at time of execution
            execution_time: Time taken to execute in seconds
            
        Returns:
            CostBreakdown object with detailed costs
        """
        try:
            notional = size * price
            
            # Spread cost (difference from mid price)
            bids = market_data.get("bids", [])
            asks = market_data.get("asks", [])
            if bids and asks:
                best_bid = float(bids[0]["price"])
                best_ask = float(asks[0]["price"])
                mid_price = (best_bid + best_ask) / 2
                
                if order_type == OrderType.MARKET:
                    # Market orders pay the spread
                    spread_cost = abs(price - mid_price) * size
                else:
                    # Limit orders might still have some spread cost
                    spread_cost = abs(price - mid_price) * size * 0.1
            else:
                spread_cost = 0.0
            
            # Trading fees
            if order_type == OrderType.POST_ONLY:
                taker_fee = 0.0
                maker_fee = notional * abs(self.maker_fee_rate)  # Rebate is negative
            else:
                taker_fee = notional * self.taker_fee_rate
                maker_fee = 0.0
            
            # Gas cost
            gas_cost = self.gas_cost_per_trade
            
            # Slippage cost (for large orders)
            slippage_cost = 0.0
            if size > 100:  # Large orders
                slippage_rate = min(0.02, size / 1000 * 0.01)  # Up to 2% slippage
                slippage_cost = notional * slippage_rate
            
            # Opportunity cost (time value of money)
            opportunity_cost = 0.0
            if execution_time > 60:  # More than 1 minute
                daily_rate = 0.0001  # 0.01% daily opportunity cost
                opportunity_cost = notional * daily_rate * (execution_time / 86400)
            
            total_cost = spread_cost + taker_fee + maker_fee + gas_cost + slippage_cost + opportunity_cost
            total_cost_pct = total_cost / notional if notional > 0 else 0
            
            return CostBreakdown(
                spread_cost=spread_cost,
                taker_fee=taker_fee,
                maker_fee=maker_fee,
                gas_cost=gas_cost,
                slippage_cost=slippage_cost,
                opportunity_cost=opportunity_cost,
                total_cost=total_cost,
                total_cost_pct=total_cost_pct
            )
            
        except Exception as e:
            logger.error(f"Error calculating costs: {e}")
            return CostBreakdown()
    
    def execute_twap_order(self, market_data: dict, side: str, total_size: float, 
                          token_id: str, client_func) -> List[dict]:
        """
        Execute a TWAP (Time-Weighted Average Price) order
        
        Args:
            market_data: Current market data
            side: "buy" or "sell"
            total_size: Total size to trade
            token_id: Token ID for the market
            client_func: Function to place individual orders
            
        Returns:
            List of order results
        """
        slice_size = total_size / self.config.twap_slices
        results = []
        
        logger.info(f"Executing TWAP order: {total_size} shares in {self.config.twap_slices} slices")
        
        for i in range(self.config.twap_slices):
            try:
                # Place individual slice order
                slice_result = self.execute_single_order(
                    market_data, side, slice_size, token_id, client_func
                )
                results.append(slice_result)
                
                # Wait between slices (except for the last one)
                if i < self.config.twap_slices - 1:
                    time.sleep(self.config.twap_interval_seconds)
                    
            except Exception as e:
                logger.error(f"TWAP slice {i+1} failed: {e}")
                results.append({"success": False, "error": str(e)})
        
        return results
    
    def execute_iceberg_order(self, market_data: dict, side: str, total_size: float,
                            token_id: str, client_func) -> List[dict]:
        """
        Execute an iceberg order (large order split into smaller visible portions)
        
        Args:
            market_data: Current market data
            side: "buy" or "sell"
            total_size: Total size to trade
            token_id: Token ID for the market
            client_func: Function to place individual orders
            
        Returns:
            List of order results
        """
        visible_size = total_size * self.config.iceberg_visible_size
        remaining_size = total_size
        results = []
        
        logger.info(f"Executing iceberg order: {total_size} shares with {visible_size} visible")
        
        while remaining_size > 0:
            try:
                # Place visible portion
                current_slice = min(visible_size, remaining_size)
                slice_result = self.execute_single_order(
                    market_data, side, current_slice, token_id, client_func
                )
                results.append(slice_result)
                
                if slice_result.get("success"):
                    remaining_size -= current_slice
                else:
                    # If order failed, try with smaller size
                    visible_size *= 0.5
                    
                # Small delay between orders
                if remaining_size > 0:
                    time.sleep(2)
                    
            except Exception as e:
                logger.error(f"Iceberg order failed: {e}")
                results.append({"success": False, "error": str(e)})
                break
        
        return results
    
    def execute_single_order(self, market_data: dict, side: str, size: float,
                           token_id: str, client_func) -> dict:
        """
        Execute a single order with optimal pricing and cost tracking
        
        Args:
            market_data: Current market data
            side: "buy" or "sell"
            size: Order size in shares
            token_id: Token ID for the market
            client_func: Function to place the order (from polymarket_client)
            
        Returns:
            Order execution result with cost breakdown
        """
        start_time = time.time()
        
        try:
            # Calculate optimal price
            price = self.calculate_optimal_order_price(market_data, side, size)
            
            # Validate order size
            if size < 0.01:
                return {"success": False, "error": "Order size too small"}
            
            if size > self.config.max_order_size:
                return {"success": False, "error": "Order size exceeds maximum"}
            
            # Execute the order
            if side.lower() == "buy":
                result = client_func(token_id, "yes", size * price)  # Convert shares to USDC
            else:
                result = client_func(token_id, "no", size * price)
            
            execution_time = time.time() - start_time
            
            # Calculate costs
            cost_breakdown = self.calculate_total_cost(
                size, price, self.config.order_type, market_data, execution_time
            )
            
            # Enhance result with cost information
            if result.get("success"):
                result["cost_breakdown"] = {
                    "spread_cost": cost_breakdown.spread_cost,
                    "taker_fee": cost_breakdown.taker_fee,
                    "maker_fee": cost_breakdown.maker_fee,
                    "gas_cost": cost_breakdown.gas_cost,
                    "slippage_cost": cost_breakdown.slippage_cost,
                    "total_cost": cost_breakdown.total_cost,
                    "total_cost_pct": cost_breakdown.total_cost_pct,
                    "execution_time": execution_time
                }
                
                logger.info(f"Order executed: {side} {size}@{price}, "
                          f"Total cost: ${cost_breakdown.total_cost:.3f} "
                          f"({cost_breakdown.total_cost_pct:.2%})")
            
            return result
            
        except Exception as e:
            logger.error(f"Order execution failed: {e}")
            return {"success": False, "error": str(e)}
    
    def should_execute_trade(self, expected_value: float, cost_breakdown: CostBreakdown) -> bool:
        """
        Determine if a trade should be executed based on expected value vs costs
        
        Args:
            expected_value: Expected value of the trade
            cost_breakdown: Cost breakdown for the trade
            
        Returns:
            True if trade should be executed
        """
        # V3.0 requirement: minimum +4.5-6% EV per trade after costs
        min_ev_after_costs = 0.045
        
        net_ev = expected_value - cost_breakdown.total_cost_pct
        
        if net_ev < min_ev_after_costs:
            logger.info(f"Trade rejected: Net EV {net_ev:.2%} < minimum {min_ev_after_costs:.2%}")
            return False
        
        # Additional check: don't trade if costs exceed 50% of expected value
        if cost_breakdown.total_cost_pct > expected_value * 0.5:
            logger.info(f"Trade rejected: Costs {cost_breakdown.total_cost_pct:.2%} > 50% of EV {expected_value:.2%}")
            return False
        
        return True
    
    def get_execution_recommendation(self, market_data: dict, side: str, size: float) -> Dict:
        """
        Get execution recommendation for a trade
        
        Args:
            market_data: Current market data
            side: "buy" or "sell"
            size: Intended trade size
            
        Returns:
            Dictionary with execution recommendation
        """
        try:
            # Calculate optimal price and costs
            price = self.calculate_optimal_order_price(market_data, side, size)
            cost_breakdown = self.calculate_total_cost(size, price, self.config.order_type, market_data)
            
            # Determine best execution strategy
            if size > 500:  # Large orders
                if self.config.urgency == "patient":
                    recommended_strategy = "TWAP"
                else:
                    recommended_strategy = "ICEBERG"
            elif size > 100:  # Medium orders
                recommended_strategy = "POST_ONLY"
            else:  # Small orders
                recommended_strategy = "POST_ONLY"
            
            return {
                "recommended_strategy": recommended_strategy,
                "optimal_price": price,
                "estimated_cost_pct": cost_breakdown.total_cost_pct,
                "estimated_cost_usd": cost_breakdown.total_cost,
                "market_impact": self._estimate_market_impact(market_data, size),
                "execution_time_estimate": self._estimate_execution_time(size, recommended_strategy)
            }
            
        except Exception as e:
            logger.error(f"Error getting execution recommendation: {e}")
            return {
                "recommended_strategy": "POST_ONLY",
                "optimal_price": market_data.get("current_price", 0.5),
                "estimated_cost_pct": 0.01,
                "estimated_cost_usd": 0.01,
                "market_impact": "low",
                "execution_time_estimate": 30
            }
    
    def _estimate_market_impact(self, market_data: dict, size: float) -> str:
        """Estimate market impact of the trade"""
        bids = market_data.get("bids", [])
        asks = market_data.get("asks", [])
        
        if not bids or not asks:
            return "unknown"
        
        # Calculate total liquidity within 1% of mid price
        best_bid = float(bids[0]["price"])
        best_ask = float(asks[0]["price"])
        mid_price = (best_bid + best_ask) / 2
        
        liquidity_1pct = 0
        for level in bids + asks:
            price = float(level["price"])
            if abs(price - mid_price) / mid_price <= 0.01:  # Within 1%
                liquidity_1pct += float(level["size"])
        
        # Estimate impact based on size vs available liquidity
        impact_ratio = size / liquidity_1pct if liquidity_1pct > 0 else 1.0
        
        if impact_ratio < 0.05:
            return "low"
        elif impact_ratio < 0.15:
            return "medium"
        else:
            return "high"
    
    def _estimate_execution_time(self, size: float, strategy: str) -> int:
        """Estimate execution time in seconds"""
        base_times = {
            "POST_ONLY": 30,
            "LIMIT": 45,
            "MARKET": 15,
            "TWAP": 120,
            "ICEBERG": 180
        }
        
        base_time = base_times.get(strategy, 30)
        
        # Adjust for size
        if size > 1000:
            base_time *= 2
        elif size > 500:
            base_time *= 1.5
        
        return base_time


# Global execution engine instance
_execution_engine = None


def get_execution_engine() -> ExecutionEngine:
    """Get the global execution engine instance"""
    global _execution_engine
    if _execution_engine is None:
        _execution_engine = ExecutionEngine()
    return _execution_engine


def execute_professional_trade(market_data: dict, side: str, size: float, 
                             token_id: str, expected_value: float, 
                             client_func) -> dict:
    """
    Execute a professional trade with intelligent order management
    
    Args:
        market_data: Current market data
        side: "buy" or "sell"
        size: Trade size in shares
        token_id: Token ID for the market
        expected_value: Expected value of the trade
        client_func: Function to place orders (from polymarket_client)
        
    Returns:
        Trade execution result
    """
    engine = get_execution_engine()
    
    # Get execution recommendation
    recommendation = engine.get_execution_recommendation(market_data, side, size)
    
    # Check if trade should be executed
    cost_breakdown = engine.calculate_total_cost(
        size, recommendation["optimal_price"], 
        OrderType.POST_ONLY, market_data
    )
    
    if not engine.should_execute_trade(expected_value, cost_breakdown):
        return {
            "success": False,
            "error": "Trade rejected: insufficient EV after costs",
            "expected_value": expected_value,
            "estimated_cost_pct": cost_breakdown.total_cost_pct,
            "net_ev": expected_value - cost_breakdown.total_cost_pct
        }
    
    # Execute based on recommendation
    strategy = recommendation["recommended_strategy"]
    
    if strategy == "TWAP":
        results = engine.execute_twap_order(market_data, side, size, token_id, client_func)
    elif strategy == "ICEBERG":
        results = engine.execute_iceberg_order(market_data, side, size, token_id, client_func)
    else:  # POST_ONLY or LIMIT
        result = engine.execute_single_order(market_data, side, size, token_id, client_func)
        results = [result]
    
    # Aggregate results
    success_count = sum(1 for r in results if r.get("success"))
    total_executed = sum(r.get("size", 0) for r in results if r.get("success"))
    total_cost = sum(r.get("cost_breakdown", {}).get("total_cost", 0) for r in results if r.get("success"))
    
    return {
        "success": success_count > 0,
        "strategy": strategy,
        "total_executed": total_executed,
        "total_cost": total_cost,
        "success_rate": success_count / len(results) if results else 0,
        "individual_results": results,
        "execution_recommendation": recommendation
    }