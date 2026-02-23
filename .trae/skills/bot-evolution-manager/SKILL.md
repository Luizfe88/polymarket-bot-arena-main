---
name: "bot-evolution-manager"
description: "Gerencia evolução de bots baseada em trades resolvidos com gatilhos de 100 trades, safety net de 8h e cooldown de 5h. Invoke quando precisar implementar ou ajustar sistema de evolução de bots."
---

# Bot Evolution Manager

Este skill implementa um sistema de evolução de bots com as seguintes regras:

## Regras de Evolução

1. **Gatilho Principal**: Evolução ocorre quando 100 trades forem resolvidos (contagem global de todos os bots)
2. **Safety Net**: Força evolução após 8 horas se não atingir os 100 trades
3. **Cooldown Mínimo**: 5 horas entre evoluções para evitar mudanças frequentes

## Estrutura do Sistema

### 1. Trade Counter Global
- Contador global de trades resolvidos
- Incrementado quando qualquer bot resolve um trade
- Resetado após evolução

### 2. Evolution Trigger
- Verifica periodicamente as condições
- Prioriza gatilho de 100 trades
- Usa safety net de 8h como fallback

### 3. Cooldown Manager
- Registra timestamp da última evolução
- Impede evoluções dentro de 5 horas
- Garante estabilidade do sistema

### 4. Bot Selection
- Analisa performance dos bots ativos
- Seleciona melhores candidatos para evolução
- Mantém diversidade na pool de bots

## Implementação

```javascript
class BotEvolutionManager {
    constructor() {
        this.globalTradeCount = 0;
        this.lastEvolutionTime = Date.now();
        this.evolutionInProgress = false;
        this.cooldownHours = 5;
        this.maxTimeWithoutEvolution = 8 * 60 * 60 * 1000; // 8 horas
        this.targetTrades = 100;
    }

    // Incrementa contador global quando trade é resolvido
    onTradeResolved(botId, tradeResult) {
        this.globalTradeCount++;
        this.evaluateEvolutionTrigger();
    }

    // Avalia se deve iniciar evolução
    evaluateEvolutionTrigger() {
        if (this.evolutionInProgress) return;
        
        const now = Date.now();
        const timeSinceLastEvolution = now - this.lastEvolutionTime;
        const cooldownActive = timeSinceLastEvolution < (this.cooldownHours * 60 * 60 * 1000);
        
        if (cooldownActive) return;
        
        // Gatilho principal: 100 trades
        if (this.globalTradeCount >= this.targetTrades) {
            this.triggerEvolution('trade_threshold');
            return;
        }
        
        // Safety net: 8 horas sem evolução
        if (timeSinceLastEvolution >= this.maxTimeWithoutEvolution) {
            this.triggerEvolution('safety_net');
            return;
        }
    }

    // Inicia processo de evolução
    async triggerEvolution(reason) {
        this.evolutionInProgress = true;
        console.log(`🧬 Iniciando evolução de bots (razão: ${reason})`);
        
        try {
            // Seleciona bots para evolução baseado em performance
            const selectedBots = await this.selectBotsForEvolution();
            
            // Executa evolução
            await this.evolveBots(selectedBots);
            
            // Atualiza estado
            this.lastEvolutionTime = Date.now();
            this.globalTradeCount = 0;
            
            console.log(`✅ Evolução concluída. Próxima evolução em ${this.cooldownHours}h.`);
            
        } catch (error) {
            console.error('❌ Erro na evolução:', error);
        } finally {
            this.evolutionInProgress = false;
        }
    }

    // Seleciona bots com melhor performance para evolução
    async selectBotsForEvolution() {
        // Implementar lógica de seleção baseada em:
        // - Taxa de sucesso
        // - Volume de trades
        // - Consistência
        // - Retorno sobre investimento
    }

    // Executa evolução dos bots selecionados
    async evolveBots(selectedBots) {
        // Implementar algoritmo de evolução:
        // - Crossover de estratégias
        // - Mutação de parâmetros
        // - Introdução de novas variantes
        // - Teste de performance
    }
}
```

## Monitoramento

O sistema deve fornecer métricas de:
- Trades resolvidos desde última evolução
- Tempo desde última evolução
- Razão da última evolução
- Performance dos bots evoluídos
- Taxa de sucesso pós-evolução

## Integração

Para integrar este sistema:

1. **Event System**: Implementar eventos quando trades são resolvidos
2. **Scheduler**: Configurar verificações periódicas do trigger
3. **Database**: Persistir estado entre reinicializações
4. **Logging**: Registrar todas as evoluções para análise

## Configuração

```json
{
  "evolution": {
    "targetTrades": 100,
    "cooldownHours": 5,
    "maxTimeWithoutEvolution": 8,
    "selectionCriteria": {
      "minSuccessRate": 0.55,
      "minTrades": 10,
      "consistencyThreshold": 0.3
    }
  }
}
```