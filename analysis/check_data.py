import sqlite3
from datetime import datetime, timedelta

# Connect to the database
conn = sqlite3.connect('bot_arena_paper_test_10.db')
cursor = conn.cursor()

# Check what data we have in the last 6 hours
cutoff = (datetime.utcnow() - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S")
print(f"Cutoff time: {cutoff}")

# Query for 6h performance data
cursor.execute("""
    SELECT bot_name, COUNT(*) as trades,
           SUM(CASE WHEN outcome IN ('win', 'exit_tp') THEN 1 ELSE 0 END) as wins,
           SUM(CASE WHEN outcome IN ('loss', 'exit_sl') THEN 1 ELSE 0 END) as losses,
           AVG(pnl_usd) as avg_pnl,
           SUM(pnl_usd) as total_pnl
    FROM trades
    WHERE created_at >= ?
    GROUP BY bot_name
    ORDER BY total_pnl DESC
""", (cutoff,))