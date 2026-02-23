"""Telegram bot commands for Polymarket Bot Arena management."""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pytz
import requests
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent))
import config
import db
from telegram_notifier import get_telegram_notifier
from evolution_integration import get_evolution_status


class TelegramCommands:
    """Handler for Telegram bot commands."""
    
    def __init__(self):
        self.brt_tz = pytz.timezone('America/Sao_Paulo')
        self.command_handlers = {
            '/bots': self.handle_bots,
            '/reset': self.handle_reset,
            '/evolucao': self.handle_evolucao,
            '/evolução': self.handle_evolucao,  # Alternative spelling
            '/trades': self.handle_trades,
            '/status': self.handle_status,
            '/help': self.handle_help,
            '/start': self.handle_start,
            '/ranking': self.handle_ranking,
            '/performance': self.handle_performance,
            '/resumo': self.handle_resumo,
            '/evolucao_trades': self.handle_evolucao_trades,
            '/trades_recentes': self.handle_trades_recentes,
        }
    
    def get_current_time_brt(self) -> str:
        """Get current time in BRT timezone."""
        return datetime.now(self.brt_tz).strftime("%d/%m/%Y %H:%M:%S")
    
    def format_currency(self, value: float) -> str:
        """Format currency with colors based on value."""
        if value >= 0:
            return f"<code>${value:.2f}</code> ✅"
        else:
            return f"<code>${value:.2f}</code> 🔴"
    
    def format_percentage(self, value: float) -> str:
        """Format percentage with colors."""
        if value >= 0:
            return f"<code>{value:.2f}%</code> 🟢"
        else:
            return f"<code>{value:.2f}%</code> 🔴"
    
    def handle_start(self, user_id: str) -> str:
        """Handle /start command."""
        return f"""
🤖 <b>Polymarket Bot Arena - Telegram Bot</b>

📅 <b>Conectado:</b> {self.get_current_time_brt()}

<b>Comandos disponíveis:</b>

📊 <b>Análise:</b>
• /bots - P&L de cada bot
• /status - Capital total e disponível
• /trades - Trades abertas
• /evolucao - Evolução do capital
• /ranking - Ranking dos bots
• /performance - Performance recente

⚙️ <b>Controle:</b>
• /reset - Resetar todos os bots
• /resumo - Resumo geral

❓ <b>Ajuda:</b>
• /help - Mostrar este menu

<i>Horário: Brasília (BRT - UTC-3)</i>
"""
    
    def handle_help(self, user_id: str) -> str:
        """Handle /help command."""
        return self.handle_start(user_id)
    
    def handle_bots(self, user_id: str) -> str:
        """Handle /bots command - Show P&L for each bot."""
        try:
            mode = config.get_current_mode()
            with db.get_conn() as conn:
                # Get all bots with their current P&L
                bots_data = conn.execute("""
                    SELECT 
                        bot_name,
                        SUM(CASE WHEN side = 'yes' THEN amount ELSE -amount END) as total_invested,
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN pnl IS NOT NULL THEN pnl ELSE 0 END) as total_pnl
                    FROM trades 
                    WHERE mode = ? 
                    GROUP BY bot_name
                    ORDER BY total_pnl DESC
                """, (mode,)).fetchall()
                
                if not bots_data:
                    return "📊 <b>P&L dos Bots</b>\n\n<i>Nenhum bot ativo ou trades encontrados.</i>"
                
                message = f"📊 <b>P&L dos Bots - {mode.upper()}</b>\n"
                message += f"📅 <b>Atualizado:</b> {self.get_current_time_brt()}\n\n"
                
                for bot in bots_data:
                    bot_name = bot['bot_name']
                    total_pnl = float(bot['total_pnl'] or 0)
                    total_trades = bot['total_trades']
                    
                    # Get recent performance (last 24h)
                    recent_perf = conn.execute("""
                        SELECT SUM(pnl) as recent_pnl, COUNT(*) as recent_trades
                        FROM trades 
                        WHERE bot_name = ? AND mode = ? 
                        AND created_at >= datetime('now', '-1 day')
                    """, (bot_name, mode)).fetchone()
                    
                    recent_pnl = float(recent_perf['recent_pnl'] or 0) if recent_perf else 0
                    recent_trades = recent_perf['recent_trades'] if recent_perf else 0
                    
                    # Bot status
                    is_paused = self.is_bot_paused(bot_name, mode)
                    status_emoji = "⏸️" if is_paused else "🟢"
                    
                    message += f"{status_emoji} <b>{bot_name}</b>\n"
                    message += f"   💰 P&L Total: {self.format_currency(total_pnl)}\n"
                    message += f"   📈 24h: {self.format_currency(recent_pnl)} ({recent_trades} trades)\n"
                    message += f"   🎯 Trades: <code>{total_trades}</code>\n\n"
                
                # Summary
                total_pnl_all = sum(float(bot['total_pnl'] or 0) for bot in bots_data)
                total_trades_all = sum(bot['total_trades'] for bot in bots_data)
                
                message += f"📈 <b>Resumo Geral:</b>\n"
                message += f"💰 P&L Total: {self.format_currency(total_pnl_all)}\n"
                message += f"🎯 Trades Totais: <code>{total_trades_all}</code>\n"
                
                return message
                
        except Exception as e:
            return f"❌ Erro ao buscar P&L dos bots: {str(e)}"
    
    def handle_status(self, user_id: str) -> str:
        """Handle /status command - Show capital status."""
        try:
            mode = config.get_current_mode()
            
            # Get total capital
            total_capital = db.get_total_current_capital(mode)
            
            # Get invested capital (sum of all open positions)
            with db.get_conn() as conn:
                invested_data = conn.execute("""
                    SELECT 
                        SUM(amount) as total_invested,
                        COUNT(DISTINCT bot_name) as active_bots
                    FROM trades 
                    WHERE mode = ? 
                    AND market_id IN (
                        SELECT market_id FROM trades 
                        WHERE mode = ? 
                        GROUP BY market_id 
                        HAVING COUNT(*) % 2 = 1
                    )
                """, (mode, mode)).fetchone()
                
                total_invested = float(invested_data['total_invested'] or 0)
                active_bots = invested_data['active_bots'] or 0
                
                # Get available capital per bot
                available_per_bot = conn.execute("""
                    SELECT bot_name, 
                           (SELECT CASE WHEN mode = 'paper' THEN 1000 ELSE 100 END) - 
                           COALESCE(SUM(amount), 0) as available
                    FROM trades 
                    WHERE mode = ?
                    GROUP BY bot_name
                """, (mode,)).fetchall()
            
            available_capital = total_capital - total_invested
            
            message = f"💰 <b>Status do Capital - {mode.upper()}</b>\n"
            message += f"📅 <b>Atualizado:</b> {self.get_current_time_brt()}\n\n"
            
            message += f"🏦 <b>Capital Total:</b> <code>${total_capital:.2f}</code>\n"
            message += f"💼 <b>Capital Investido:</b> <code>${total_invested:.2f}</code>\n"
            message += f"💵 <b>Capital Disponível:</b> <code>${available_capital:.2f}</code>\n"
            message += f"🤖 <b>Bots Ativos:</b> <code>{active_bots}</code>\n\n"
            
            if available_per_bot:
                message += f"📊 <b>Disponível por Bot:</b>\n"
                for bot in available_per_bot[:5]:  # Show top 5
                    bot_name = bot['bot_name']
                    available = float(bot['available'] or 0)
                    message += f"• {bot_name}: <code>${available:.2f}</code>\n"
                
                if len(available_per_bot) > 5:
                    message += f"<i>... e mais {len(available_per_bot) - 5} bots</i>\n"
            
            # Today's performance
            today_pnl = self.get_today_pnl(mode)
            if today_pnl != 0:
                message += f"\n📈 <b>P&L Hoje:</b> {self.format_currency(today_pnl)}\n"
            
            return message
            
        except Exception as e:
            return f"❌ Erro ao buscar status do capital: {str(e)}"
    
    def handle_trades(self, user_id: str) -> str:
        """Handle /trades command - Show open trades."""
        try:
            mode = config.get_current_mode()
            
            with db.get_conn() as conn:
                # Get open trades (markets with odd number of trades = open position)
                open_trades = conn.execute("""
                    SELECT 
                        t.bot_name,
                        t.market_question,
                        t.side,
                        t.amount,
                        t.created_at,
                        t.confidence,
                        t.market_id
                    FROM trades t
                    INNER JOIN (
                        SELECT market_id, bot_name
                        FROM trades 
                        WHERE mode = ?
                        GROUP BY market_id, bot_name
                        HAVING COUNT(*) % 2 = 1
                    ) open_pos ON t.market_id = open_pos.market_id AND t.bot_name = open_pos.bot_name
                    WHERE t.mode = ?
                    ORDER BY t.created_at DESC
                    LIMIT 10
                """, (mode, mode)).fetchall()
                
                if not open_trades:
                    return "📈 <b>Trades Abertas</b>\n\n<i>Nenhuma posição aberta no momento.</i>"
                
                message = f"📈 <b>Trades Abertas - {mode.upper()}</b>\n"
                message += f"📅 <b>Atualizado:</b> {self.get_current_time_brt()}\n\n"
                
                for trade in open_trades:
                    bot_name = trade['bot_name']
                    question = trade['market_question'] or trade['market_id']
                    side = trade['side'].upper()
                    amount = float(trade['amount'])
                    created_at = trade['created_at']
                    confidence = float(trade['confidence'] or 0)
                    
                    # Format time ago
                    if created_at:
                        created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        time_ago = self.get_time_ago(created_dt)
                    else:
                        time_ago = "Desconhecido"
                    
                    side_emoji = "📈" if side == "YES" else "📉"
                    
                    message += f"{side_emoji} <b>{bot_name}</b>\n"
                    message += f"📝 <b>Mercado:</b> {question[:50]}{'...' if len(question) > 50 else ''}\n"
                    message += f"💰 <b>Valor:</b> <code>${amount:.2f}</code>\n"
                    message += f"🎯 <b>Lado:</b> {side}\n"
                    if confidence > 0:
                        message += f"🤔 <b>Confiança:</b> <code>{confidence:.1f}%</code>\n"
                    message += f"⏰ <b>Aberta:</b> {time_ago}\n\n"
                
                # Count total open positions
                total_open = conn.execute("""
                    SELECT COUNT(DISTINCT market_id || '_' || bot_name) as total
                    FROM trades 
                    WHERE mode = ?
                    GROUP BY market_id, bot_name
                    HAVING COUNT(*) % 2 = 1
                """, (mode,)).fetchone()
                
                total_positions = total_open['total'] if total_open else 0
                message += f"📊 <b>Total de Posições:</b> <code>{total_positions}</code>\n"
                
                return message
                
        except Exception as e:
            return f"❌ Erro ao buscar trades abertas: {str(e)}"
    
    def handle_evolucao(self, user_id: str) -> str:
        """Handle /evolucao command - Show capital evolution."""
        try:
            mode = config.get_current_mode()
            
            with db.get_conn() as conn:
                # Get daily P&L for the last 7 days
                evolution_data = conn.execute("""
                    SELECT 
                        DATE(created_at) as date,
                        SUM(pnl) as daily_pnl,
                        COUNT(*) as trades,
                        SUM(amount) as volume
                    FROM trades 
                    WHERE mode = ? 
                    AND created_at >= datetime('now', '-7 days')
                    AND pnl IS NOT NULL
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                """, (mode,)).fetchall()
                
                # Check for recent evolution events (last 4 hours)
                recent_evolution = conn.execute("""
                    SELECT cycle_number, created_at, survivors, replaced, new_bots
                    FROM evolution_events 
                    WHERE created_at >= datetime('now', '-4 hours')
                    ORDER BY created_at DESC 
                    LIMIT 1
                """).fetchone()
                
                # Get 6h performance data for all active bots
                bots_6h_data = []
                if evolution_data:
                    # Get list of active bots
                    active_bots = conn.execute("""
                        SELECT DISTINCT bot_name 
                        FROM trades 
                        WHERE mode = ? 
                        AND created_at >= datetime('now', '-7 days')
                    """, (mode,)).fetchall()
                    
                    for bot in active_bots:
                        bot_name = bot['bot_name']
                        perf_6h = db.get_bot_performance(bot_name, hours=6)
                        bots_6h_data.append({
                            'bot_name': bot_name,
                            'pnl_6h': perf_6h.get('total_pnl', 0),
                            'win_rate_6h': perf_6h.get('win_rate', 0),
                            'trades_6h': perf_6h.get('total_trades', 0)
                        })
                
                message = f"📊 <b>Evolução do Capital - {mode.upper()}</b>\n"
                message += f"📅 <b>Período:</b> Últimos 7 dias\n"
                message += f"📅 <b>Atualizado:</b> {self.get_current_time_brt()}\n\n"
                
                # Show recent evolution info if available
                if recent_evolution:
                    cycle_num = recent_evolution['cycle_number']
                    evo_time = datetime.fromisoformat(recent_evolution['created_at'])
                    evo_time_brt = evo_time.replace(tzinfo=pytz.UTC).astimezone(self.brt_tz)
                    survivors = json.loads(recent_evolution['survivors'])
                    replaced = json.loads(recent_evolution['replaced'])
                    
                    message += f"🔄 <b>Evolução Recentemente Detectada</b>\n"
                    message += f"📊 Ciclo: <code>#{cycle_num}</code>\n"
                    message += f"⏰ Horário: <code>{evo_time_brt.strftime('%d/%m %H:%M')}</code>\n"
                    message += f"✅ Sobreviventes: <code>{len(survivors)}</code>\n"
                    message += f"🔄 Substituídos: <code>{len(replaced)}</code>\n\n"
                
                # Show 6h performance data
                if bots_6h_data:
                    message += f"📈 <b>Performance Últimas 6h</b>\n"
                    total_6h_pnl = sum(bot['pnl_6h'] for bot in bots_6h_data)
                    total_6h_trades = sum(bot['trades_6h'] for bot in bots_6h_data)
                    avg_6h_win_rate = (sum(bot['win_rate_6h'] for bot in bots_6h_data) / len(bots_6h_data)) if bots_6h_data else 0
                    
                    message += f"💰 P&L Total 6h: {self.format_currency(total_6h_pnl)}\n"
                    message += f"🎯 Win Rate Médio 6h: {self.format_percentage(avg_6h_win_rate * 100)}\n"
                    message += f"📊 Trades 6h: <code>{total_6h_trades}</code>\n\n"
                
                if not evolution_data:
                    message += "<i>Sem dados de evolução disponíveis.</i>\n\n"
                
                total_pnl_period = 0
                total_trades = 0
                total_volume = 0
                
                for day in evolution_data:
                    date = day['date']
                    daily_pnl = float(day['daily_pnl'] or 0)
                    trades = day['trades']
                    volume = float(day['volume'] or 0)
                    
                    total_pnl_period += daily_pnl
                    total_trades += trades
                    total_volume += volume
                    
                    # Format date
                    if date:
                        date_obj = datetime.fromisoformat(date)
                        formatted_date = date_obj.strftime("%d/%m")
                    else:
                        formatted_date = "Desconhecido"
                    
                    pnl_emoji = "🟢" if daily_pnl >= 0 else "🔴"
                    
                    message += f"{pnl_emoji} <b>{formatted_date}</b>\n"
                    message += f"   💰 P&L: {self.format_currency(daily_pnl)}\n"
                    message += f"   🎯 Trades: <code>{trades}</code>\n"
                    message += f"   📊 Volume: <code>${volume:.2f}</code>\n\n"
                
                # Summary
                message += f"📈 <b>Resumo do Período:</b>\n"
                message += f"💰 P&L Total: {self.format_currency(total_pnl_period)}\n"
                message += f"🎯 Trades: <code>{total_trades}</code>\n"
                message += f"📊 Volume: <code>${total_volume:.2f}</code>\n"
                
                # Calculate average daily P&L
                if len(evolution_data) > 0:
                    avg_daily = total_pnl_period / len(evolution_data)
                    message += f"📈 Média Diária: {self.format_currency(avg_daily)}\n"
                
                return message
                
        except Exception as e:
            return f"❌ Erro ao buscar evolução do capital: {str(e)}"

    def handle_evolucao_trades(self) -> str:
        """Handles the /evolucao_trades command, showing trade-based evolution status."""
        try:
            status = get_evolution_status()
            
            # Header
            message = "🧬 <b>Sistema de Evolução por Trades</b> 🧬\n\n"
            
            # Progress bar for trades
            progress = status['global_trade_count'] / status['target_trades']
            bar_length = 20
            filled_length = int(bar_length * progress)
            bar = '▓' * filled_length + '░' * (bar_length - filled_length)
            message += f"📊 <b>Trades Resolvidos:</b> {status['global_trade_count']}/{status['target_trades']}\n"
            message += f"   <code>[{bar}] {progress:.1%}</code>\n\n"
            
            # Timers
            time_since_evolution = str(timedelta(seconds=int(status['time_since_last_evolution'])))
            message += f"⏰ <b>Última Evolução:</b> {time_since_evolution} atrás\n"
            
            if status['cooldown_active']:
                remaining_cooldown = str(timedelta(seconds=int(status['remaining_cooldown'])))
                message += f"⏳ <b>Cooldown Ativo:</b> {remaining_cooldown} restantes\n\n"
            else:
                message += f"✅ <b>Cooldown:</b> Livre\n\n"

            # Triggers
            message += "🎯 <b>Gatilhos de Evolução:</b>\n"
            if status['triggers']['trade_threshold']:
                message += f"   • Contagem de Trades (100): ✅\n"
            else:
                message += f"   • Contagem de Trades (100): ❌ ({status['global_trade_count']}/{status['target_trades']})\n"
            
            if status['triggers']['safety_net']:
                message += f"   • Safety Net (8h): ✅\n\n"
            else:
                message += f"   • Safety Net (8h): ❌\n\n"

            # Final Status
            if status['can_evolve']:
                message += f"🔥 <b>Status:</b> PODE EVOLUIR\n"
                message += f"   <b>Razão:</b> {status['trigger_reason']}\n"
            else:
                message += f"❄️ <b>Status:</b> AGUARDANDO\n"
            
            return message

        except Exception as e:
            return f"❌ Erro ao buscar status da evolução por trades: {str(e)}"

    def handle_trades_recentes(self) -> str:
        """Handles the /trades_recentes command, showing recent trading activity."""
        try:
            # Get trades from last 15 minutes
            fifteen_min_ago = datetime.now() - timedelta(minutes=15)
            
            with db.get_conn() as conn:
                # Count recent trades
                recent_trades = conn.execute("""
                    SELECT COUNT(*) as count, 
                           SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
                           SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) as losses
                    FROM trades 
                    WHERE resolved_at >= ? 
                    AND outcome IS NOT NULL
                """, (fifteen_min_ago.isoformat(),)).fetchone()
                
                # Get pending trades
                pending = conn.execute("""
                    SELECT COUNT(*) as count
                    FROM trades 
                    WHERE created_at >= ? 
                    AND resolved_at IS NULL
                """, (fifteen_min_ago.isoformat(),)).fetchone()
                
                # Get recent market activity
                markets = conn.execute("""
                    SELECT COUNT(DISTINCT market_id) as unique_markets
                    FROM trades 
                    WHERE created_at >= ?
                """, (fifteen_min_ago.isoformat(),)).fetchone()
                
            message = "📊 <b>Atividade de Trades (Últimos 15min)</b> 📊\n\n"
            
            # Recent trades
            if recent_trades and recent_trades['count'] > 0:
                win_rate = (recent_trades['wins'] / recent_trades['count'] * 100) if recent_trades['count'] > 0 else 0
                message += f"✅ <b>Trades Resolvidos:</b> {recent_trades['count']}\n"
                message += f"   🏆 Vitórias: {recent_trades['wins']} | ❌ Derrotas: {recent_trades['losses']}\n"
                message += f"   📈 Win Rate: {win_rate:.1f}%\n\n"
            else:
                message += f"❌ <b>Trades Resolvidos:</b> Nenhum\n\n"
            
            # Pending trades
            pending_count = pending['count'] if pending else 0
            message += f"⏳ <b>Trades Pendentes:</b> {pending_count}\n"
            
            # Market activity
            markets_count = markets['unique_markets'] if markets else 0
            message += f"🎯 <b>Mercados Ativos:</b> {markets_count}\n\n"
            
            # Overall activity status
            total_activity = (recent_trades['count'] if recent_trades else 0) + pending_count
            if total_activity == 0:
                message += "⚠️ <b>Status:</b> Sem atividade recente\n"
                message += "💡 Os bots estão analisando mercados mas não encontraram oportunidades\n"
            else:
                message += "✅ <b>Status:</b> Ativo\n"
            
            return message
            
        except Exception as e:
            return f"❌ Erro ao buscar trades recentes: {str(e)}"

    
    def handle_reset(self, user_id: str) -> str:
        """Handle /reset command - Reset all bots."""
        try:
            mode = config.get_current_mode()
            
            # Get list of bots before reset
            with db.get_conn() as conn:
                bots = conn.execute("""
                    SELECT DISTINCT bot_name 
                    FROM trades 
                    WHERE mode = ?
                """, (mode,)).fetchall()
                
                bot_names = [bot['bot_name'] for bot in bots]
            
            if not bot_names:
                return "🔄 <b>Resetar Bots</b>\n\n<i>Nenhum bot encontrado para resetar.</i>"
            
            # Reset each bot
            reset_results = []
            for bot_name in bot_names:
                try:
                    # Reset bot state
                    db.set_arena_state(f"unpause:{bot_name}:{mode}", "1")
                    
                    # Reset daily stats
                    db.reset_bot_daily_stats(bot_name, mode)
                    
                    reset_results.append(f"✅ {bot_name}")
                except Exception as e:
                    reset_results.append(f"❌ {bot_name}: {str(e)}")
            
            message = f"🔄 <b>Reset de Bots - {mode.upper()}</b>\n"
            message += f"📅 <b>Realizado:</b> {self.get_current_time_brt()}\n\n"
            
            message += f"<b>Bots Resetados:</b> <code>{len(bot_names)}</code>\n\n"
            
            for result in reset_results:
                message += f"{result}\n"
            
            message += f"\n✅ Todos os bots foram resetados e estão prontos para operar!"
            
            return message
            
        except Exception as e:
            return f"❌ Erro ao resetar bots: {str(e)}"
    
    def handle_ranking(self, user_id: str) -> str:
        """Handle /ranking command - Show bot ranking."""
        try:
            mode = config.get_current_mode()
            
            with db.get_conn() as conn:
                # Get bot ranking by P&L
                ranking_data = conn.execute("""
                    SELECT 
                        bot_name,
                        SUM(CASE WHEN pnl IS NOT NULL THEN pnl ELSE 0 END) as total_pnl,
                        COUNT(*) as total_trades,
                        AVG(CASE WHEN pnl IS NOT NULL THEN pnl ELSE 0 END) as avg_pnl,
                        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                        SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses
                    FROM trades 
                    WHERE mode = ? 
                    AND pnl IS NOT NULL
                    GROUP BY bot_name
                    ORDER BY total_pnl DESC
                """, (mode,)).fetchall()
                
                if not ranking_data:
                    return "🏆 <b>Ranking dos Bots</b>\n\n<i>Nenhum dado de ranking disponível.</i>"
                
                message = f"🏆 <b>Ranking dos Bots - {mode.upper()}</b>\n"
                message += f"📅 <b>Atualizado:</b> {self.get_current_time_brt()}\n\n"
                
                for i, bot in enumerate(ranking_data, 1):
                    bot_name = bot['bot_name']
                    total_pnl = float(bot['total_pnl'] or 0)
                    total_trades = bot['total_trades']
                    avg_pnl = float(bot['avg_pnl'] or 0)
                    wins = bot['wins']
                    losses = bot['losses']
                    
                    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
                    
                    # Medal emoji for top 3
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                    
                    message += f"{medal} <b>{bot_name}</b>\n"
                    message += f"   💰 P&L: {self.format_currency(total_pnl)}\n"
                    message += f"   📊 Win Rate: {self.format_percentage(win_rate)}\n"
                    message += f"   🎯 Trades: <code>{wins}W {losses}L</code>\n"
                    message += f"   📈 Média: {self.format_currency(avg_pnl)}\n\n"
                
                return message
                
        except Exception as e:
            return f"❌ Erro ao buscar ranking: {str(e)}"
    
    def handle_performance(self, user_id: str) -> str:
        """Handle /performance command - Show recent performance."""
        try:
            mode = config.get_current_mode()
            
            with db.get_conn() as conn:
                # Get performance for last 24 hours
                perf_data = conn.execute("""
                    SELECT 
                        bot_name,
                        SUM(CASE WHEN pnl IS NOT NULL THEN pnl ELSE 0 END) as pnl_24h,
                        COUNT(*) as trades_24h,
                        AVG(CASE WHEN pnl IS NOT NULL THEN pnl ELSE 0 END) as avg_pnl,
                        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                        SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses
                    FROM trades 
                    WHERE mode = ? 
                    AND created_at >= datetime('now', '-1 day')
                    AND pnl IS NOT NULL
                    GROUP BY bot_name
                    ORDER BY pnl_24h DESC
                """, (mode,)).fetchall()
                
                if not perf_data:
                    return "⚡ <b>Performance 24h</b>\n\n<i>Nenhuma atividade nas últimas 24 horas.</i>"
                
                message = f"⚡ <b>Performance 24h - {mode.upper()}</b>\n"
                message += f"📅 <b>Período:</b> Últimas 24 horas\n"
                message += f"📅 <b>Atualizado:</b> {self.get_current_time_brt()}\n\n"
                
                total_pnl_24h = 0
                total_trades_24h = 0
                total_wins = 0
                total_losses = 0
                
                for bot in perf_data:
                    bot_name = bot['bot_name']
                    pnl_24h = float(bot['pnl_24h'] or 0)
                    trades_24h = bot['trades_24h']
                    wins = bot['wins']
                    losses = bot['losses']
                    
                    total_pnl_24h += pnl_24h
                    total_trades_24h += trades_24h
                    total_wins += wins
                    total_losses += losses
                    
                    win_rate = (wins / trades_24h * 100) if trades_24h > 0 else 0
                    
                    # Activity indicator
                    activity = "🔥" if trades_24h > 10 else "⚡" if trades_24h > 5 else "🐌"
                    
                    message += f"{activity} <b>{bot_name}</b>\n"
                    message += f"   💰 P&L: {self.format_currency(pnl_24h)}\n"
                    message += f"   🎯 Trades: <code>{trades_24h}</code>\n"
                    message += f"   📊 Win Rate: {self.format_percentage(win_rate)}\n\n"
                
                # Summary
                total_win_rate = (total_wins / total_trades_24h * 100) if total_trades_24h > 0 else 0
                
                message += f"📈 <b>Resumo 24h:</b>\n"
                message += f"💰 P&L Total: {self.format_currency(total_pnl_24h)}\n"
                message += f"🎯 Trades: <code>{total_trades_24h}</code>\n"
                message += f"📊 Win Rate: {self.format_percentage(total_win_rate)}\n"
                message += f"🏆 Vitórias: <code>{total_wins}</code> | 🚫 Derrotas: <code>{total_losses}</code>\n"
                
                return message
                
        except Exception as e:
            return f"❌ Erro ao buscar performance: {str(e)}"
    
    def handle_resumo(self, user_id: str) -> str:
        """Handle /resumo command - Show general summary."""
        try:
            mode = config.get_current_mode()
            
            # Get key metrics
            total_capital = db.get_total_current_capital(mode)
            today_pnl = self.get_today_pnl(mode)
            
            with db.get_conn() as conn:
                # Active bots count
                active_bots_result = conn.execute("""
                    SELECT COUNT(DISTINCT bot_name) as count
                    FROM trades 
                    WHERE mode = ?
                """, (mode,)).fetchone()
                active_bots = active_bots_result['count'] if active_bots_result else 0
                
                # Total trades today
                today_trades_result = conn.execute("""
                    SELECT COUNT(*) as count
                    FROM trades 
                    WHERE mode = ? 
                    AND DATE(created_at) = DATE('now')
                """, (mode,)).fetchone()
                today_trades = today_trades_result['count'] if today_trades_result else 0
                
                # Open positions
                open_positions_result = conn.execute("""
                    SELECT COUNT(DISTINCT market_id || '_' || bot_name) as total
                    FROM trades 
                    WHERE mode = ?
                    GROUP BY market_id, bot_name
                    HAVING COUNT(*) % 2 = 1
                """, (mode,)).fetchone()
                open_positions = open_positions_result['total'] if open_positions_result else 0
            
            message = f"📋 <b>Resumo Geral - {mode.upper()}</b>\n"
            message += f"📅 <b>{self.get_current_time_brt()}</b>\n\n"
            
            # Key metrics
            message += f"💰 <b>Capital:</b> <code>${total_capital:.2f}</code>\n"
            message += f"🤖 <b>Bots:</b> <code>{active_bots}</code>\n"
            message += f"📊 <b>Posições:</b> <code>{open_positions}</code> abertas\n"
            message += f"🎯 <b>Trades Hoje:</b> <code>{today_trades}</code>\n"
            message += f"📈 <b>P&L Hoje:</b> {self.format_currency(today_pnl)}\n\n"
            
            # Quick status indicators
            status_indicators = []
            if today_pnl > 0:
                status_indicators.append("🟢 Lucro no dia")
            elif today_pnl < 0:
                status_indicators.append("🔴 Prejuízo no dia")
            else:
                status_indicators.append("⚪ Neutro no dia")
            
            if active_bots > 0:
                status_indicators.append("⚡ Bots ativos")
            
            if open_positions > 0:
                status_indicators.append("📈 Posições abertas")
            
            message += "📊 <b>Status:</b> " + " | ".join(status_indicators)
            
            return message
            
        except Exception as e:
            return f"❌ Erro ao gerar resumo: {str(e)}"
    
    # Helper methods
    def is_bot_paused(self, bot_name: str, mode: str) -> bool:
        """Check if a bot is paused."""
        try:
            # This is a simplified check - in real implementation you'd check the bot's state
            return False  # Placeholder
        except:
            return False
    
    def get_today_pnl(self, mode: str) -> float:
        """Get today's P&L."""
        try:
            with db.get_conn() as conn:
                result = conn.execute("""
                    SELECT SUM(pnl) as today_pnl
                    FROM trades 
                    WHERE mode = ? 
                    AND DATE(created_at) = DATE('now')
                    AND pnl IS NOT NULL
                """, (mode,)).fetchone()
                
                return float(result['today_pnl'] or 0)
        except:
            return 0
    
    def get_time_ago(self, dt: datetime) -> str:
        """Get human-readable time ago."""
        try:
            now = datetime.now(pytz.UTC)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=pytz.UTC)
            
            diff = now - dt
            
            if diff.days > 0:
                return f"{diff.days}d atrás"
            elif diff.seconds // 3600 > 0:
                return f"{diff.seconds // 3600}h atrás"
            elif diff.seconds // 60 > 0:
                return f"{diff.seconds // 60}m atrás"
            else:
                return "agora"
        except:
            return "Desconhecido"
    
    def process_command(self, command: str, user_id: str) -> str:
        """Process a Telegram command."""
        command = command.lower().strip()
        
        # Remove @bot_username if present
        if '@' in command:
            command = command.split('@')[0]
        
        # Find matching handler
        for cmd, handler in self.command_handlers.items():
            if command.startswith(cmd.lower()):
                return handler(user_id)
        
        return f"❓ Comando não reconhecido: {command}\n\nUse /help para ver os comandos disponíveis."


# Global instance
commands_handler = TelegramCommands()
