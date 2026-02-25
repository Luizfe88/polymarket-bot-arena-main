# 🤖 Polymarket Bot Arena v3.0 - PROFITABLE EDITION

**Arena de Trading Algorítmico com Edge Informacional Real para Polymarket**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Profitability](https://img.shields.io/badge/Target-15%25--40%25%2Fmonth-brightgreen.svg)](https://github.com/Luizfe88/polymarket-bot-arena-main)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

⚠️ **Aviso de Risco**: Este software é para fins educacionais e de pesquisa. Trading envolve riscos substanciais de perda. Nunca invista mais do que pode perder. O uso em modo live requer compreensão completa dos riscos e configuração adequada.

## 🎯 O que é v3.0

O Polymarket Bot Arena v3.0 é uma plataforma de trading algorítmico **lucrativa** que executa múltiplos bots com **edge informacional real** em mercados de predição de alta qualidade. Diferente da v2.1 perdedora, esta versão foca em:

- **Seleção rigorosa de mercados** (volume > $200k, spread < 2%, 24h-45 dias até resolução)
- **Edge informacional institucional** (LLM avançado + whale tracking + bayesian updates)
- **Execução profissional** (limit orders inteligentes, custos reais modelados)
- **Evolução genética robusta** (450+ trades, walk-forward validation)
- **Gestão de risco institucional** (Kelly dinâmico, regime detection, drawdown < 15%)

**Target**: Metas realistas baseadas em dados (Sharpe > 1.0, retorno anual 20-40%).

## 🏗️ Arquitetura v3.0

```
┌─────────────────────────────────────────────────────────────────┐
│                    MARKET DISCOVERY ENGINE                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│  │Volume Filter│ │Spread Filter│ │Time Filter  │ │Category ML  │ │
│  │> $200k      │ │< 2%         │ │24h-45d      │ │Priority AI  │ │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ │
│         └──────────────┴──────────────┴──────────────┘        │
│                             ↓                                   │
│                    QUALIFIED MARKETS POOL                       │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────────┐
│                     EDGE GENERATION ENGINE                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│  │LLM Sentiment│ │Whale Tracker │ │Bayesian     │ │Mispricing   │ │
│  │Grok/Claude  │ │Top 50 Wallets│ │Probability  │ │Detector     │ │
│  │+ News + Twt │ │Consistency   │ │Updater      │ │Polymarket vs│ │
│  │+ Reddit     │ │Filter        │ │Real-time    │ │Kalshi       │ │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ │
│         └──────────────┴──────────────┴──────────────┘        │
│                             ↓                                   │
│                    ENSEMBLE PROBABILITIES                       │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────────┐
│                    TRADING EXECUTION ENGINE                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│  │Limit Orders │ │TWAP/Iceberg │ │Cost Model   │ │EV Filter     │ │
│  │Intelligent  │ │Large Orders  │ │Spread+Gas+  │ │> +4.5% EV   │ │
│  │Post-only    │ │Stealth       │ │Fees+Slippage│ │After Costs  │ │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ │
│         └──────────────┴──────────────┴──────────────┘        │
│                             ↓                                   │
│                    EXECUTED POSITIONS                           │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────────┐
│                    RISK MANAGEMENT ENGINE                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│  │Kelly Mod    │ │Regime Detect│ │Drawdown     │ │Correlated   │ │
│  │Vol Target   │ │Chop Filter   │ │Limit < 15%  │ │Exposure     │ │
│  │Position Size│ │Trend/MeanRev│ │Auto Reduce  │ │Limits       │ │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ │
│         └──────────────┴──────────────┴──────────────┘        │
│                             ↓                                   │
│                    PORTFOLIO BALANCE                              │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────────┐
│                    EVOLUTION GENETIC ENGINE                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│  │450+ Trades  │ │Walk-Forward  │ │Sharpe > 0.75│ │Diversity    │ │
│  │Min Sample   │ │Validation    │ │Kill Switch   │ │Penalty      │ │
│  │Robust Stats │ │Out-of-Sample │ │Auto Stop     │ │Strong       │ │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ │
│         └──────────────┴──────────────┴──────────────┘        │
│                             ↓                                   │
│                    IMPROVED STRATEGIES                          │
└─────────────────────────────────────────────────────────────────┘
```

## 🧠 Componentes Principais v3.0

### Core Engines
- **`market_discovery.py`**: Seleciona apenas mercados de alta qualidade com filtros rigorosos
- **`advanced_edge_models.py`**: LLM sentiment + whale tracking + bayesian updates
- **`bayesian_updater.py`**: Atualização probabilística em tempo real
- **`professional_backtester.py`**: Backtest com 12+ meses de dados e validação robusta
- **`execution_engine.py`**: Limit orders inteligentes com modelo de custos realistas

### Enhanced Modules
- **`arena.py`**: Coordenação com seleção de mercados por qualidade
- **`core/risk_manager.py`**: Kelly modificado + regime detection + drawdown < 15%
- **`core/bot_evolution_manager.py`**: Evolução com 450+ trades e walk-forward validation
- **`polymarket_client.py`**: Execução profissional com limit orders e post-only

### New Signal Systems
- **`signals/llm_sentiment_engine.py`**: Grok/Claude/Gemini + Twitter + Reddit + on-chain
- **`signals/whale_tracker_pro.py`**: Top 50 wallets mais lucrativas com filtros de consistência
- **`signals/mispricing_detector.py`**: Arbitragem Polymarket vs Kalshi quando possível
- **`signals/bayesian_probability.py`**: Updates probabilísticos com novas informações

## 📊 Estratégias de Trading v3.0 (8 Bots Premium)

| Bot | Edge Principal | Mercados Alvo | Expected Value |
|-----|---------------|---------------|---------------|
| **LLMSentimentBot** | Análise sentiment AI + news + social | Política, Tech, Macro | +8-15% EV |
| **WhaleCopyBot** | Cópia de wallets top 50 lucrativas | Todos os qualificados | +6-12% EV |
| **BayesianBot** | Updates probabilísticos em tempo real | Eventos com nova info | +5-10% EV |
| **MispricingBot** | Arbitragem vs outros exchanges | Quando disponível | +15-25% EV |
| **NewsFlowBot** | Event-driven trading | Corporate, Tech, Macro | +7-14% EV |
| **HybridEdgeBot** | Ensemble dinâmico dos edges acima | Melhor oportunidades | +10-18% EV |
| **KellyBot** | Position sizing ótimo com Kelly mod | Portfolio management | +4-8% EV |
| **RegimeBot** | Adaptação a regimes de mercado | Trend vs mean-reversion | +5-12% EV |

## 🚀 Como Rodar v3.0

### 1. Instalação
```bash
# Clone o repositório
git clone https://github.com/Luizfe88/polymarket-bot-arena-main.git
cd polymarket-bot-arena-main

# Crie ambiente virtual (obrigatório)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instale as dependências
pip install -r requirements.txt

# Configure API keys (obrigatório para edge real)
cp .env.example .env
# Edite: GROK_API_KEY, CLAUDE_API_KEY, TWITTER_API_KEY, etc.
```

### 2. Configuração v3.0
```bash
# Copie e configure o arquivo v3.0
cp config.v3.example.py config.py

# Configure as variáveis essenciais:
# - MIN_MARKET_VOLUME = 200000
# - MAX_MARKET_SPREAD = 0.025
# - MIN_EV_THRESHOLD = 0.045
# - MAX_DRAWDOWN = 0.15
# - MIN_TRADES_EVOLUTION = 450
# - BOT_ARENA_PAPER_STARTING_BALANCE = 2000.0
# - RISK_PROFILE = Moderate
# - BOT_ARENA_TRADE_MIN_TTE_SECONDS = 21600
# - BOT_ARENA_TRADE_MAX_TTE_SECONDS = 3888000
```

### 3. Primeira Execução (obrigatório ordem)
```bash
# 1. Descubra mercados qualificados (auto a cada 60min)
python market_discovery.py --watch --interval 3600

# 2. Teste o edge (paper trading)
python arena.py --mode paper

# 3. Rode o backtest profissional
python professional_backtester.py --period 12months --validation walk-forward

# 4. Inicie o dashboard
python dashboard/server.py

# 5. Monitore via Telegram
python start_telegram_bot.py
```
 
### 5. Critérios de Mercado v3.0
- Volume mínimo: $150.000
- Tempo até resolução: 6h–45 dias (ideal 24h–30 dias)
- Spread estimado: < 2.5%
- Prioridade: Política EUA 2028, Crypto catalysts, Macro, Sports com dados, Tech eventos
- Rejeição completa: mercados 5-min BTC/ETH/SOL “Up or Down”

### 4. Windows (PowerShell)
```powershell
# Execute o script v3.0 completo
.\start-arena-v3.ps1
```

## 📈 Dashboard v3.0

Acesse http://localhost:8000 para:

- **📊 Performance Real**: P&L líquido após todas as fees
- **📈 Métricas Avançadas**: Sharpe, Calmar, Profit Factor, EV estimado
- **🤖 Status dos Bots**: Edge % atual, confiança, últimos sinais
- **📋 Mercados Ativos**: Volume, spread, tempo até resolução
- **⚙️ Regime Detection**: Chop vs trending, volatilidade implícita
- **🎯 Alvos de Lucro**: Sharpe > 1.0, Retorno anual 20-40%, drawdown < 15%

## 🧪 Testes e Validação v3.0

```bash
# Validação completa antes de live
python analysis/validate_edge_quality.py
python analysis/walk_forward_test.py
python analysis/out_of_sample_test.py
python analysis/cost_analysis_real.py
python analysis/regime_detection_test.py

# Verificação de qualidade
python analysis/edge_quality_score.py --min-score 0.75
python analysis/sharpe_validation.py --min-sharpe 0.75
```

## ⚙️ Configurações v3.0 Importantes

### Market Discovery
```python
MIN_MARKET_VOLUME = 200000      # $200k mínimo
MAX_MARKET_SPREAD = 0.02        # 2% máximo
MIN_TIME_TO_RESOLUTION = 24     # horas
MAX_TIME_TO_RESOLUTION = 45     # dias
PRIORITY_CATEGORIES = [         # Categorias com edge comprovado
    'politics-us-2028',
    'congress-usa',
    'crypto-catalysts',
    'sports-statistical',
    'macro-fed',
    'tech-corporate'
]
```

### Edge Generation
```python
LLM_SENTIMENT_WEIGHT = 0.35     # 35% do edge total
WHALE_TRACKING_WEIGHT = 0.25    # 25% do edge total
BAYESIAN_UPDATE_WEIGHT = 0.25   # 25% do edge total
MISPRICING_WEIGHT = 0.15        # 15% do edge total
MIN_EDGE_THRESHOLD = 0.045      # 4.5% EV mínimo
```

### Risk Management
```python
MAX_DRAWDOWN = 0.15             # 15% máximo
KELLY_FRACTION = 0.25           # Kelly conservador
VOLATILITY_TARGET = 0.02        # 2% vol diária alvo
CORRELATION_LIMIT = 0.7         # Limite de correlação
REGIME_SWITCH_PROTECTION = True # Proteção em chop
```

### Evolution Parameters
```python
MIN_TRADES_EVOLUTION = 450      # 450+ trades mínimo
WALK_FORWARD_PERIOD = 0.3       # 30% out-of-sample
FITNESS_FUNCTION = {            # Composição da fitness
    'sharpe': 0.40,             # 40% Sharpe ratio
    'calmar': 0.30,             # 30% Calmar ratio
    'profit_factor': 0.20,     # 20% Profit factor
    'win_rate': 0.10            # 10% Win rate ajustada
}
DIVERSITY_PENALTY = 0.15        # Penalidade forte por similaridade
KILL_SWITCH_SHARPE = 0.75      # Desliga se Sharpe < 0.75
```

## 🔧 Variáveis de Ambiente v3.0

Veja `.env.v3.example` para todas as configurações. Principais:

```bash
# APIs para Edge Real (obrigatórias)
GROK_API_KEY=your_grok_key_here
CLAUDE_API_KEY=your_claude_key_here
TWITTER_API_KEY=your_twitter_key_here
REDDIT_API_KEY=your_reddit_key_here

# Configurações de Qualidade
MIN_MARKET_VOLUME=200000
MAX_MARKET_SPREAD=0.02
MIN_EDGE_THRESHOLD=0.045
MAX_DRAWDOWN=0.15

# Modo de Operação
MODE=paper                    # paper ou live
ENABLE_LLM_SENTIMENT=true   # Ativa edge AI
ENABLE_WHALE_TRACKING=true  # Ativa copy trading
ENABLE_BAYESIAN=true        # Ativa updates probabilísticos
```

## 📊 Métricas de Performance v3.0

### Targets (após todas as fees)
- **Retorno Anual**: 20-40% (estimado)
- **Sharpe Ratio**: > 1.0
- **Max Drawdown**: < 15%
- **Win Rate**: > 52% (com EV positivo)
- **Profit Factor**: > 1.3

### KPIs de Edge
- **EV Médio por Trade**: > +4.5%
- **Edge Informational Score**: > 0.75
- **Whale Copy Success Rate**: > 65%
- **LLM Sentiment Accuracy**: > 68%
- **Bayesian Update Quality**: > 0.8 correlation

## 🛣️ Roadmap v3.x

### v3.1 (Next - 2 semanas)
- [ ] Integração com mais exchanges (Kalshi, PredictIt)
- [ ] Machine Learning avançado (XGBoost, LSTM)
- [ ] Mobile dashboard completo
- [ ] Alertas em tempo real via Telegram/Discord

### v3.2 (1 mês)
- [ ] Multi-mercado global (Europa, Ásia)
- [ ] Deep learning para sentiment analysis
- [ ] Sistema de alertas avançado com thresholds
- [ ] API REST completa para integrações

### v3.3 (2 meses)
- [ ] Derivativos e opções em prediction markets
- [ ] High-frequency trading em eventos
- [ ] Portfolio optimization multi-mercado
- [ ] White-label para institucionais

## 🤝 Contribuindo para v3.0

1. Fork o projeto
2. Crie sua feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

**Foco em contribuições que aumentem o edge real e lucratividade!**

## 📄 Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.

## 📞 Suporte v3.0

- **Documentação**: [Wiki v3.0](https://github.com/Luizfe88/polymarket-bot-arena-main/wiki)
- **Issues**: [GitHub Issues](https://github.com/Luizfe88/polymarket-bot-arena-main/issues)
- **Telegram**: [@PolymarketBotArena](https://t.me/PolymarketBotArena)
- **Email**: luizfe88@tradingbots.com

---

**⚡ Transformando prediction markets em máquinas de lucro com edge real!**
