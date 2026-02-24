import json
import requests
from datetime import datetime, timedelta

# Buscar mercados para analisar tipos financeiros
now = datetime.now()
start_date = now.strftime('%Y-%m-%dT%H:%M:%SZ')
url = 'https://gamma-api.polymarket.com/markets'
params = {
    'limit': 50,
    'offset': 0,
    'endDateMin': start_date,
    'active': 'true',
    'closed': 'false',
    'archived': 'false',
    'orderBy': 'liquidity',
    'orderDirection': 'desc'
}

response = requests.get(url, params=params)
markets = response.json()

print('Analisando mercados financeiros disponíveis:')
print()

# Palavras-chave para identificar mercados financeiros
finance_keywords = [
    'fed', 'federal reserve', 'interest rate', 'inflation', 'gdp', 'unemployment', 'recession',
    'stock market', 'dow jones', 'nasdaq', 'sp500', 's&p', 'oil', 'gold', 'dollar', 'euro', 'yuan',
    'trade war', 'tariff', 'bond', 'yield', 'treasury', 'fomc', 'rate', 'economic', 'economy',
    'market crash', 'bull market', 'bear market', 'recession', 'inflation', 'deflation',
    'quantitative easing', 'qe', 'interest', 'mortgage', 'housing', 'real estate'
]

finance_markets = []
for market in markets:
    question = market.get('question', '').lower()
    volume = float(market.get('volume', 0))
    liquidity = float(market.get('liquidity', 0))
    
    # Verificar se é financeiro
    is_finance = any(keyword in question for keyword in finance_keywords)
    
    if is_finance:
        finance_markets.append({
            'question': market.get('question'),
            'volume': volume,
            'liquidity': liquidity,
            'keywords_found': [kw for kw in finance_keywords if kw in question]
        })

# Ordenar por volume
finance_markets.sort(key=lambda x: x['volume'], reverse=True)

print(f'Encontrados {len(finance_markets)} mercados financeiros:')
print()
for market in finance_markets[:10]:  # Mostrar top 10
    print(f'Pergunta: {market["question"][:60]}...')
    print(f'  Volume: ${market["volume"]:,.0f}')
    print(f'  Liquidez: ${market["liquidity"]:,.0f}')
    print(f'  Keywords: {market["keywords_found"]}')
    print()