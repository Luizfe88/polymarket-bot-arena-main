# 🤖 Telegram Bot - Polymarket Bot Arena

## 📋 Visão Geral

O sistema de Telegram foi completamente transformado de um simples notificador para um **sistema completo de gerenciamento e monitoramento** dos seus bots de trading. Agora você pode controlar e visualizar todos os aspectos do seu arena diretamente pelo Telegram!

## 🎯 O que foi Implementado

### ✅ Remoção de Notificações de Trade
- **Removidas** notificações individuais de cada trade executado (conforme solicitado)
- **Mantidas** notificações importantes: pausas, retomadas e erros

### ✅ Sistema de Comandos Completo
Implementamos **10 comandos** coloridos e didáticos:

#### 📊 Análise e Monitoramento
- `/bots` - P&L detalhado de cada bot com emojis coloridos ✅🔴
- `/status` - Capital total, investido e disponível 💰
- `/trades` - Todas as posições abertas no momento 📈
- `/evolucao` - Evolução do capital nos últimos 7 dias 📊
- `/ranking` - Ranking dos bots por performance 🏆
- `/performance` - Performance das últimas 24h ⚡
- `/resumo` - Resumo geral do sistema 📋

#### ⚙️ Controle
- `/reset` - Resetar todos os bots (despausar) 🔄

#### ❓ Ajuda
- `/help` - Menu completo de ajuda
- `/start` - Mensagem de boas-vindas

## 🚀 Como Usar

### 1. Configuração Inicial
```bash
# Configure suas credenciais
export TELEGRAM_BOT_TOKEN="seu_token_aqui"
export TELEGRAM_CHAT_ID="seu_id_aqui"
export TELEGRAM_ENABLED="true"
```

### 2. Iniciar o Bot
```bash
# Opção 1: Iniciar diretamente
python telegram_bot.py

# Opção 2: Usar o script de inicialização
python start_telegram_bot.py

# Opção 3: Testar comandos antes de iniciar
python start_telegram_bot.py --test
```

### 3. Comandos no Telegram
Simplesmente envie qualquer comando para o seu bot:

```
/status
```

Resposta:
```
💰 Status do Capital - PAPER
📅 Atualizado: 17/02/2026 12:59:51

🏦 Capital Total: $10,000.00
💼 Capital Investido: $2,500.00
💵 Capital Disponível: $7,500.00
🤖 Bots Ativos: 5
```

## 🎨 Características Visuais

### Emojis e Cores
- ✅ **Verde**: Valores positivos (lucro, ganhos)
- 🔴 **Vermelho**: Valores negativos (prejuízo, perdas)
- 🟡 **Amarelo**: Avisos e neutralidade
- 📊 **Gráficos**: Indicadores de performance
- 🏆 **Troféus**: Top 3 do ranking

### Formatação Inteligente
- Valores monetários: `$1,234.56`
- Percentuais: `65.50%`
- Horários: BRT (Brasília)
- Tempo decorrido: `2h atrás`, `5m atrás`

## 📊 Exemplos de Uso

### Monitoramento Diário
```
# Ver resumo do dia
/resumo

# Checar performance das últimas 24h
/performance

# Ver ranking atual
/ranking
```

### Análise Detalhada
```
# Ver todos os bots e seus P&Ls
/bots

# Ver trades abertas
/trades

# Ver evolução da semana
/evolucao
```

### Gerenciamento
```
# Resetar todos os bots pausados
/reset

# Ver status completo
/status
```

## 🔧 Arquivos Criados/Modificados

### Novos Arquivos
- `telegram_commands.py` - Sistema completo de comandos
- `telegram_bot.py` - Bot principal com loop de escuta
- `start_telegram_bot.py` - Script de inicialização
- `test_telegram_commands.py` - Testes dos comandos

### Arquivos Modificados
- `telegram_notifier.py` - Adicionado suporte a comandos
- `base_bot.py` - Removidas notificações de trade
- `TELEGRAM_SETUP.md` - Documentação atualizada

## 🧪 Testes

Execute os testes antes de iniciar:
```bash
python test_telegram_commands.py
```

Isso testará todos os comandos sem precisar do bot rodando.

## ⚠️ Notas Importantes

1. **Horário**: Todos os horários são BRT (Brasília)
2. **Database**: Os comandos consultam o banco de dados real
3. **Segurança**: Mantenha seu token seguro
4. **Rate Limits**: Telegram permite 30 msgs/segundo
5. **Fallback**: Se o Telegram falhar, o sistema continua funcionando

## 🎯 Próximos Passos

O sistema está completo e pronto para uso! Você pode:

1. **Iniciar o bot** e começar a usar os comandos
2. **Personalizar mensagens** se desejar
3. **Adicionar novos comandos** conforme necessário
4. **Monitorar performance** através dos comandos implementados

---

**🤖 Seu Polymarket Bot Arena agora está totalmente integrado com Telegram!**

Use os comandos para monitorar, analisar e controlar seus bots de forma fácil e visual.