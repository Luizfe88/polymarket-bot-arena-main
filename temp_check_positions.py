import sqlite3

conn = sqlite3.connect('bot_arena_paper_test_10.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute('SELECT id, bot_name, market_question, side, amount, shares_bought, outcome, created_at FROM trades WHERE outcome IS NULL ORDER BY created_at DESC LIMIT 5;')
rows = cursor.fetchall()

print("Posições em aberto:")
print("-" * 80)
for row in rows:
    print(f"ID: {row['id']}")
    print(f"Bot: {row['bot_name']}")
    print(f"Side: {row['side']}")
    print(f"Amount: ${row['amount']:.4f}")
    print(f"Shares bought: {row['shares_bought']}")
    print(f"Outcome: {row['outcome']}")
    print(f"Created: {row['created_at']}")
    print("-" * 40)

conn.close()