# debug_clob4.py
import requests, base64, json

headers = {"User-Agent": "PolymarketBotArena/3.0"}

print("=== Vasculhando região 140000-160000 para achar BTC/ETH Up or Down ===")

for offset in [140000, 145000, 148000, 150000, 152000, 155000, 160000]:
    cursor = base64.b64encode(str(offset).encode()).decode()
    r = requests.get("https://clob.polymarket.com/markets", params={
        "limit": 500, "next_cursor": cursor
    }, headers=headers, timeout=15)
    
    data = r.json()
    markets = data.get("data", [])
    
    updown = [m for m in markets if "up or down" in (m.get("question") or "").lower()]
    
    print(f"\noffset {offset}: total={len(markets)} | up_or_down={len(updown)}")
    for m in updown[:5]:
        print(f"  Q: {m.get('question')}")
        print(f"     slug: {m.get('market_slug')}")
        print(f"     end: {m.get('end_date_iso')}")
        print(f"     active: {m.get('active')} | accepting_orders: {m.get('accepting_orders')}")
        print(f"     tags: {m.get('tags')}")
        toks = m.get("tokens", [])
        for t in toks:
            print(f"     token: {t}")