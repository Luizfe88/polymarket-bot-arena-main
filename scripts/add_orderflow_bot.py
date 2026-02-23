#!/usr/bin/env python3
"""
Script para adicionar o OrderflowBot manualmente ao sistema.
Usage: python add_orderflow_bot.py
"""

import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao path para importações
sys.path.insert(0, str(Path(__file__).parent))

try:
    import db
    from bots.bot_orderflow import OrderflowBot
    from logging_config import setup_logging_with_brt
    
    # Configura logging
    logger = setup_logging_with_brt("add_orderflow_bot")
    
    def main():
        """Adiciona OrderflowBot ao sistema."""
        logger.info("Iniciando adição de OrderflowBot...")
        
        try:
            # Criar o bot
            bot = OrderflowBot(name="orderflow-v1", generation=0)
            
            # Adicionar ao banco de dados
            db.save_bot_config(bot.name, bot.strategy_type, bot.generation, bot.strategy_params)
            
            logger.info(f"✅ OrderflowBot adicionado com sucesso!")
            logger.info(f"Nome: {bot.name}")
            logger.info(f"Tipo: {bot.strategy_type}")
            logger.info(f"Geração: {bot.generation}")
            logger.info(f"Parâmetros: {bot.strategy_params}")
            
            # Verificar se foi adicionado
            active_bots = db.get_active_bots()
            orderflow_bots = [b for b in active_bots if 'orderflow' in b['bot_name'].lower()]
            logger.info(f"Total de bots orderflow ativos agora: {len(orderflow_bots)}")
            
            print(f"✅ OrderflowBot adicionado com sucesso!")
            print(f"Nome: {bot.name}")
            print(f"Tipo: {bot.strategy_type}")
            print(f"Geração: {bot.generation}")
            print(f"Parâmetros: {bot.strategy_params}")
            print(f"Total de bots orderflow ativos agora: {len(orderflow_bots)}")
            
            return 0
            
        except Exception as e:
            logger.error(f"Erro ao adicionar OrderflowBot: {e}")
            print(f"❌ Erro ao adicionar OrderflowBot: {e}")
            return 1
    
    if __name__ == "__main__":
        sys.exit(main())
        
except ImportError as e:
    print(f"❌ Erro de importação: {e}")
    print("Certifique-se de que todos os módulos necessários estão disponíveis.")
    sys.exit(1)