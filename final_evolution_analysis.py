import sqlite3
from datetime import datetime, timedelta

# Conectar ao banco de dados
conn = sqlite3.connect('bot_arena_paper_test_10.db')

print("=== ANÁLISE DE EVOLUÇÃO - 6 HORAS ===")
print()

# Verificar trades dos 5 bots atuais
current_bots = ['momentum-g3-140', 'hybrid-g3-625', 'mean_reversion-g5-606', 'mean_reversion_sl-g5-776', 'orderflow-v1']
print("=== STATUS ATUAL DOS BOTS ===")
for bot in current_bots:
    trades = conn.execute("SELECT COUNT(*) FROM trades WHERE bot_name = ?", (bot,)).fetchone()[0]
    resolved = conn.execute("SELECT COUNT(*) FROM trades WHERE bot_name = ? AND resolved_at IS NOT NULL", (bot,)).fetchone()[0]
    print(f"{bot}: {trades} trades | {resolved} resolvidos")

print()

# Verificar velocidade média de trades (últimos 7 dias)
print("=== VELOCIDADE MÉDIA DE TRADES (ÚLTIMOS 7 DIAS) ===")
for bot in current_bots:
    result = conn.execute("""
        SELECT COUNT(*) as count, 
               MIN(created_at) as first_trade,
               MAX(created_at) as last_trade
        FROM trades 
        WHERE bot_name = ? 
        AND created_at >= datetime('now', '-7 days')
    """, (bot,)).fetchone()
    
    count = result[0]
    if count > 0:
        # Calcular dias desde o primeiro trade
        first_trade = datetime.fromisoformat(result[1].replace('Z', '+00:00'))
        last_trade = datetime.fromisoformat(result[2].replace('Z', '+00:00'))
        days_diff = (last_trade - first_trade).total_seconds() / 86400  # segundos para dias
        trades_per_day = count / max(days_diff, 0.1)  # evitar divisão por zero
        print(f"{bot}: {count} trades em {days_diff:.1f} dias = {trades_per_day:.1f} trades/dia")
        
        print(f"  Para 40 trades mínimos: {40/trades_per_day:.1f} dias")
        print(f"  Para 20 trades mínimos: {20/trades_per_day:.1f} dias")
        print(f"  Para 10 trades mínimos: {10/trades_per_day:.1f} dias")
    else:
        print(f"{bot}: Nenhum trade nos últimos 7 dias")

print()

# Verificar se há geração snapshots
print("=== EVOLUÇÃO POR GERAÇÃO ===")
snapshots = conn.execute("""
    SELECT bot_name, generation, COUNT(*) as count
    FROM generation_snapshots 
    GROUP BY bot_name, generation
    ORDER BY bot_name, generation
""").fetchall()

if snapshots:
    for bot, gen, count in snapshots:
        print(f"{bot} geração {gen}: {count} snapshots")
else:
    print("Nenhum snapshot de geração encontrado")

print()

# Verificar trades resolvidos recentemente (últimas 6h)
print("=== TRADES RESOLVIDOS RECENTEMENTE (ÚLTIMAS 6h) ===")
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

print()

# Análise de tempo de evolução
print("=== ANÁLISE DE TEMPO DE EVOLUÇÃO ===")
print("Com 6 horas de intervalo:")
print("- Os bots terão mais tempo para acumular trades e desempenho")
print("- Menos pressão para evolução prematura")
print("- Ciclos de evolução mais estáveis")
print("- Melhor diversificação de estratégias")

# Calcular trades médios por ciclo de 6h
trades_per_6h = []
for bot in current_bots:
    result = conn.execute("""
        SELECT COUNT(*) as count
        FROM trades 
        WHERE bot_name = ? 
        AND created_at >= datetime('now', '-6 hours')
    """, (bot,)).fetchone()
    trades_per_6h.append(result[0])

avg_trades_6h = sum(trades_per_6h) / len(trades_per_6h) if trades_per_6h else 0
print(f"\nMédia de trades por bot em 6h: {avg_trades_6h:.1f}")

if avg_trades_6h > 0:
    cycles_to_40 = 40 / avg_trades_6h
    print(f"Ciclos de 6h necessários para 40 trades: {cycles_to_40:.1f} = {cycles_to_40 * 6:.1f} horas")
    print(f"Isso equivale a {(cycles_to_40 * 6) / 24:.1f} dias")

conn.close()