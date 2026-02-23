# 📱 Integração com Telegram

## 🎯 Objetivo
Gerenciar e monitorar seus bots de trading no Polymarket através de comandos no Telegram.

## 📋 O que você pode fazer

### 📊 Comandos de Análise
- **`/bots`** - Ver P&L de cada bot
- **`/status`** - Ver capital total, investido e disponível
- **`/trades`** - Ver trades abertas no momento
- **`/evolucao`** - Ver evolução do capital (últimos 7 dias)
- **`/ranking`** - Ver ranking dos bots por performance
- **`/performance`** - Ver performance das últimas 24h
- **`/resumo`** - Ver resumo geral do sistema

### ⚙️ Comandos de Controle
- **`/reset`** - Resetar todos os bots (despausar)

### ❓ Ajuda
- **`/help`** - Mostrar menu de ajuda
- **`/start`** - Mostrar mensagem de boas-vindas

## 📱 Exemplos de Respostas

### /status - Status do Capital
```
💰 Status do Capital - PAPER
📅 Atualizado: 17/02/2026 12:59:51

🏦 Capital Total: $10,000.00
💼 Capital Investido: $2,500.00
💵 Capital Disponível: $7,500.00
🤖 Bots Ativos: 5

📊 Disponível por Bot:
• momentum-g1: $1,200.00
• mean_reversion-g2: $800.00
```

### /bots - P&L dos Bots
```
📊 P&L dos Bots - PAPER
📅 Atualizado: 17/02/2026 12:59:51

🟢 momentum-g1
   💰 P&L Total: $125.50 ✅
   📈 24h: $45.20 ✅ (12 trades)
   🎯 Trades: 156

🔴 mean_reversion-g2
   💰 P&L Total: -$23.40 🔴
   📈 24h: -$5.60 🔴 (8 trades)
   🎯 Trades: 89
```

### /trades - Trades Abertas
```
📈 Trades Abertas - PAPER
📅 Atualizado: 17/02/2026 12:59:51

📈 momentum-g1
📝 Mercado: BTC will be above $50,000 in 5 minutes?
💰 Valor: $25.00
🎯 Lado: YES
🤔 Confiança: 65.5%
⏰ Aberta: 2h atrás
```

### /evolucao - Evolução do Capital
```
📊 Evolução do Capital - PAPER
📅 Período: Últimos 7 dias
📅 Atualizado: 17/02/2026 12:59:51

🟢 17/02
   💰 P&L: $125.50 ✅
   🎯 Trades: 45
   📊 Volume: $1,250.00

🔴 16/02
   💰 P&L: -$23.40 🔴
   🎯 Trades: 32
   📊 Volume: $890.00

📈 Resumo do Período:
💰 P&L Total: $456.80 ✅
🎯 Trades: 234
📊 Volume: $5,670.00
📈 Média Diária: $65.26 ✅
```

### /ranking - Ranking dos Bots
```
🏆 Ranking dos Bots - PAPER
📅 Atualizado: 17/02/2026 12:59:51

🥇 momentum-g3
   💰 P&L: $456.80 ✅
   📊 Win Rate: 68.50% 🟢
   🎯 Trades: 89W 41L
   📈 Média: $5.13 ✅

🥈 sentiment-v2
   💰 P&L: $234.50 ✅
   📊 Win Rate: 62.30% 🟢
   🎯 Trades: 156W 94L
   📈 Média: $2.34 ✅

🥉 hybrid-g1
   💰 P&L: $123.20 ✅
   📊 Win Rate: 58.90% 🟢
   🎯 Trades: 134W 93L
   📈 Média: $1.89 ✅
```

### Notificações Automáticas (ainda disponíveis)
- **Pausa de Bot**: 🔴 Quando um bot é pausado por limite ou perdas consecutivas
- **Retomada de Bot**: 🟢 Quando um bot volta a operar
- **Erros**: ❌ Quando ocorrem erros nos bots

