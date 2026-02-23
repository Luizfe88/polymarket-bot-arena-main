import sqlite3
from pathlib import Path

# Testar a consulta SQL usada no endpoint
db_path = Path("bot_arena_paper_test_10.db")

if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Executar a mesma consulta do endpoint
    cursor.execute("""
        SELECT 
            t.id,
            t.bot_name,
            t.market_question,
            t.side,
            t.amount,
            t.shares_bought,
            t.created_at
        FROM trades t
        WHERE t.outcome IS NULL
        ORDER BY t.created_at DESC
    """)
    
    rows = cursor.fetchall()
    print(f"Encontradas {len(rows)} posições em aberto")
    
    for row in rows:
        print(f"ID: {row['id']}, Bot: {row['bot_name']}, Side: {row['side']}, Amount: ${row['amount']}, Shares: {row['shares_bought']}")
    
    conn.close()
else:
    print("Banco de dados não encontrado")