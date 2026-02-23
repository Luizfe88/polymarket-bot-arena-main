import sqlite3

# Conectar ao banco de dados
conn = sqlite3.connect('bot_arena_paper_test_10.db')
cursor = conn.cursor()

# Verificar tabela de configurações
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Tabelas no banco:')
for table in tables:
    print(f'  {table[0]}')

# Verificar bots na tabela de configurações
if 'bot_configs' in [t[0] for t in tables]:
    cursor.execute("SELECT bot_name FROM bot_configs")
    config_bots = cursor.fetchall()
    print('\nBots na tabela bot_configs:')
    for bot in config_bots:
        print(f'  {bot[0]}')

# Verificar se orderflow está em algum lugar
cursor.execute("SELECT * FROM trades WHERE bot_name LIKE '%orderflow%' LIMIT 5")
orderflow_trades = cursor.fetchall()
if orderflow_trades:
    print('\nTrades do orderflow encontrados:')
    for trade in orderflow_trades:
        print(f'  {trade}')
else:
    print('\nNenhum trade do orderflow encontrado')

conn.close()