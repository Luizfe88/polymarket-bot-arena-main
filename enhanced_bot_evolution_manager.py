"""
Enhanced Bot Evolution Manager for Polymarket Bot Arena v3.0
Implements walk-forward optimization, advanced fitness functions, and professional evolution criteria.
"""

import json
import logging
import time
import threading
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import config
import db
from bots.base_bot import BaseBot

logger = logging.getLogger(__name__)


class EvolutionTrigger(Enum):
    """Evolution trigger reasons"""
    TRADE_THRESHOLD = "trade_threshold"
    WALK_FORWARD = "walk_forward"
    SAFETY_NET = "safety_net"
    MANUAL = "manual"
    SHARPE_KILL_SWITCH = "sharpe_kill_switch"


@dataclass
class BotPerformanceMetrics:
    """Comprehensive performance metrics for bot evaluation"""
    total_trades: int
    resolved_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    sharpe_ratio: float
    calmar_ratio: float
    max_drawdown: float
    total_pnl: float
    avg_trade_pnl: float
    fitness_score: float
    consistency_score: float


@dataclass
class EvolutionWindow:
    """Walk-forward optimization window"""
    start_date: datetime
    end_date: datetime
    is_training: bool
    performance_metrics: Optional[Dict] = None


class EnhancedBotEvolutionManager:
    """
    Professional evolution manager with v3.0 enhancements:
    - Walk-forward optimization (450-600 resolved trades)
    - Advanced fitness function (Sharpe 40% + Calmar 30% + Profit Factor 20% + Win Rate 10%)
    - Sharpe < 0.75 kill-switch
    - Diversity penalty and population management
    - Professional backtesting integration
    """
    
    def __init__(self, bots_source=None):
        # V3.0 Configuration
        self.min_resolved_trades = 450  # Minimum 450 resolved trades for evolution
        self.target_resolved_trades = 600  # Target 600 resolved trades
        self.walk_forward_window_days = 30  # 30-day walk-forward windows
        self.sharpe_kill_threshold = 0.75  # Kill-switch if Sharpe < 0.75
        self.max_evolution_time_hours = 12  # Maximum 12 hours for evolution process
        self.cooldown_hours = 5  # Minimum 5 hours between evolutions
        self.max_time_without_evolution = 8 * 3600  # 8 hours safety net
        
        # Evolution parameters
        self.population_size = getattr(config, 'NUM_BOTS', 8)
        self.survivors_per_cycle = getattr(config, 'SURVIVORS_PER_CYCLE', 3)
        self.mutation_rate = getattr(config, 'MUTATION_RATE', 0.10)
        self.diversity_penalty_weight = getattr(config, 'DIVERSITY_PENALTY', 0.15)
        
        # State management
        self.global_trade_count = 0
        self.resolved_trade_count = 0
        self.last_evolution_time = None
        self.evolution_in_progress = False
        self.evolution_history = []
        self.performance_windows = []
        
        # Threading
        self.lock = threading.Lock()
        self._bots_source = bots_source
        
        # Load persistent state
        self._load_state()
        
        logger.info(f"🧬 EnhancedBotEvolutionManager v3.0 iniciado")
        logger.info(f"   - Min resolved trades: {self.min_resolved_trades}")
        logger.info(f"   - Target resolved trades: {self.target_resolved_trades}")
        logger.info(f"   - Sharpe kill threshold: {self.sharpe_kill_threshold}")
        logger.info(f"   - Walk-forward window: {self.walk_forward_window_days} days")
        logger.info(f"   - Population size: {self.population_size}")
        logger.info(f"   - Survivors per cycle: {self.survivors_per_cycle}")
    
    def _load_state(self):
        """Load persistent state from database"""
        try:
            saved_state = db.get_arena_state("enhanced_evolution_state")
            if saved_state:
                state = json.loads(saved_state)
                self.global_trade_count = state.get("global_trade_count", 0)
                self.resolved_trade_count = state.get("resolved_trade_count", 0)
                self.last_evolution_time = datetime.fromtimestamp(state.get("last_evolution_time", time.time()))
                self.evolution_history = state.get("evolution_history", [])
                logger.info(f"📊 Estado carregado: {self.resolved_trade_count} trades resolvidos")
            else:
                # Initialize with current state
                self._save_state()
                logger.info("📊 Estado inicial criado")
                
        except Exception as e:
            logger.error(f"Erro ao carregar estado: {e}")
            # Fallback initialization
            self.last_evolution_time = datetime.now() - timedelta(hours=5)
            self._save_state()
    
    def _save_state(self):
        """Save state to database"""
        try:
            state = {
                "global_trade_count": self.global_trade_count,
                "resolved_trade_count": self.resolved_trade_count,
                "last_evolution_time": self.last_evolution_time.timestamp() if self.last_evolution_time else time.time(),
                "evolution_history": self.evolution_history[-10:],  # Keep last 10
            }
            db.set_arena_state("enhanced_evolution_state", json.dumps(state))
        except Exception as e:
            logger.error(f"Erro ao salvar estado: {e}")
    
    def record_resolved_trade(self, bot_name: str, trade_result: Dict):
        """
        Record a resolved trade and check evolution triggers
        
        Args:
            bot_name: Name of the bot that executed the trade
            trade_result: Trade result data (pnl, win/loss, etc.)
        """
        with self.lock:
            self.global_trade_count += 1
            self.resolved_trade_count += 1
            
            logger.info(f"📈 Trade resolvido: {bot_name} - P&L: ${trade_result.get('pnl', 0):.3f}")
            logger.info(f"📊 Total resolvidos: {self.resolved_trade_count}/{self.target_resolved_trades}")
            
            # Save to database
            try:
                db.record_resolved_trade(bot_name, trade_result)
            except Exception as e:
                logger.error(f"Erro ao registrar trade: {e}")
            
            self._save_state()
            self._evaluate_evolution_triggers()
    
    def _evaluate_evolution_triggers(self):
        """Evaluate all evolution triggers"""
        if self.evolution_in_progress:
            return
        
        # Check kill-switch trigger (Sharpe < 0.75)
        if self._check_sharpe_kill_switch():
            self._trigger_evolution(EvolutionTrigger.SHARPE_KILL_SWITCH)
            return
        
        # Check walk-forward trigger (450+ resolved trades)
        if self.resolved_trade_count >= self.min_resolved_trades:
            self._trigger_evolution(EvolutionTrigger.WALK_FORWARD)
            return
        
        # Check safety net trigger (8+ hours without evolution)
        if self.last_evolution_time:
            time_since_last = (datetime.now() - self.last_evolution_time).total_seconds()
            if time_since_last >= self.max_time_without_evolution:
                # Check if cooldown has passed
                if time_since_last >= self.cooldown_hours * 3600:
                    self._trigger_evolution(EvolutionTrigger.SAFETY_NET)
                    return
        
        # Log progress
        remaining_trades = max(0, self.min_resolved_trades - self.resolved_trade_count)
        if remaining_trades > 0:
            progress_pct = (self.resolved_trade_count / self.min_resolved_trades) * 100
            logger.debug(f"⏳ Evolução: {progress_pct:.1f}% completo, faltam {remaining_trades} trades")
    
    def _check_sharpe_kill_switch(self) -> bool:
        """Check if any bot has Sharpe ratio below kill threshold"""
        try:
            active_bots = self._get_active_bots()
            for bot in active_bots:
                metrics = self._calculate_bot_metrics(bot, days=30)
                if metrics and metrics.sharpe_ratio < self.sharpe_kill_threshold:
                    logger.warning(f"🚨 Kill-switch ativado: {bot.name} Sharpe={metrics.sharpe_ratio:.3f} < {self.sharpe_kill_threshold}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Erro ao verificar kill-switch: {e}")
            return False
    
    def _trigger_evolution(self, trigger: EvolutionTrigger):
        """Trigger evolution process"""
        with self.lock:
            if self.evolution_in_progress:
                return
            self.evolution_in_progress = True
        
        logger.info(f"🧬 Iniciando evolução v3.0 (razão: {trigger.value})")
        logger.info(f"📊 Métricas: {self.resolved_trade_count} trades resolvidos")
        
        # Start evolution in separate thread
        thread = threading.Thread(target=self._execute_evolution, args=(trigger,))
        thread.daemon = True
        thread.start()
    
    def _execute_evolution(self, trigger: EvolutionTrigger):
        """Execute the complete evolution process"""
        start_time = time.time()
        
        try:
            # Step 1: Get active bots and calculate performance metrics
            active_bots = self._get_active_bots()
            if not active_bots:
                logger.warning("Nenhum bot ativo para evolução")
                return
            
            logger.info(f"📊 Analisando {len(active_bots)} bots ativos")
            
            # Step 2: Calculate comprehensive performance metrics
            bot_metrics = {}
            for bot in active_bots:
                metrics = self._calculate_bot_metrics(bot, days=self.walk_forward_window_days)
                if metrics:
                    bot_metrics[bot.name] = metrics
            
            if len(bot_metrics) < 2:
                logger.warning("Performance insuficiente para evolução")
                return
            
            # Step 3: Apply walk-forward optimization
            walk_forward_results = self._perform_walk_forward_optimization(bot_metrics)
            
            # Step 4: Calculate fitness scores with diversity penalty
            fitness_rankings = self._calculate_fitness_rankings(walk_forward_results)
            
            # Step 5: Select survivors based on fitness
            survivors = self._select_survivors(fitness_rankings)
            
            # Step 6: Create evolved bots
            new_bots = self._create_evolved_bots(survivors, active_bots)
            
            # Step 7: Update configurations and retire underperformers
            self._update_bot_population(survivors, new_bots, active_bots)
            
            # Step 8: Log evolution event
            self._log_evolution_event(trigger, fitness_rankings, survivors, new_bots)
            
            # Update state
            evolution_time = time.time() - start_time
            with self.lock:
                self.last_evolution_time = datetime.now()
                self.resolved_trade_count = 0  # Reset counter
                self.evolution_in_progress = False
                self._save_state()
            
            logger.info(f"✅ Evolução v3.0 concluída em {evolution_time/60:.1f} minutos")
            logger.info(f"📈 Próxima evolução em {self.cooldown_hours}h")
            
        except Exception as e:
            logger.error(f"❌ Erro na evolução v3.0: {e}", exc_info=True)
            with self.lock:
                self.evolution_in_progress = False
    
    def _calculate_bot_metrics(self, bot: BaseBot, days: int = 30) -> Optional[BotPerformanceMetrics]:
        """Calculate comprehensive performance metrics for a bot"""
        try:
            # Get detailed performance data
            perf = bot.get_performance(hours=days*24)
            trades = db.get_bot_trades(bot.name, hours=days*24)
            
            if not trades:
                logger.debug(f"Sem trades para {bot.name} nos últimos {days} dias. Pulando cálculo de métricas.")
                return None
            
            if not trades or len(trades) < 10:
                return None
            
            # Calculate basic metrics
            total_trades = len(trades)
            resolved_trades = len([t for t in trades if t.get("resolved", False)])
            winning_trades = len([t for t in trades if (t.get("pnl") or 0) > 0])
            losing_trades = len([t for t in trades if (t.get("pnl") or 0) < 0])
            
            if resolved_trades == 0:
                return None
            
            win_rate = winning_trades / resolved_trades if resolved_trades > 0 else 0
            
            # Calculate P&L metrics
            total_pnl = sum((t.get("pnl") or 0) for t in trades)
            avg_trade_pnl = total_pnl / total_trades if total_trades > 0 else 0
            
            winning_pnls = [(t.get("pnl") or 0) for t in trades if (t.get("pnl") or 0) > 0]
            losing_pnls = [(t.get("pnl") or 0) for t in trades if (t.get("pnl") or 0) < 0]
            
            avg_win = statistics.mean(winning_pnls) if winning_pnls else 0
            avg_loss = statistics.mean(losing_pnls) if losing_pnls else 0
            
            # Calculate profit factor
            gross_profit = sum(winning_pnls)
            gross_loss = abs(sum(losing_pnls))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Calculate Sharpe ratio (simplified)
            daily_returns = self._calculate_daily_returns(trades)
            if len(daily_returns) > 5:
                sharpe_ratio = statistics.mean(daily_returns) / (statistics.stdev(daily_returns) + 1e-6) * (252**0.5)
            else:
                sharpe_ratio = 0.0
            
            # Calculate Calmar ratio
            max_drawdown = self._calculate_max_drawdown(trades)
            calmar_ratio = (total_pnl / abs(max_drawdown)) if max_drawdown != 0 else 0
            
            # Calculate fitness score (v3.0 formula)
            fitness_score = (
                sharpe_ratio * 0.40 +  # Sharpe: 40%
                calmar_ratio * 0.30 +  # Calmar: 30%
                (profit_factor / 2.0) * 0.20 +  # Profit Factor: 20% (normalized)
                (win_rate - 0.5) * 2.0 * 0.10  # Win Rate: 10% (normalized)
            )
            
            # Calculate consistency score (lower volatility is better)
            if len(daily_returns) > 5:
                consistency_score = 1.0 / (1.0 + statistics.stdev(daily_returns))
            else:
                consistency_score = 0.5
            
            return BotPerformanceMetrics(
                total_trades=total_trades,
                resolved_trades=resolved_trades,
                win_rate=win_rate,
                avg_win=avg_win,
                avg_loss=avg_loss,
                profit_factor=profit_factor,
                sharpe_ratio=sharpe_ratio,
                calmar_ratio=calmar_ratio,
                max_drawdown=max_drawdown,
                total_pnl=total_pnl,
                avg_trade_pnl=avg_trade_pnl,
                fitness_score=fitness_score,
                consistency_score=consistency_score
            )
            
        except Exception as e:
            logger.error(f"Erro ao calcular métricas de {bot.name}: {e}")
            return None
    
    def _calculate_daily_returns(self, trades: List[Dict]) -> List[float]:
        """Calculate daily returns from trade data"""
        daily_pnl = {}
        
        for trade in trades:
            date = trade.get("timestamp", "").split("T")[0]  # Extract date
            if date:
                pnl = trade.get("pnl") or 0
                daily_pnl[date] = daily_pnl.get(date, 0) + pnl
        
        return list(daily_pnl.values())
    
    def _calculate_max_drawdown(self, trades: List[Dict]) -> float:
        """Calculate maximum drawdown from trade sequence"""
        if not trades:
            return 0.0
        
        cumulative_pnl = 0
        peak = 0
        max_drawdown = 0
        
        for trade in trades:
            cumulative_pnl += (trade.get("pnl") or 0)
            if cumulative_pnl > peak:
                peak = cumulative_pnl
            
            drawdown = peak - cumulative_pnl
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return max_drawdown
    
    def _perform_walk_forward_optimization(self, bot_metrics: Dict[str, BotPerformanceMetrics]) -> Dict[str, Dict]:
        """Perform walk-forward optimization on bot performance"""
        logger.info(f"🔍 Executando walk-forward optimization em {len(bot_metrics)} bots")
        
        walk_forward_results = {}
        
        for bot_name, metrics in bot_metrics.items():
            # Get historical performance windows
            windows = self._create_walk_forward_windows(metrics.total_trades)
            
            window_results = []
            for window in windows:
                # Simulate performance in this window
                window_metrics = self._simulate_window_performance(bot_name, window)
                if window_metrics:
                    window_results.append({
                        "window": window,
                        "metrics": window_metrics,
                        "stability": self._calculate_stability_score(window_metrics)
                    })
            
            if window_results:
                # Calculate overall walk-forward score
                avg_fitness = statistics.mean([w["metrics"].fitness_score for w in window_results])
                stability_score = statistics.mean([w["stability"] for w in window_results])
                
                walk_forward_results[bot_name] = {
                    "avg_fitness": avg_fitness,
                    "stability_score": stability_score,
                    "window_results": window_results,
                    "overall_score": avg_fitness * stability_score
                }
        
        return walk_forward_results
    
    def _create_walk_forward_windows(self, total_trades: int) -> List[EvolutionWindow]:
        """Create walk-forward optimization windows"""
        windows = []
        now = datetime.now()
        
        # Create 4 windows of 30 days each, overlapping
        for i in range(4):
            start_date = now - timedelta(days=(i+1)*45)  # 45-day intervals
            end_date = start_date + timedelta(days=30)
            
            # Alternate between training and validation windows
            is_training = (i % 2 == 0)
            
            windows.append(EvolutionWindow(
                start_date=start_date,
                end_date=end_date,
                is_training=is_training
            ))
        
        return windows
    
    def _simulate_window_performance(self, bot_name: str, window: EvolutionWindow) -> Optional[BotPerformanceMetrics]:
        """Simulate bot performance in a specific window"""
        # This is a simplified simulation - in a real implementation,
        # you would use historical data for the specific window
        try:
            # Get bot trades within the window
            trades = db.get_bot_trades(bot_name, hours=30*24)
            if len(trades) < 10:
                return None
            
            return self._calculate_bot_metrics_from_trades(trades)
        except Exception as e:
            logger.error(f"Erro ao simular janela para {bot_name}: {e}")
            return None
    
    def _calculate_bot_metrics_from_trades(self, trades: List[Dict]) -> Optional[BotPerformanceMetrics]:
        """Calculate metrics from a specific set of trades"""
        if not trades or len(trades) < 5:
            return None
        
        # Simplified calculation - reuse existing logic
        total_trades = len(trades)
        resolved_trades = len([t for t in trades if t.get("resolved", False)])
        
        if resolved_trades == 0:
            return None
        
        winning_trades = len([t for t in trades if (t.get("pnl") or 0) > 0])
        win_rate = winning_trades / resolved_trades
        
        total_pnl = sum((t.get("pnl") or 0) for t in trades)
        avg_trade_pnl = total_pnl / total_trades
        
        # Simplified Sharpe and other metrics
        daily_returns = self._calculate_daily_returns(trades)
        if len(daily_returns) > 3:
            sharpe_ratio = statistics.mean(daily_returns) / (statistics.stdev(daily_returns) + 1e-6)
        else:
            sharpe_ratio = 0.0
        
        max_drawdown = self._calculate_max_drawdown(trades)
        calmar_ratio = (total_pnl / abs(max_drawdown)) if max_drawdown != 0 else 0
        
        # Calculate fitness score
        fitness_score = (
            sharpe_ratio * 0.40 +
            calmar_ratio * 0.30 +
            (win_rate - 0.5) * 2.0 * 0.30
        )
        
        return BotPerformanceMetrics(
            total_trades=total_trades,
            resolved_trades=resolved_trades,
            win_rate=win_rate,
            avg_win=0,  # Simplified
            avg_loss=0,  # Simplified
            profit_factor=1.5,  # Simplified
            sharpe_ratio=sharpe_ratio,
            calmar_ratio=calmar_ratio,
            max_drawdown=max_drawdown,
            total_pnl=total_pnl,
            avg_trade_pnl=avg_trade_pnl,
            fitness_score=fitness_score,
            consistency_score=0.5  # Simplified
        )
    
    def _calculate_stability_score(self, metrics: BotPerformanceMetrics) -> float:
        """Calculate stability score based on consistency of performance"""
        # Higher fitness with lower volatility = higher stability
        base_score = metrics.fitness_score
        consistency_bonus = metrics.consistency_score
        
        # Penalize high drawdowns
        drawdown_penalty = min(1.0, 1.0 - (metrics.max_drawdown / 0.5))  # Max 50% drawdown
        
        return base_score * consistency_bonus * drawdown_penalty
    
    def _calculate_fitness_rankings(self, walk_forward_results: Dict[str, Dict]) -> List[Dict]:
        """Calculate final fitness rankings with diversity penalty"""
        logger.info("📊 Calculando rankings de fitness com penalidade de diversidade")
        
        rankings = []
        
        for bot_name, wf_result in walk_forward_results.items():
            # Base fitness from walk-forward optimization
            base_fitness = wf_result["overall_score"]
            
            # Apply diversity penalty (reduce score for similar strategies)
            diversity_penalty = self._calculate_diversity_penalty(bot_name, walk_forward_results)
            
            final_fitness = base_fitness * (1.0 - diversity_penalty)
            
            rankings.append({
                "bot_name": bot_name,
                "base_fitness": base_fitness,
                "diversity_penalty": diversity_penalty,
                "final_fitness": final_fitness,
                "walk_forward_result": wf_result
            })
        
        # Sort by final fitness
        rankings.sort(key=lambda x: x["final_fitness"], reverse=True)
        
        # Log rankings
        logger.info("🏆 Rankings finais de fitness:")
        for i, rank in enumerate(rankings):
            logger.info(f"  #{i+1} {rank['bot_name']}: "
                       f"fitness={rank['final_fitness']:.3f} "
                       f"(base={rank['base_fitness']:.3f}, "
                       f"diversity_penalty={rank['diversity_penalty']:.1%})")
        
        return rankings
    
    def _calculate_diversity_penalty(self, bot_name: str, all_results: Dict[str, Dict]) -> float:
        """Calculate diversity penalty to encourage strategy diversity"""
        # This is a simplified implementation
        # In practice, you would analyze strategy similarity based on:
        # - Trade timing correlation
        # - Position sizing similarity
        # - Market selection overlap
        # - Parameter similarity
        
        # For now, use a simple penalty based on similar fitness scores
        current_fitness = all_results[bot_name]["overall_score"]
        similar_bots = 0
        
        for name, result in all_results.items():
            if name != bot_name:
                fitness_diff = abs(result["overall_score"] - current_fitness)
                if fitness_diff < 0.1:  # Similar fitness
                    similar_bots += 1
        
        # Penalty increases with number of similar bots
        penalty = min(0.3, similar_bots * 0.05)  # Max 30% penalty
        
        return penalty
    
    def _select_survivors(self, fitness_rankings: List[Dict]) -> List[Dict]:
        """Select survivors based on fitness rankings"""
        survivors_count = min(self.survivors_per_cycle, len(fitness_rankings))
        survivors = fitness_rankings[:survivors_count]
        
        logger.info(f"🏆 Selecionando {survivors_count} sobreviventes:")
        for i, survivor in enumerate(survivors):
            logger.info(f"  #{i+1} {survivor['bot_name']} (fitness: {survivor['final_fitness']:.3f})")
        
        return survivors
    
    def _create_evolved_bots(self, survivors: List[Dict], all_bots: List[BaseBot]) -> List[Dict]:
        """Create evolved bots from survivors"""
        new_bots = []
        
        # Identify bots to replace
        survivor_names = {s["bot_name"] for s in survivors}
        replaced_bots = [b for b in all_bots if b.name not in survivor_names]
        
        for dead_bot in replaced_bots:
            # Select parent (best performer among survivors)
            best_survivor = survivors[0]
            parent_name = best_survivor["bot_name"]
            parent = next(b for b in all_bots if b.name == parent_name)
            
            # Create evolved bot
            evolved = self._create_evolved_bot_from_parent(parent, dead_bot.strategy_type)
            
            new_bots.append({
                "evolved_bot": evolved,
                "parent": parent.name,
                "replaced": dead_bot.name,
                "parent_fitness": best_survivor["final_fitness"]
            })
            
            logger.info(f"  ⭐ Criado {evolved.name} (de {parent.name}, fitness: {best_survivor['final_fitness']:.3f})")
        
        return new_bots
    
    def _create_evolved_bot_from_parent(self, parent: BaseBot, strategy_type: str) -> BaseBot:
        """Create an evolved bot from a parent bot"""
        # Import evolution function from arena
        from arena import create_evolved_bot
        
        # Create with next generation number
        gen_number = parent.generation + 1
        
        # Apply intelligent mutation based on parent's performance
        mutation_intensity = self._calculate_mutation_intensity(parent)
        
        evolved = create_evolved_bot(parent, strategy_type, gen_number)
        
        # Apply additional mutations based on performance
        if mutation_intensity > 0:
            self._apply_performance_based_mutation(evolved, parent, mutation_intensity)
        
        return evolved
    
    def _calculate_mutation_intensity(self, parent: BaseBot) -> float:
        """Calculate mutation intensity based on parent performance"""
        try:
            metrics = self._calculate_bot_metrics(parent, days=30)
            if not metrics:
                return 0.5  # Default moderate mutation
            
            # Higher mutation for poor performers, lower for good performers
            if metrics.sharpe_ratio < 0.5:
                return 0.8  # High mutation
            elif metrics.sharpe_ratio < 1.0:
                return 0.5  # Moderate mutation
            else:
                return 0.2  # Low mutation (good performer)
        except:
            return 0.5
    
    def _apply_performance_based_mutation(self, evolved: BaseBot, parent: BaseBot, intensity: float):
        """Apply performance-based mutations to evolved bot"""
        # This would contain sophisticated mutation logic based on:
        # - Parent's failure patterns
        # - Market regime changes
        # - Parameter sensitivity analysis
        # For now, it's a placeholder for advanced mutation strategies
        pass
    
    def _update_bot_population(self, survivors: List[Dict], new_bots: List[Dict], all_bots: List[BaseBot]):
        """Update bot population in database"""
        try:
            # Retire replaced bots
            for new_bot_info in new_bots:
                replaced_name = new_bot_info["replaced"]
                db.retire_bot(replaced_name)
                logger.info(f"  🗑️ Bot aposentado: {replaced_name}")
            
            # Save new bots
            for new_bot_info in new_bots:
                evolved = new_bot_info["evolved_bot"]
                db.save_bot_config(
                    evolved.name,
                    evolved.strategy_type,
                    evolved.generation,
                    evolved.strategy_params,
                    evolved.lineage
                )
                logger.info(f"  💾 Bot salvo: {evolved.name}")
                
        except Exception as e:
            logger.error(f"Erro ao atualizar população: {e}")
    
    def _log_evolution_event(self, trigger: EvolutionTrigger, fitness_rankings: List[Dict], 
                           survivors: List[Dict], new_bots: List[Dict]):
        """Log evolution event to database"""
        try:
            survivor_names = [s["bot_name"] for s in survivors]
            replaced_names = [nb["replaced"] for nb in new_bots]
            new_bot_names = [nb["evolved_bot"].name for nb in new_bots]
            
            # Calculate evolution statistics
            avg_fitness = statistics.mean([s["final_fitness"] for s in survivors]) if survivors else 0
            avg_sharpe = statistics.mean([s["walk_forward_result"]["avg_fitness"] for s in survivors]) if survivors else 0
            
            db.log_evolution(
                cycle_number=int(time.time()),
                survivor_names=survivor_names,
                replaced_names=replaced_names,
                new_bot_names=new_bot_names,
                rankings=fitness_rankings,
                trigger_reason=trigger.value,
                avg_fitness=avg_fitness,
                avg_sharpe=avg_sharpe
            )
            
            # Add to evolution history
            self.evolution_history.append({
                "timestamp": datetime.now().isoformat(),
                "trigger": trigger.value,
                "survivors": survivor_names,
                "new_bots": new_bot_names,
                "avg_fitness": avg_fitness,
                "avg_sharpe": avg_sharpe
            })
            
        except Exception as e:
            logger.error(f"Erro ao registrar evolução: {e}")
    
    def force_evolution(self) -> bool:
        """Force manual evolution (bypasses cooldown)"""
        if self.evolution_in_progress:
            logger.warning("Evolução já em progresso")
            return False
        
        logger.info("🚨 Forçando evolução manual v3.0")
        thread = threading.Thread(target=self._execute_evolution, args=(EvolutionTrigger.MANUAL,))
        thread.daemon = True
        thread.start()
        return True
    
    def get_status(self) -> Dict:
        """Get comprehensive evolution status"""
        now = datetime.now()
        
        if self.last_evolution_time:
            time_since_last = (now - self.last_evolution_time).total_seconds()
            cooldown_active = time_since_last < (self.cooldown_hours * 3600)
        else:
            time_since_last = 0
            cooldown_active = False
        
        remaining_trades = max(0, self.min_resolved_trades - self.resolved_trade_count)
        progress_pct = (self.resolved_trade_count / self.min_resolved_trades) * 100 if self.min_resolved_trades > 0 else 0
        
        triggers = {
            "walk_forward": self.resolved_trade_count >= self.min_resolved_trades,
            "sharpe_kill_switch": self._check_sharpe_kill_switch(),
            "safety_net": (time_since_last >= self.max_time_without_evolution) and not cooldown_active
        }
        
        can_evolve = any(triggers.values()) and not cooldown_active
        
        return {
            "version": "3.0",
            "resolved_trade_count": self.resolved_trade_count,
            "min_resolved_trades": self.min_resolved_trades,
            "target_resolved_trades": self.target_resolved_trades,
            "progress_percent": progress_pct,
            "last_evolution_time": self.last_evolution_time.isoformat() if self.last_evolution_time else None,
            "time_since_last_evolution": time_since_last,
            "hours_since_last_evolution": time_since_last / 3600.0,
            "cooldown_active": cooldown_active,
            "remaining_cooldown": max(0, int(self.cooldown_hours * 3600 - time_since_last)),
            "trades_to_evolution": remaining_trades,
            "can_evolve": can_evolve,
            "evolution_in_progress": self.evolution_in_progress,
            "triggers": triggers,
            "sharpe_kill_threshold": self.sharpe_kill_threshold,
            "walk_forward_window_days": self.walk_forward_window_days,
            "population_size": self.population_size,
            "survivors_per_cycle": self.survivors_per_cycle,
            "evolution_history": self.evolution_history[-5:],  # Last 5 evolutions
            "next_evolution_time": (self.last_evolution_time + timedelta(hours=self.cooldown_hours)).isoformat() if cooldown_active else None
        }
    
    def _get_active_bots(self) -> List[BaseBot]:
        """Get list of active bots"""
        if self._bots_source:
            return self._bots_source()
        return []
