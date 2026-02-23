import sqlite3

# Conectar ao banco de dados
conn = sqlite3.connect('bot_arena_paper_test_10.db')
cursor = conn.cursor()

# Ver estrutura da tabela evolution_events
cursor.execute("PRAGMA table_info(evolution_events)")
columns = cursor.fetchall()
print('Colunas da tabela evolution_events:')
for col in columns:
    print(f'  {col[0]}: {col[1]} ({col[2]})')

# Ver últimas evoluções
cursor.execute("SELECT * FROM evolution_events ORDER BY created_at DESC LIMIT 5")
evolution_events = cursor.fetchall()
print('\nÚltimas 5 evoluções:')
for event in evolution_events:
    print(f'  {event}')

# Ver estado atual da arena
cursor.execute("SELECT * FROM arena_state ORDER BY id")
arena_state = cursor.fetchall()
print('\nEstado atual da arena:')
for state in arena_state:
    print(f'  {state}')

# Ver geração atual
cursor.execute("SELECT MAX(generation) FROM bot_configs")
max_generation = cursor.fetchone()[0]
print(f'\nGeração máxima: {max_generation}')

# Ver bots ativos por geração
cursor.execute("SELECT generation, COUNT(*) as count FROM bot_configs WHERE is_active = 1 GROUP BY generation ORDER BY generation DESC")
generation_counts = cursor.fetchall()
print('\nBots ativos por geração:')
for gen, count in generation_counts:
    print(f'  G{gen}: {count} bots')

conn.close()