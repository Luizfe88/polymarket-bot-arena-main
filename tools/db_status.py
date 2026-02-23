import sqlite3
from pathlib import Path


def summarize(db_path: Path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    tables = [r["name"] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if "trades" not in tables:
        return f"{db_path.name}: sem tabela trades"
    total = cur.execute("SELECT COUNT(*) c FROM trades").fetchone()["c"]
    pending = cur.execute("SELECT COUNT(*) c FROM trades WHERE outcome IS NULL").fetchone()["c"]
    resolved = cur.execute(
        "SELECT COUNT(*) c FROM trades WHERE outcome IN ('win','loss','exit_tp','exit_sl','expired')"
    ).fetchone()["c"]
    pnl = cur.execute("SELECT COALESCE(SUM(pnl), 0) s FROM trades WHERE outcome IS NOT NULL").fetchone()["s"]
    return f"{db_path.name}: total={total} pending={pending} resolved={resolved} pnl={float(pnl):+.2f}"


def main():
    root = Path(__file__).resolve().parent.parent
    for db in sorted(root.glob("*.db")):
        if db.name == "long_term_accumulation.db":
            continue
        print(summarize(db))


if __name__ == "__main__":
    main()

