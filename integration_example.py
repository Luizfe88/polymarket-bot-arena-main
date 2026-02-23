def run_evolution(bots, cycle_number):
    """Versão modificada que integra com o novo sistema"""
    
    # PRIMEIRO: Verifica se deve usar evolução por trades ou evolução regular
    if evolution_integration.should_run_regular_evolution():
        # Usa evolução regular (4h) - mantém código existente
        logger.info("=== Usando evolução regular (4h) ===")
        return run_regular_evolution(bots, cycle_number)
    else:
        # Usa evolução por trades - novo sistema
        logger.info("=== Usando evolução por trades ===")
        return run_trade_based_evolution(bots, cycle_number)


def run_regular_evolution(bots, cycle_number):
    """Mantém código original de evolução"""
    # ... código existente de evolução ...
    pass


def run_trade_based_evolution(bots, cycle_number):
    """Nova função que usa o sistema de evolução por trades"""
    
    # Obtém rankings de performance
    rankings = []
    for bot in bots:
        perf = bot.get_performance(hours=6)  # Últimas 6 horas
        trades = perf.get("total_trades", 0)
        pnl = perf.get("total_pnl", 0)
        win_rate = perf.get("win_rate", 0)
        
        # Calcula score
        score = pnl + (win_rate - 0.5) * 2.0
        
        rankings.append({
            "bot": bot,
            "name": bot.name,
            "strategy_type": bot.strategy_type,
            "pnl": pnl,
            "win_rate": win_rate,
            "trades": trades,
            "score": score,
        })
    
    # Ordena por performance
    rankings.sort(key=lambda x: x["score"], reverse=True)
    
    # Seleciona sobreviventes (top 3)
    survivors = rankings[:3]
    survivor_bots = [r["bot"] for r in survivors]
    
    # Identifica bots para substituir
    replaced = rankings[3:]
    
    # Cria novos bots evoluídos
    new_bots = []
    for dead_rank in replaced:
        dead_bot = dead_rank["bot"]
        
        # Seleciona parent (melhor performer)
        parent = survivors[0]["bot"]
        
        # Cria bot evoluído
        evolved = create_evolved_bot(parent, dead_bot.strategy_type, cycle_number)
        
        # Copia configurações do bot antigo
        if hasattr(dead_bot, '_api_key_slot'):
            evolved._api_key_slot = dead_bot._api_key_slot
        
        new_bots.append(evolved)
        
        # Registra no banco
        db.retire_bot(dead_bot.name)
        db.save_bot_config(
            evolved.name, evolved.strategy_type, evolved.generation,
            evolved.strategy_params, evolved.lineage
        )
    
    # Retorna lista final: sobreviventes + novos
    return survivor_bots + new_bots
"""

"""
# 3. MODIFICAR O LOOP PRINCIPAL PARA MONITORAR TRADES RESOLVIDOS

def main_loop():
    """Loop principal modificado"""
    
    bots = create_default_bots()
    evolution_manager = BotEvolutionManager()
    
    while True:
        try:
            # ... código existente de trading ...
            
            # NOVO: Verifica trades resolvidos
            check_resolved_trades(bots)
            
            # Verifica se deve executar evolução
            evolution_manager.evaluate_evolution_trigger()
            
            time.sleep(TRADE_INTERVAL)
            
        except Exception as e:
            logger.error(f"Erro no loop principal: {e}")
            time.sleep(60)


def check_resolved_trades(bots):
    """Verifica e notifica trades resolvidos"""
    
    for bot in bots:
        try:
            # Obtém trades resolvidos recentemente
            resolved_trades = bot.get_recently_resolved_trades()
            
            for trade in resolved_trades:
                # Notifica sistema de evolução
                trade_data = {
                    'market_id': trade.market_id,
                    'outcome': trade.outcome,
                    'pnl': trade.pnl,
                    'resolved_at': trade.resolved_at
                }
                
                on_trade_resolved(bot.name, trade_data)
                
        except Exception as e:
            logger.error(f"Erro ao verificar trades de {bot.name}: {e}")
"""

"""
# 4. ADICIONAR COMANDO TELEGRAM PARA MONITORAR EVOLUÇÃO

def telegram_evolution_status(update, context):
    """Comando /evolution_status para Telegram"""
    
    try:
        status = evolution_integration.get_evolution_status()
        
        message = f"""🧬 *Status da Evolução*
        
📊 Trades: {status['global_trade_count']}/{status['target_trades']} ({status['progress_percent']:.1f}%)
⏰ Última evolução: {status['time_since_last_evolution']}
🔒 Cooldown: {'Ativo' if status['cooldown_active'] else 'Livre'}
🎯 Status: {'Pode evoluir' if status['can_evolve'] else 'Aguardando'}
        
🎯 Gatilhos:
• Trade Threshold: {'✅' if status['global_trade_count'] >= status['target_trades'] else '❌'}
• Safety Net (8h): {'✅' if not status['cooldown_active'] else '❌'}
        """
        
        update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        update.message.reply_text(f"Erro ao obter status: {e}")


def telegram_force_evolution(update, context):
    """Comando /force_evolution para Telegram"""
    
    try:
        success = evolution_integration.force_evolution()
        
        if success:
            update.message.reply_text("🚀 Evolução forçada iniciada!")
        else:
            update.message.reply_text("❌ Evolução já em progresso")
            
    except Exception as e:
        update.message.reply_text(f"Erro ao forçar evolução: {e}")


def main():
    """Função principal de demonstração"""
    
    print("🧬 Sistema de Evolução por Trades")
    print("="*50)
    print("Este script mostra como integrar o novo sistema com arena.py")
    print("\nPrincipais modificações necessárias:")
    print("1. Adicionar imports no início do arena.py")
    print("2. Modificar função run_evolution() para verificar tipo de evolução")
    print("3. Adicionar verificação de trades resolvidos no loop principal")
    print("4. Adicionar comandos Telegram para monitoramento")
    print("\nUse monitor_evolution.py para ver o sistema em ação!")


if __name__ == "__main__":
    main()