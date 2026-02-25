# Thresholds Temporários - Ajuste para Gerar Primeiros Trades

## Objetivo
Reduzir temporariamente os thresholds de edge/confiança para permitir que o bot gere os primeiros 100-200 trades necessários para análise e evolução.

## Valores Originais (Restaurar após 100-200 trades)
- `MIN_EXPECTED_VALUE`: 0.075 (7.5%)
- `MIN_EDGE_THRESHOLD`: 0.075 (7.5%)
- `MIN_CONFIDENCE_THRESHOLD`: 0.20 (20%)

## Valores Temporários (Atuais)
- `MIN_EXPECTED_VALUE`: -0.005 (-0.5%)
- `MIN_EDGE_THRESHOLD`: -0.005 (-0.5%)
- `MIN_CONFIDENCE_THRESHOLD`: 0.10 (10%)

## Quando Restaurar
Restaurar os valores originais quando:
- [ ] 100-200 trades forem gerados e resolvidos
- [ ] Análise inicial de performance for concluída
- [ ] Sistema de evolução de bots estiver ativo

## Arquivos Modificados
- `config.py`: Linhas 141, 158-160

## Notas
- Estes valores temporários aceitam trades com margem negativa para acelerar a geração de dados
- Monitorar de perto os resultados iniciais
- Ajustar para valores mais conservadores assim que possível