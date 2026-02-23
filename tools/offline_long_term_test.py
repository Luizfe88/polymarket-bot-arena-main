import json
import sqlite3
from pathlib import Path


def main():
    path = Path(__file__).resolve().parent.parent / "long_term_accumulation.db"
    if not path.exists():
        raise SystemExit(f"DB não encontrado: {path}")

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    tables = [r["name"] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print(f"db={path.name} size={path.stat().st_size} tables={tables}")

    if "trades" in tables:
        table = "trades"
    elif "backtest_trades" in tables:
        table = "backtest_trades"
    else:
        raise SystemExit("Nenhuma tabela de trades encontrada (trades/backtest_trades)")

    cols = [r["name"] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]
    print(f"{table}.columns={cols}")

    total = cur.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"]
    print(f"{table}.total={total}")

    common_cols = set(cols)
    if {"outcome", "pnl"}.issubset(common_cols):
        resolved = cur.execute(f"SELECT COUNT(*) AS c FROM {table} WHERE outcome IS NOT NULL").fetchone()["c"]
        pnl = cur.execute(f"SELECT COALESCE(SUM(pnl), 0) AS s FROM {table} WHERE outcome IS NOT NULL").fetchone()["s"]
        wins = cur.execute(f"SELECT COUNT(*) AS c FROM {table} WHERE pnl > 0").fetchone()["c"]
        losses = cur.execute(f"SELECT COUNT(*) AS c FROM {table} WHERE pnl < 0").fetchone()["c"]
        print(f"{table}.resolved={resolved} pnl={float(pnl):+.2f} wins={wins} losses={losses}")
    elif "net_pnl" in common_cols:
        net = cur.execute(f"SELECT COALESCE(SUM(net_pnl), 0) AS s FROM {table}").fetchone()["s"]
        wins = cur.execute(f"SELECT COUNT(*) AS c FROM {table} WHERE net_pnl > 0").fetchone()["c"]
        losses = cur.execute(f"SELECT COUNT(*) AS c FROM {table} WHERE net_pnl < 0").fetchone()["c"]
        avg_ret = cur.execute(f"SELECT COALESCE(AVG(return_pct), 0) AS a FROM {table}").fetchone()["a"]
        costs = cur.execute(f"SELECT COALESCE(SUM(total_costs), 0) AS s FROM {table}").fetchone()["s"]
        print(f"{table}.net_pnl={float(net):+.2f} wins={wins} losses={losses} avg_return_pct={float(avg_ret):+.3f} costs={float(costs):+.2f}")

    sample_cols = [c for c in ("bot_name", "market_id", "side", "amount", "confidence", "outcome", "pnl", "trade_features") if c in common_cols]
    if sample_cols:
        q = f"SELECT {', '.join(sample_cols)} FROM {table} ORDER BY rowid DESC LIMIT 5"
        sample = cur.execute(q).fetchall()
        for r in sample:
            row = dict(r)
            tf = row.get("trade_features")
            ok = None
            if tf:
                try:
                    obj = json.loads(tf)
                    ok = isinstance(obj, (dict, list))
                except Exception:
                    ok = False
            if "trade_features" in row:
                row["trade_features_json"] = ok
                row.pop("trade_features", None)
            print(f"sample {row}")


if __name__ == "__main__":
    main()

