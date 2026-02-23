import sqlite3

# Conectar ao banco de dados
conn = sqlite3.connect('bot_arena_paper_test_10.db')
cursor = conn.cursor()

# Procurar por orderflow especificamente
cursor.execute("SELECT DISTINCT bot_name FROM trades WHERE bot_name LIKE '%orderflow%'")
orderflow_bots = cursor.fetchall()
print('Bots orderflow encontrados:')
for bot in orderflow_bots:
    print(f'  {bot[0]}')

# Verificar quantos trades cada bot tem
cursor.execute('SELECT bot_name, COUNT(*) as count FROM trades GROUP BY bot_name ORDER BY count DESC')
bot_counts = cursor.fetchall()
print('\nTrades por bot:')
for bot, count in bot_counts:
    print(f'  {bot}: {count} trades')

# Verificar últimos trades
cursor.execute("SELECT bot_name, created_at, outcome FROM trades ORDER BY created_at DESC LIMIT 10")
recent_trades = cursor.fetchall()
print('\nÚltimos 10 trades:')
for bot, created_at, outcome in recent_trades:
    print(f'  {bot} em {created_at}: {outcome}')

conn.close()