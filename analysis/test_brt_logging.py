#!/usr/bin/env python3
"""Testar o novo sistema de logging com timezone BRT"""

import sys
sys.path.append('.')

from logging_config import setup_logging_with_brt
import logging

# Testar o novo logger
logger = setup_logging_with_brt("test_brt")

print("=== Teste de Logging com BRT ===")
print("Horário atual UTC:", logging.Formatter().formatTime(logging.LogRecord(
    name="test", level=logging.INFO, pathname="", lineno=0, 
    msg="", args=(), exc_info=None
)))

# Testar mensagem de log
logger.info("Testando logging com timezone BRT")
logger.warning("Daily loss limit hit ($5.20 >= $15.00), pausing. Loss: $5.20")

print("\n✅ Teste concluído!")
print("Agora os logs aparecerão em horário de Brasília (BRT - UTC-3)")
print("Exemplo: 2026-02-17 08:31:41 [bots.base_bot] INFO: [sentiment-v1] Paused (daily_loss_limit), skipping trade")