import sqlite3
from datetime import datetime, timedelta

# Connect to the database
conn = sqlite3.connect('bot_arena_paper_test_10.db')
cursor = conn.cursor()

# Test the get_bot_performance function logic
def test_get_bot_performance(bot_name, hours=6):
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        SELECT
            COUNT(*) as total_trades,
            SUM(CASE WHEN outcome IN ('win', 'exit_tp') THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN outcome IN ('loss', 'exit_sl') THEN 1 ELSE 0 END) as losses,
            COALESCE(SUM(pnl), 0) as total_pnl,
            COALESCE(AVG(pnl), 0) as avg_pnl
        FROM trades
        WHERE bot_name=? AND created_at>=? AND outcome IN ('win', 'loss', 'exit_tp', 'exit_sl')
    """, (bot_name, cutoff))