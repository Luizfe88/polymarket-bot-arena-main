# 🤖 Polymarket Bot Arena v2.1

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-2.1-blue.svg)](https://github.com/your-username/polymarket-bot-arena)
[![Status](https://img.shields.io/badge/status-active-brightgreen.svg)](https://github.com/your-username/polymarket-bot-arena)

> **Arena de Trading Algorítmico com Evolução Genética para Polymarket**

## ⚠️ Aviso de Risco
**Este software é para fins educacionais e de pesquisa. Trading envolve riscos substanciais de perda. Nunca invista mais do que pode perder. O uso em modo live (dinheiro real) requer compreensão completa dos riscos e configuração adequada.**

## 🎯 O que é

O Polymarket Bot Arena é uma plataforma de trading algorítmico que executa múltiplos bots de trading competindo entre si em mercados de predição. O sistema utiliza evolução genética para melhorar continuamente o desempenho dos bots através de:

- **Seleção Natural**: Apenas os melhores bots sobrevivem
- **Crossover Genético**: Criação de novos bots a partir dos vencedores
- **Mutação**: Introdução de variações para explorar novas estratégias
- **Gestão de Risco Centralizada**: Sistema único de controle de risco baseado no tamanho da banca

## 🏗️ Arquitetura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Dashboard     │    │   Arena.py      │    │   Bots          │
│   (FastAPI)     │◄──►│   (Principal)   │◄──►│   (8 Estratégias)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Banco de Dados│    │   Risk Manager  │    │   Evolution     │
│   (SQLite)      │    │   (Centralizado)│    │   (Genética)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Componentes Principais

- **[arena.py](arena.py)**: Loop principal de trading e coordenação
- **[core/risk_manager.py](core/risk_manager.py)**: Gestão centralizada de risco
- **[core/bot_evolution_manager.py](core/bot_evolution_manager.py)**: Motor de evolução genética
- **[bots/](bots/)**: Implementações das 8 estratégias de trading
- **[signals/](signals/)**: Sistemas de análise de mercado
- **[dashboard/](dashboard/)**: Interface web para monitoramento
- **[analysis/](analysis/)**: Ferramentas de análise e diagnóstico

## 🚀 Como Rodar

### 1. Instalação

```bash
# Clone o repositório
git clone https://github.com/your-username/polymarket-bot-arena.git
cd polymarket-bot-arena

# Crie ambiente virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instale as dependências
pip install -r requirements.txt
```

### 2. Configuração

```bash
# Copie o arquivo de exemplo
cp .env.example .env

# Edite as variáveis necessárias no .env
nano .env
```

### 3. Primeira Execução

```bash
# Modo Paper Trading (recomendado para testes)
python arena.py --mode paper

# Com interface de dashboard
python dashboard/server.py
```

### 4. Windows (PowerShell)

```powershell
# Execute o script pronto
.\start-arena.ps1
```

## 📊 Estratégias de Trading (8 Bots)

| Bot | Estratégia | Descrição |
|-----|------------|-----------|
| **MomentumBot** | 🚀 Momentum | Segue tendências de preço |
| **MeanRevBot** | 📈 Mean Reversion | Compra baixo, vende alto |
| **MeanRevSLBot** | 🛡️ Mean Reversion com Stop Loss | Versão com proteção |
| **MeanRevTPBot** | 🎯 Mean Reversion com Take Profit | Versão com alvos |
| **SentimentBot** | 😊 Sentimento | Análise de sentimento do mercado |
| **HybridBot** | 🔀 Híbrido | Combina múltiplas estratégias |
| **OrderflowBot** | 📊 Order Flow | Análise de fluxo de ordens |

## ⚙️ Configurações Importantes

### Evolução Genética
- **Ciclo de Evolução**: 4 horas (padrão)
- **Trades Mínimos**: 80 trades para evolução
- **Cooldown**: 5 horas entre evoluções
- **Sobreviventes**: Top performers continuam

### Gestão de Risco
- **Limites Dinâmicos**: Baseados no tamanho da banca
- **Drawdown Protection**: Reduz exposição em quedas
- **Stop Diário**: Limites de perda por bot e global
- **Controle de Posição**: Máximo por bot e total

### Modos de Operação
- **Paper Trading**: Simulação sem risco real
- **Live Trading**: Dinheiro real (requer configuração)

## 📈 Dashboard

Acesse `http://localhost:8000` para:
- 📊 Visualizar performance em tempo real
- 📈 Gráficos de P&L e estatísticas
- 🤖 Status de cada bot
- 📋 Histórico de trades
- ⚙️ Configurações da arena

## 🧪 Testes e Análise

```bash
# Executar análises
python analysis/performance_analyzer.py
python analysis/risk_analyzer.py
python analysis/evolution_analyzer.py

# Verificar integridade
python analysis/system_checker.py
```

## 🔧 Variáveis de Ambiente

Veja [.env.example](.env.example) para todas as configurações disponíveis.

## 📝 Roadmap

### Versão 2.2 (Próxima)
- [ ] Integração com mais exchanges
- [ ] Estratégias baseadas em machine learning
- [ ] Backtesting avançado
- [ ] Mobile dashboard

### Versão 3.0 (Futuro)
- [ ] Trading multi-mercado
- [ ] Algoritmos de deep learning
- [ ] Sistema de alertas avançado
- [ ] API REST completa

## 🤝 Contribuindo

1. Fork o projeto
2. Crie sua feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## ⚖️ Disclaimer

Este software é fornecido "como está", sem garantia de qualquer tipo, expressa ou implícita. O uso deste software é por sua conta e risco. Os autores não são responsáveis por quaisquer perdas financeiras resultantes do uso deste software.

## 📞 Suporte

- 📧 Email: seu-email@example.com
- 💬 Discord: [Link do servidor]
- 🐛 Issues: Use o GitHub Issues

---

**⭐ Se este projeto foi útil, considere dar uma estrela no GitHub!**