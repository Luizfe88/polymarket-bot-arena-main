import db
import sqlite3

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
    
    # Verificar frequência de trades por hora
    print("\n=== FREQUÊNCIA DE TRADES ===")
    hourly_stats = conn.execute("""
        SELECT strftime('%H', timestamp) as hour, COUNT(*) as trades
        FROM trades 
        WHERE timestamp >= datetime('now', '-24 hours')
        GROUP BY hour
        ORDER BY trades DESC
        LIMIT 5
    """).fetchall()
    
    print("Horários mais ativos (últimas 24h):")
    for hour, trades in hourly_stats:
        print(f"  {hour}:00 - {trades} trades")
    
    # Verificar trades resolvidos recentemente
    print("\n=== TRADES RESOLVIDOS RECENTEMENTE ===")
    resolved_recent = conn.execute("""
        SELECT bot_name, COUNT(*) as resolved, AVG(pnl) as avg_pnl
        FROM trades 
        WHERE timestamp >= datetime('now', '-4 hours') AND resolved = 1
        GROUP BY bot_name
        ORDER BY resolved DESC
    """).fetchall()
    
    for bot, resolved, avg_pnl in resolved_recent:
        print(f"{bot}: {resolved} trades resolvidos | Avg PnL: ${avg_pnl:.2f}")
    
    # Verificar gerações atuais
    print("\n=== GERAÇÕES ATUAIS ===")
    generations = conn.execute("""
        SELECT bot_name, generation, COUNT(*) as snapshots
        FROM generation_snapshots 
        GROUP BY bot_name, generation
        ORDER BY bot_name
    """).fetchall()
    
    for bot, gen, snapshots in generations:
        print(f"{bot}: Geração {gen} | {snapshots} snapshots")