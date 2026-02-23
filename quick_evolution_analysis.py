import db

# Análise rápida dos bots ativos
with db.get_conn() as conn:
    # Verificar trades dos 5 bots atuais
    print("=== ANÁLISE DOS 5 BOTS ATUAIS ===")
    current_bots = ['momentum-g3-140', 'hybrid-g3-625', 'mean_reversion-g5-606', 'mean_reversion_sl-g5-776', 'orderflow-v1']
    
    total_trades = 0
    total_resolved = 0
    
    for bot in current_bots:
        trades = conn.execute("SELECT COUNT(*) FROM trades WHERE bot_name = ?", (bot,)).fetchone()[0]
        resolved = conn.execute("SELECT COUNT(*) FROM trades WHERE bot_name = ? AND resolved = 1", (bot,)).fetchone()[0]
        
        print(f"{bot}: {trades} trades | {resolved} resolvidos")
        total_trades += trades
        total_resolved += resolved
    
    print(f"\nTOTAL: {total_trades} trades | {total_resolved} resolvidos")
    
    # Verificar velocidade de trades por dia
    print("\n=== VELOCIDADE DE TRADES ===")
    daily_data = conn.execute("""
        SELECT DATE(created_at) as date, COUNT(*) as trades
        FROM trades 
        WHERE bot_name IN (?, ?, ?, ?, ?)
        GROUP BY DATE(created_at)
        ORDER BY date DESC
        LIMIT 7
    """, current_bots).fetchall()
    
    if daily_data:
        trades_per_day = sum(row[1] for row in daily_data) / len(daily_data)
        print(f"Média: {trades_per_day:.1f} trades/dia")
        print(f"Para 40 trades mínimos: {40/trades_per_day:.1f} dias")
        print(f"Para 20 trades mínimos: {20/trades_per_day:.1f} dias")
    
    # Verificar se há geração snapshots
    print("\n=== EVOLUÇÃO POR GERAÇÃO ===")
    snapshots = conn.execute("""
        SELECT bot_name, generation, COUNT(*) as count
        FROM generation_snapshots 
        GROUP BY bot_name, generation
        ORDER BY bot_name, generation DESC
    """).fetchall()
    
    if snapshots:
        for bot, gen, count in snapshots:
            print(f"{bot}: G{gen} ({count} snapshots)")
    else:
        print("Ainda sem snapshots de geração")
    
    # Verificar última evolução
    print("\n=== ÚLTIMA EVOLUÇÃO ===")
    last_evolution = conn.execute("SELECT MAX(cycle_number) FROM evolution_log").fetchone()
    if last_evolution and last_evolution[0]:
        print(f"Último ciclo: #{last_evolution[0]}")
        
        # Ver quando foi
        last_time = conn.execute("SELECT MAX(timestamp) FROM evolution_log").fetchone()
        if last_time and last_time[0]:
            print(f"Última evolução: {last_time[0]}")
    else:
        print("Ainda sem evoluções registradas")