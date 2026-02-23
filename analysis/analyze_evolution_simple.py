import db

# Verificar estatísticas de trades e desempenho
with db.get_conn() as conn:
    # Total de trades por bot
    print("=== TRADES POR BOT (ATIVOS) ===")
    trades_by_bot = conn.execute("""
        SELECT bot_name, COUNT(*) as total_trades, 
               SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
               AVG(pnl) as avg_pnl,
               SUM(pnl) as total_pnl
        FROM trades 
        WHERE bot_name IN ('momentum-g3-140', 'hybrid-g3-625', 'mean_reversion-g5-606', 'mean_reversion_sl-g5-776', 'orderflow-v1')
        GROUP BY bot_name 
        ORDER BY total_trades DESC
    """).fetchall()
    
    for bot, trades, wins, avg_pnl, total_pnl in trades_by_bot:
        win_rate = (wins/trades*100) if trades > 0 else 0
        print(f"{bot}: {trades} trades | Win Rate: {win_rate:.1f}% | Avg PnL: ${avg_pnl:.2f} | Total: ${total_pnl:.2f}")
    
    # Verificar trades resolvidos recentemente (últimas 6h)
    print("\n=== TRADES RESOLVIDOS RECENTEMENTE (ÚLTIMAS 6h) ===")
    resolved_recent = conn.execute("""
        SELECT bot_name, COUNT(*) as resolved, AVG(pnl) as avg_pnl
        FROM trades 
        WHERE created_at >= datetime('now', '-6 hours') AND resolved_at IS NOT NULL
        AND bot_name IN ('momentum-g3-140', 'hybrid-g3-625', 'mean_reversion-g5-606', 'mean_reversion_sl-g5-776', 'orderflow-v1')
        GROUP BY bot_name
        ORDER BY resolved DESC
    """).fetchall()
    
    if resolved_recent:
        for bot, resolved, avg_pnl in resolved_recent:
            print(f"{bot}: {resolved} trades resolvidos | Avg PnL: ${avg_pnl:.2f}")
    else:
        print("Nenhum trade resolvido nas últimas 6 horas")
    
    # Verificar velocidade média de trades
    print("\n=== VELOCIDADE DE TRADES ===")
    total_trades = conn.execute("""
        SELECT COUNT(*) as total,
               MIN(created_at) as first_trade,
               MAX(created_at) as last_trade
        FROM trades 
        WHERE bot_name IN ('momentum-g3-140', 'hybrid-g3-625', 'mean_reversion-g5-606', 'mean_reversion_sl-g5-776', 'orderflow-v1')
    """).fetchone()
    
    if total_trades and total_trades[0] > 0:
        total_count = total_trades[0]
        print(f"Total de trades dos 5 bots ativos: {total_count}")
        
        # Estimar trades por dia
        from datetime import datetime
        try:
            first = datetime.fromisoformat(total_trades[1].replace('Z', '+00:00'))
            last = datetime.fromisoformat(total_trades[2].replace('Z', '+00:00'))
            days_diff = (last - first).total_seconds() / (24 * 3600)
            
            if days_diff > 0:
                trades_per_day = total_count / days_diff
                print(f"Velocidade: {trades_per_day:.1f} trades/dia")
                print(f"Para 40 trades mínimos: {40/trades_per_day:.1f} dias")
                print(f"Para 20 trades mínimos: {20/trades_per_day:.1f} dias")
        except:
            print("Não foi possível calcular velocidade")
    
    # Verificar gerações
    print("\n=== GERAÇÕES DOS BOTS ATUAIS ===")
    current_bots = ['momentum-g3-140', 'hybrid-g3-625', 'mean_reversion-g5-606', 'mean_reversion_sl-g5-776', 'orderflow-v1']
    for bot in current_bots:
        gen = conn.execute("""
            SELECT generation, COUNT(*) as snapshots
            FROM generation_snapshots 
            WHERE bot_name = ?
            GROUP BY generation
            ORDER BY generation DESC
            LIMIT 1
        """, (bot,)).fetchone()
        
        if gen:
            print(f"{bot}: Geração {gen[0]} | {gen[1]} snapshots")
        else:
            print(f"{bot}: Sem snapshots ainda")