**Nota**: As notificações de trade individual foram removidas conforme solicitado.

---

## 🔧 Configuração Passo a Passo

### Passo 1: Criar um Bot no Telegram

1. Abra o Telegram e procure por **@BotFather**
2. Envie `/newbot`
3. Escolha um nome para seu bot (ex: "Polymarket Bot Arena")
4. Escolha um username único (deve terminar com "bot", ex: "polymarket_arena_bot")
5. Copie o **token** fornecido (formato: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Passo 2: Obter seu Chat ID

1. No Telegram, procure por **@userinfobot**
2. Inicie uma conversa e ele mostrará seu **ID** (número)
3. Copie esse número

### Passo 3: Configurar as Variáveis de Ambiente

#### Opção A: Linux/Mac (Terminal)
```bash
export TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
export TELEGRAM_CHAT_ID="123456789"
export TELEGRAM_ENABLED="true"
```

#### Opção B: Windows (PowerShell)
```powershell
$env:TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
$env:TELEGRAM_CHAT_ID="123456789"
$env:TELEGRAM_ENABLED="true"
```

#### Opção C: Arquivo .env (Recomendado)
Crie um arquivo `.env` na raiz do projeto:
```
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
TELEGRAM_ENABLED=true
```

### Passo 4: Testar a Integração

Execute o teste:
```bash
python test_telegram.py
```

---

## 📱 Exemplos de Mensagens

### Pausa por Limite Diário
```
🔴 Bot Pausado - Limite Diário Atingido

🤖 Bot: mean_reversion-g3-621
📅 Data/Hora: 17/02/2026 11:31:41
💰 Perda Atual: $5.20
🚫 Limite Máximo: $15.00
⚠️ Motivo: Limite diário de perdas atingido
```

### Trade Executado
```
💹 Trade Executado

🤖 Bot: sentiment-v1
📅 Data/Hora: 17/02/2026 11:31:41
💰 Valor: $2.50
📈 Lado: YES
📊 Mercado: BTC will be above $50,000 in 5 minutes?
```

### Bot Retomado
```
🟢 Bot Retomado

🤖 Bot: momentum-g4-457
📅 Data/Hora: 17/02/2026 11:31:41
✅ Status: Bot retomado com sucesso
```

---

## ⚙️ Configurações Avançadas

### Desabilitar Notificações
```bash
export TELEGRAM_ENABLED="false"
```

### Testar com Mensagens de Exemplo
```python
from telegram_notifier import get_telegram_notifier

telegram = get_telegram_notifier()
if telegram:
    # Testar notificação de pausa
    telegram.notify_bot_paused("meu-bot", "daily_loss_limit", loss_amount=10.50, max_loss=15.00)
    
    # Testar notificação de trade
    telegram.notify_trade_executed("meu-bot", 5.00, "YES", "BTC 5-min prediction")
    
    # Testar notificação de erro
    telegram.notify_error("meu-bot", "Erro de conexão com API")
```

---

## 🐛 Solução de Problemas

### "Telegram notifier não está disponível"
- Verifique se as variáveis de ambiente estão configuradas corretamente
- Certifique-se de que o bot token e chat ID estão válidos

### Mensagens não chegam
- Certifique-se de que você iniciou uma conversa com seu bot no Telegram
- Verifique se o bot não está bloqueado
- Teste o token manualmente: `https://api.telegram.org/bot<SEU_TOKEN>/getMe`

### Erros de importação
- Verifique se o arquivo `telegram_notifier.py` está na raiz do projeto
- Certifique-se de que o `requests` está instalado: `pip install requests`

---

## 📝 Notas Importantes

- **Segurança**: Nunca compartilhe seu bot token publicamente
- **Rate Limits**: O Telegram limita a 30 mensagens por segundo para bots
- **Timezone**: Todas as mensagens usam horário de Brasília (BRT - UTC-3)
- **Fallback**: Se o Telegram falhar, os logs locais ainda funcionam normalmente