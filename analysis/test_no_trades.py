import sqlite3
from datetime import datetime, timedelta

# Connect to the database
conn = sqlite3.connect('bot_arena_paper_test_10.db')
cursor = conn.cursor()

# Test with a bot that might not have recent trades
def test_bot_with_no_trades(bot_name, hours=6):
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        SELECT
            COUNT(*) as total_trades,
            SUM(CASE WHEN outcome IN ('win', 'exit_tp') THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN outcome IN ('loss', 'exit_sl') THEN 1 ELSE 0 END) as losses
        FROM trades
        WHERE bot_name = ? AND created_at >= ?
    """, (bot_name, cutoff))