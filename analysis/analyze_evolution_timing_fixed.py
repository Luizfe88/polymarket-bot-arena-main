import db

# Verificar estatísticas de trades e desempenho
with db.get_conn() as conn:
    # Total de trades por bot
    print("=== TRADES POR BOT ===")
    trades_by_bot = conn.execute("""
        SELECT bot_name, COUNT(*) as total_trades, 
               SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
               AVG(pnl) as avg_pnl,
               SUM(pnl) as total_pnl
        FROM trades 
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
        GROUP BY bot_name
        ORDER BY resolved DESC
    """).fetchall()
    
    if resolved_recent:
        for bot, resolved, avg_pnl in resolved_recent:
            print(f"{bot}: {resolved} trades resolvidos | Avg PnL: ${avg_pnl:.2f}")
    else:
        print("Nenhum trade resolvido nas últimas 6 horas")
    
    # Verificar gerações atuais
    print("\n=== GERAÇÕES ATUAIS ===")
    generations = conn.execute("""
        SELECT bot_name, generation, COUNT(*) as snapshots
        FROM generation_snapshots 
        GROUP BY bot_name, generation
        ORDER BY bot_name
    """).fetchall()
    
    if generations:
        for bot, gen, snapshots in generations:
            print(f"{bot}: Geração {gen} | {snapshots} snapshots")
    else:
        print("Nenhum snapshot de geração encontrado")
    
    # Verificar velocidade de trades por dia
    print("\n=== VELOCIDADE DE TRADES ===")
    daily_trades = conn.execute("""
        SELECT DATE(created_at) as date, COUNT(*) as trades
        FROM trades 
        WHERE created_at >= datetime('now', '-7 days')
        GROUP BY DATE(created_at)
        ORDER BY date DESC
    """).fetchall()
    
    if daily_trades:
        print("Trades por dia (últimos 7 dias):")
        for date, trades in daily_trades:
            print(f"  {date}: {trades} trades")
        
        avg_daily = sum(trades for _, trades in daily_trades) / len(daily_trades)
        print(f"Média diária: {avg_daily:.1f} trades")
        print(f"Para atingir 40 trades mínimos: {40/avg_daily:.1f} dias necessários")
    else:
        print("Dados insuficientes para análise diária")