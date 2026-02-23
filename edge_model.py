import json
import math
import time
import db
import config


_CACHE = {}
_CACHE_TTL_SEC = 30


def _sigmoid(z: float) -> float:
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)


def _logit(p: float) -> float:
    p = max(1e-6, min(1.0 - 1e-6, p))
    return math.log(p / (1.0 - p))


def _ensure_schema():
    with db.get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bot_models (
                bot_name TEXT PRIMARY KEY,
                bias REAL NOT NULL,
                weights TEXT NOT NULL,
                updated_at TEXT DEFAULT (datetime('now'))
            );
        """)


def _default_weights() -> dict:
    return {
        "mom": 0.40,
        "vol": -0.25,
        "tte": 0.10,
        "strat": 0.35,
        "sent": 0.10,
        "of_delta": 0.20,
        "of_vol": 0.05,
        "stale": -0.30,
    }


def get_model(bot_name: str) -> tuple[float, dict]:
    _ensure_schema()
    now = time.time()
    cached = _CACHE.get(bot_name)
    if cached and (now - cached["ts"] < _CACHE_TTL_SEC):
        return cached["bias"], cached["weights"]

    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT bias, weights FROM bot_models WHERE bot_name=?",
            (bot_name,),
        ).fetchone()

        if not row:
            bias = 0.0
            weights = _default_weights()
            conn.execute(
                "INSERT INTO bot_models (bot_name, bias, weights) VALUES (?, ?, ?)",
                (bot_name, bias, json.dumps(weights)),
            )
        else:
            bias = float(row["bias"])
            try:
                weights = json.loads(row["weights"]) if row["weights"] else {}
            except json.JSONDecodeError:
                weights = {}
            if not isinstance(weights, dict) or not weights:
                weights = _default_weights()

    _CACHE[bot_name] = {"ts": now, "bias": bias, "weights": weights}
    return bias, weights


def predict_yes_probability(bot_name: str, market_yes_price: float, x: dict) -> float:
    bias, weights = get_model(bot_name)
    base = _logit(max(1e-3, min(1.0 - 1e-3, market_yes_price)))
    delta = bias
    for k, w in weights.items():
        try:
            delta += float(w) * float(x.get(k, 0.0))
        except (TypeError, ValueError):
            continue
    return max(0.01, min(0.99, _sigmoid(base + delta)))


def update_model(bot_name: str, market_yes_price: float, x: dict, y_yes_win: int) -> dict:
    _ensure_schema()
    y = 1.0 if int(y_yes_win) == 1 else 0.0
    lr = getattr(config, "MODEL_LR", 0.05)
    l2 = getattr(config, "MODEL_L2", 1e-4)

    bias, weights = get_model(bot_name)
    p = predict_yes_probability(bot_name, market_yes_price, x)
    err = (y - p)

    bias = bias + lr * err
    for k in list(weights.keys()):
        try:
            xv = float(x.get(k, 0.0))
        except (TypeError, ValueError):
            xv = 0.0
        weights[k] = float(weights.get(k, 0.0)) + lr * (err * xv - l2 * float(weights.get(k, 0.0)))

    with db.get_conn() as conn:
        conn.execute(
            "UPDATE bot_models SET bias=?, weights=?, updated_at=datetime('now') WHERE bot_name=?",
            (float(bias), json.dumps(weights), bot_name),
        )

    _CACHE[bot_name] = {"ts": time.time(), "bias": bias, "weights": weights}
    return {"p": p, "y": y, "err": err}

