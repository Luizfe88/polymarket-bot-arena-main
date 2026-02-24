# Polymarket Bot Arena - Regras do Projeto

## Configurações de Mercado

### Filtros de Qualidade
- **MIN_MARKET_VOLUME**: $100,000 (mercados com volume mínimo para garantir atividade)
- **MIN_LIQUIDITY**: $3,000 (liquidez mínima para garantir facilidade de entrada/saída)
- **MAX_MARKET_SPREAD**: 0.15 (15% de spread máximo para permitir mais mercados qualificados)
- **MIN_DAYS_TO_RESOLUTION**: 7 dias (mercados que se resolvem em pelo menos 7 dias)

### Categorias Prioritárias
```python
PRIORITY_CATEGORIES = ["finance", "macro", "politics"]
```

### Mapeamento de Categorias
O sistema inferi categorias baseado nas perguntas dos mercados quando o campo `raw_category` está ausente ou é "unknown":

#### Financeiro/Macro (Prioridade Máxima)
Palavras-chave: fed, federal reserve, interest rate, inflation, gdp, unemployment, recession, stock market, dow jones, nasdaq, sp500, s&p 500, oil, gold, silver, dollar, euro, yuan, trade war, tariff, bond, yield, treasury, fomc, rate, economic, economy, market crash, bull market, bear market, deflation, quantitative easing, qe, mortgage, housing, real estate, commodity, forex, currency, exchange rate, central bank, monetary, fiscal, budget, debt, stock, shares, equity, dividend, earnings, revenue, profit, loss

#### Política
Palavras-chave: trump, biden, election, president, senate, house, republican, democrat, vote, candidate, primary, impeach, resign, minister, prime minister, parliament, congress, war, invasion, china, russia, ukraine, taiwan, ceasefire, peace, nato, un, security council

#### Crypto
Palavras-chave: bitcoin, btc, ethereum, eth, crypto, cryptocurrency, blockchain, defi, nft

## Fonte de Mercados (arena.py)

O `arena.py` utiliza uma estratégia dual:
1. **Arquivo local**: `qualified_markets.json` (gerado por `market_discovery.py`)
2. **API Simmer**: Mercados de crypto de 5 minutos como fallback

## Comandos de Validação

### Executar Descoberta de Mercados
```bash
python market_discovery.py
```

### Analisar Mercados Financeiros
```bash
python analyze_finance_markets.py
```

### Executar Arena
```bash
python arena.py
```

## Padrões de Código

### Acesso Seguro a Propriedades
Sempre usar `market.get('propriedade', valor_padrao)` ao invés de `market['propriedade']`

### Formatação de Datas
Usar `strftime('%Y-%m-%dT%H:%M:%SZ')` ao invés de `isoformat()` para garantir formato consistente

### Logging
Sempre logar mercados qualificados com métricas principais:
- Volume
- Liquidez  
- Spread
- Categoria mapeada

## Estrutura de Arquivos

- `market_discovery.py`: Motor de descoberta e filtragem de mercados
- `arena.py`: Sistema de competição entre bots
- `config.py`: Configurações centralizadas
- `qualified_markets.json`: Arquivo de mercados qualificados (gerado automaticamente)
- `analyze_finance_markets.py`: Script de análise de mercados financeiros

## Variáveis de Ambiente

As seguintes variáveis podem ser configuradas no arquivo `.env`:
- `MIN_MARKET_VOLUME`
- `MAX_MARKET_SPREAD`
- `MIN_LIQUIDITY`

**Nota**: Valores no arquivo `.env` sobrescrevem valores padrão em `config.py`