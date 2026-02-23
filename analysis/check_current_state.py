import sqlite3

# Conectar ao banco de dados
conn = sqlite3.connect('bot_arena_paper_test_10.db')
cursor = conn.cursor()

# Verificar bots atuais (últimos 6h)
cursor.execute("""
    SELECT DISTINCT bot_name, COUNT(*) as trade_count
    FROM trades 
    WHERE created_at >= datetime('now', '-6 hours')
    GROUP BY bot_name
    ORDER BY trade_count DESC
""")
recent_bots = cursor.fetchall()
print('Bots ativos nas últimas 6h:')
for bot, count in recent_bots:
    print(f'  {bot}: {count} trades')

# Verificar configurações do orderflow
cursor.execute("SELECT * FROM bot_configs WHERE bot_name LIKE '%orderflow%'")
orderflow_configs = cursor.fetchall()
print('\nConfigurações do orderflow:')
for config in orderflow_configs:
    print(f'  {config}')

# Ver última evolução
cursor.execute("SELECT * FROM evolution_events ORDER BY timestamp DESC LIMIT 1")
last_evolution = cursor.fetchone()
if last_evolution:
    print(f'\nÚltima evolução: {last_evolution}')

# Ver estado da arena
cursor.execute("SELECT * FROM arena_state")
arena_state = cursor.fetchall()
print('\nEstado da arena:')
for state in arena_state:
    print(f'  {state}')

conn.close()