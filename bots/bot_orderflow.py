"""
Orderflow Bot - Análise de Fluxo de Ordens para Polymarket
"""

import logging
import time
import math
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from bots.base_bot import BaseBot
import config
import db

logger = logging.getLogger(__name__)


class OrderflowBot(BaseBot):
    """
    Bot baseado em análise de fluxo de ordens.
    
    Esta estratégia analisa:
    - Volume de ordens de compra vs venda
- Tamanho médio das ordens
    - Pressão de compra/venda
    - Mudanças no fluxo de ordens
    """
    
    def __init__(self, name: str, params: Dict[str, Any] = None, generation: int = 0):
        super().__init__(name, params, generation)
        
        # Parâmetros padrão
        self.params = {
            # Sensibilidade ao fluxo (0.1 = baixa, 1.0 = alta)
            'flow_sensitivity': 0.3,
            
            # Mínimo de volume para considerar sinal
            'min_volume_threshold': 1000,
            
            # Período de análise (minutos)
            'analysis_period': 15,
            
            # Ratio mínimo de compra/venda para sinal
            'min_buy_sell_ratio': 1.5,
            
            # Máximo ratio de compra/venda para sinal
            'max_buy_sell_ratio': 5.0,
            
            # Tamanho mínimo de ordem para considerar "whale"
            'whale_order_size': 500,
            
            # Peso de ordens de "whale" (0.1 = normal, 2.0 = muito importante)
            'whale_weight': 1.5,
            
            # Threshold de confiança para executar trade (0.5 = 50%)
            'confidence_threshold': 0.65,
            
            # Tempo máximo para manter posição (horas)
            'max_hold_time': 4,
            
            # Stop loss percentual
            'stop_loss_pct': 0.08,
            
            # Take profit percentual
            'take_profit_pct': 0.12,
            
            **(params or {})
        }
        
        # Cache de dados de fluxo
        self.flow_cache = {}
        self.last_analysis = {}
        
        logger.info(f"🌊 OrderflowBot '{name}' inicializado com params: {self.params}")
    
    def generate_signal(self, market: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gera sinal baseado em análise de fluxo de ordens.
        """
        market_id = market['market_id']
        
        # Obter dados de fluxo
        flow_data = self._get_orderflow_data(market_id)
        if not flow_data:
            return {"signal": 0, "confidence": 0, "reason": "no_flow_data"}
        
        # Analisar fluxo
        analysis = self._analyze_flow(flow_data)
        if not analysis:
            return {"signal": 0, "confidence": 0, "reason": "analysis_failed"}
        
        # Calcular sinal baseado na análise
        signal = self._calculate_signal(analysis, market)
        
        # Adicionar metadados
        signal.update({
            "analysis": analysis,
            "flow_data": flow_data,
            "market_price": market.get("p_yes", 0.5),
            "timestamp": time.time()
        })
        
        return signal
    
    def _get_orderflow_data(self, market_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém dados de fluxo de ordens do mercado.
        """
        try:
            # Obter do feed de orderflow
            from signals.orderflow import get_feed
            feed = get_feed()
            
            if not feed or market_id not in feed.data:
                return None
            
            return feed.data[market_id]
            
        except Exception as e:
            logger.error(f"Erro ao obter dados de orderflow para {market_id}: {e}")
            return None
    
    def _analyze_flow(self, flow_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analisa os dados de fluxo e extrai insights.
        """
        try:
            # Extrair métricas básicas
            buy_volume = flow_data.get("buy_volume", 0)
            sell_volume = flow_data.get("sell_volume", 0)
            buy_orders = flow_data.get("buy_orders", 0)
            sell_orders = flow_data.get("sell_orders", 0)
            
            # Calcular volumes e ratios
            total_volume = buy_volume + sell_volume
            
            if total_volume < self.params["min_volume_threshold"]:
                return {"reason": "low_volume", "total_volume": total_volume}
            
            # Ratio de compra/venda
            buy_sell_ratio = buy_volume / sell_volume if sell_volume > 0 else float('inf')
            
            # Tamanho médio das ordens
            avg_buy_size = buy_volume / buy_orders if buy_orders > 0 else 0
            avg_sell_size = sell_volume / sell_orders if sell_orders > 0 else 0
            
            # Identificar "whales" (ordens grandes)
            whale_buy_orders = flow_data.get("whale_buy_orders", 0)
            whale_sell_orders = flow_data.get("whale_sell_orders", 0)
            whale_buy_volume = flow_data.get("whale_buy_volume", 0)
            whale_sell_volume = flow_data.get("whale_sell_volume", 0)
            
            # Calcular pressão
            buy_pressure = self._calculate_pressure(
                volume=buy_volume,
                orders=buy_orders,
                whale_volume=whale_buy_volume,
                whale_orders=whale_buy_orders,
                avg_size=avg_buy_size
            )
            
            sell_pressure = self._calculate_pressure(
                volume=sell_volume,
                orders=sell_orders,
                whale_volume=whale_sell_volume,
                whale_orders=whale_sell_orders,
                avg_size=avg_sell_size
            )
            
            # Net pressure (positivo = compra dominante, negativo = venda dominante)
            net_pressure = buy_pressure - sell_pressure
            
            # Mudança na pressão vs período anterior
            pressure_change = self._calculate_pressure_change(flow_data)
            
            return {
                "buy_volume": buy_volume,
                "sell_volume": sell_volume,
                "total_volume": total_volume,
                "buy_sell_ratio": buy_sell_ratio,
                "avg_buy_size": avg_buy_size,
                "avg_sell_size": avg_sell_size,
                "buy_pressure": buy_pressure,
                "sell_pressure": sell_pressure,
                "net_pressure": net_pressure,
                "pressure_change": pressure_change,
                "whale_buy_orders": whale_buy_orders,
                "whale_sell_orders": whale_sell_orders,
                "whale_ratio": whale_buy_orders / whale_sell_orders if whale_sell_orders > 0 else float('inf')
            }
            
        except Exception as e:
            logger.error(f"Erro na análise de fluxo: {e}")
            return None
    
    def _calculate_pressure(self, volume: float, orders: int, whale_volume: float, 
                         whale_orders: int, avg_size: float) -> float:
        """
        Calcula pressão de compra ou venda com base em múltiplos fatores.
        """
        # Fator volume (0-1)
        volume_factor = min(volume / (self.params["min_volume_threshold"] * 5), 1.0)
        
        # Fator número de ordens (0-1)
        orders_factor = min(orders / 100, 1.0)
        
        # Fator tamanho médio (0-1)
        size_factor = min(avg_size / self.params["whale_order_size"], 1.0)
        
        # Fator whale (0-2, pode ser maior que 1)
        whale_factor = 1.0
        if whale_orders > 0:
            whale_ratio = whale_orders / orders if orders > 0 else 0
            whale_factor = 1.0 + (whale_ratio * (self.params["whale_weight"] - 1.0))
        
        # Pressão final (0-3)
        pressure = (volume_factor * 0.4 + orders_factor * 0.3 + size_factor * 0.3) * whale_factor
        
        return pressure
    
    def _calculate_pressure_change(self, flow_data: Dict[str, Any]) -> float:
        """
        Calcula mudança na pressão vs período anterior.
        """
        # Obter dados históricos se disponíveis
        historical = flow_data.get("historical", [])
        if len(historical) < 2:
            return 0.0
        
        try:
            # Comparar com período anterior
            current_pressure = flow_data.get("current_pressure", 0)
            previous_pressure = historical[-1].get("pressure", 0)
            
            if previous_pressure == 0:
                return 0.0
            
            return (current_pressure - previous_pressure) / abs(previous_pressure)
            
        except Exception:
            return 0.0
    
    def _calculate_signal(self, analysis: Dict[str, Any], market: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula sinal final baseado na análise de fluxo.
        """
        # Verificar se temos dados suficientes
        if "reason" in analysis:
            return {"signal": 0, "confidence": 0, "reason": analysis["reason"]}
        
        # Extrair métricas principais
        net_pressure = analysis["net_pressure"]
        buy_sell_ratio = analysis["buy_sell_ratio"]
        pressure_change = analysis["pressure_change"]
        
        # Verificar thresholds
        if buy_sell_ratio < self.params["min_buy_sell_ratio"] and buy_sell_ratio > (1 / self.params["max_buy_sell_ratio"]):
            return {"signal": 0, "confidence": 0, "reason": "ratio_outside_thresholds"}
        
        # Calcular força do sinal (-1 a 1)
        # Positivo = sinal de compra (YES), Negativo = sinal de venda (NO)
        
        # Baseado na pressão líquida
        pressure_signal = net_pressure * self.params["flow_sensitivity"]
        
        # Baseado na mudança de pressão (momentum)
        change_signal = pressure_change * 0.3
        
        # Baseado no ratio compra/venda
        if buy_sell_ratio > 1:
            ratio_signal = min((buy_sell_ratio - 1) / (self.params["max_buy_sell_ratio"] - 1), 1.0)
        else:
            ratio_signal = -min((1 - buy_sell_ratio) / (1 - 1/self.params["max_buy_sell_ratio"]), 1.0)
        
        # Sinal combinado
        signal = (pressure_signal * 0.5 + change_signal * 0.2 + ratio_signal * 0.3)
        
        # Limitar entre -1 e 1
        signal = max(-1.0, min(1.0, signal))
        
        # Calcular confiança (0 a 1)
        confidence = abs(signal)
        
        # Ajustar confiança baseado na qualidade dos dados
        if analysis["total_volume"] < self.params["min_volume_threshold"] * 2:
            confidence *= 0.7
        
        # Verificar threshold de confiança
        if confidence < self.params["confidence_threshold"]:
            return {"signal": 0, "confidence": confidence, "reason": "low_confidence"}
        
        # Determinar direção e força
        direction = "YES" if signal > 0 else "NO"
        strength = abs(signal)
        
        # Calcular tamanho sugerido do trade
        suggested_amount = self._calculate_position_size(strength, market)
        
        return {
            "signal": signal,
            "confidence": confidence,
            "direction": direction,
            "strength": strength,
            "suggested_amount": suggested_amount,
            "reason": "orderflow_signal",
            "analysis_summary": {
                "net_pressure": net_pressure,
                "buy_sell_ratio": buy_sell_ratio,
                "pressure_change": pressure_change,
                "total_volume": analysis["total_volume"]
            }
        }
    
    def _calculate_position_size(self, strength: float, market: Dict[str, Any]) -> float:
        """
        Calcula tamanho da posição baseado na força do sinal.
        """
        # Obter limites de risco
        max_pos = self._get_max_position_size()
        
        # Tamanho baseado na força do sinal (30% a 80% do máximo)
        base_size = max_pos * (0.3 + strength * 0.5)
        
        # Ajustar baseado na volatilidade do mercado (se disponível)
        volatility = market.get("volatility", 0.05)
        if volatility > 0.1:  # Alta volatilidade
            base_size *= 0.7
        
        return base_size
    
    def _get_max_position_size(self) -> float:
        """
        Obtém tamanho máximo de posição baseado na banca atual.
        """
        # Usar o RiskManager para obter limites atuais
        from core.risk_manager import risk_manager
        
        # Atualizar bankroll se necessário
        if time.time() - risk_manager.last_update > 30:
            risk_manager.update_bankroll(risk_manager._get_current_bankroll())
        
        # Retornar limite de posição por bot
        return risk_manager.limits.get("max_pos_per_bot", 50.0)
    
    def should_exit_position(self, position: Dict[str, Any], market: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decide se deve sair de uma posição baseada em condições de saída.
        """
        # Verificar stop loss e take profit
        exit_check = super().should_exit_position(position, market)
        if exit_check["should_exit"]:
            return exit_check
        
        # Verificar reversão no fluxo
        try:
            market_id = position["market_id"]
            flow_data = self._get_orderflow_data(market_id)
            
            if not flow_data:
                return {"should_exit": False, "reason": "no_flow_data"}
            
            # Analisar fluxo atual
            analysis = self._analyze_flow(flow_data)
            if not analysis or "net_pressure" not in analysis:
                return {"should_exit": False, "reason": "analysis_failed"}
            
            # Verificar reversão
            current_pressure = analysis["net_pressure"]
            entry_pressure = position.get("entry_flow_pressure", current_pressure)
            
            # Se a pressão reverteu significativamente, considerar saída
            pressure_change = (current_pressure - entry_pressure) / abs(entry_pressure) if entry_pressure != 0 else 0
            
            if abs(pressure_change) > 0.5:  # 50% de reversão
                return {
                    "should_exit": True,
                    "reason": "flow_reversal",
                    "pressure_change": pressure_change
                }
            
            # Verificar tempo máximo de holding
            entry_time = datetime.fromisoformat(position["created_at"])
            max_hold = timedelta(hours=self.params["max_hold_time"])
            
            if datetime.now() - entry_time > max_hold:
                return {
                    "should_exit": True,
                    "reason": "max_hold_time_reached"
                }
            
            return {"should_exit": False, "reason": "hold"}
            
        except Exception as e:
            logger.error(f"Erro ao verificar saída por fluxo: {e}")
            return {"should_exit": False, "reason": "error"}
    
    def analyze(self, market: dict, signals: dict) -> dict:
        """Analyze market + signals and return a trade signal.
        
        Returns:
            {
                "action": "buy" | "sell" | "hold",
                "side": "yes" | "no",
                "confidence": 0.0-1.0,
                "reasoning": "why this trade",
                "suggested_amount": float,
            }
        """
        try:
            # Generate signal using existing logic
            signal_data = self.generate_signal(market)
            
            # Convert signal to standard format
            signal = signal_data.get("signal", 0)
            confidence = signal_data.get("confidence", 0)
            
            # Determine action based on signal
            if confidence < self.params["confidence_threshold"]:
                return {
                    "action": "hold",
                    "side": "yes",
                    "confidence": confidence,
                    "reasoning": signal_data.get("reason", "low_confidence"),
                    "suggested_amount": 0.0
                }
            
            # Determine side based on signal direction
            if signal > 0:
                action = "buy"
                side = "yes"
            else:
                action = "sell" 
                side = "no"
            
            # Get suggested amount
            suggested_amount = signal_data.get("suggested_amount", 0.0)
            
            # Build reasoning
            analysis_summary = signal_data.get("analysis_summary", {})
            reasoning_parts = []
            
            if "net_pressure" in analysis_summary:
                pressure = analysis_summary["net_pressure"]
                if pressure > 0:
                    reasoning_parts.append(f"Strong buy pressure ({pressure:.2f})")
                else:
                    reasoning_parts.append(f"Strong sell pressure ({abs(pressure):.2f})")
            
            if "buy_sell_ratio" in analysis_summary:
                ratio = analysis_summary["buy_sell_ratio"]
                reasoning_parts.append(f"Buy/sell ratio: {ratio:.2f}")
            
            if "total_volume" in analysis_summary:
                volume = analysis_summary["total_volume"]
                reasoning_parts.append(f"Volume: ${volume:,.0f}")
            
            reasoning = "; ".join(reasoning_parts) if reasoning_parts else "Orderflow signal"
            
            return {
                "action": action,
                "side": side,
                "confidence": confidence,
                "reasoning": reasoning,
                "suggested_amount": suggested_amount
            }
            
        except Exception as e:
            logger.error(f"Error in analyze method: {e}")
            return {
                "action": "hold",
                "side": "yes", 
                "confidence": 0.0,
                "reasoning": f"Analysis error: {str(e)}",
                "suggested_amount": 0.0
            }

    def get_strategy_description(self) -> str:
        """Retorna descrição da estratégia."""
        return f"""
Orderflow Bot - Análise de Fluxo de Ordens

Parâmetros atuais:
- Sensibilidade: {self.params['flow_sensitivity']}
- Volume mínimo: ${self.params['min_volume_threshold']}
- Período análise: {self.params['analysis_period']}min
- Threshold compra: {self.params['min_buy_sell_ratio']}
- Max hold: {self.params['max_hold_time']}h
- Stop: {self.params['stop_loss_pct']*100}%
- Target: {self.params['take_profit_pct']*100}%

Estratégia: Analisa volume, tamanho e direção das ordens para identificar 
pressão de compra/venda antes de executar trades.
        """.strip()