#!/usr/bin/env python3
"""
Telegram Bot for Polymarket Bot Arena

This script runs a Telegram bot that responds to commands for managing
and monitoring polymarket trading bots.

Commands available:
- /bots: Show P&L for each bot
- /reset: Reset all bots
- /evolucao: Show capital evolution
- /trades: Show open trades
- /status: Show capital status
- /ranking: Show bot ranking
- /performance: Show recent performance
- /resumo: Show general summary
- /help: Show help menu
- /start: Show welcome message
"""

import time
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from telegram_notifier import get_telegram_notifier
from telegram_commands import commands_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function to run the Telegram bot."""
    logger.info("Starting Polymarket Bot Arena Telegram Bot...")
    
    # Get Telegram notifier instance
    telegram = get_telegram_notifier()
    
    if not telegram:
        logger.error("Telegram notifier not configured. Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in config.py")
        return
    
    if not telegram.enabled:
        logger.warning("Telegram notifications are disabled")
        return
    
    # Set up command handler
    telegram.set_command_handler(commands_handler.process_command)
    
    # Send startup message
    startup_message = f"""
🤖 <b>Polymarket Bot Arena - Telegram Bot Iniciado</b>

✅ Bot conectado e pronto para receber comandos!
📅 <b>Iniciado:</b> {commands_handler.get_current_time_brt()}

<b>Comandos disponíveis:</b>
• /help - Mostrar menu de ajuda
• /bots - P&L dos bots
• /status - Status do capital
• /trades - Trades abertas
• /evolucao - Evolução do capital

<i>Use /help para ver todos os comandos disponíveis.</i>
"""
    
    telegram.send_message(startup_message)
    
    # Main bot loop
    logger.info("Bot started successfully. Listening for commands...")
    offset = 0
    
    try:
        while True:
            try:
                # Get updates from Telegram
                updates = telegram.get_updates(offset=offset, timeout=30)
                
                if updates:
                    logger.info(f"Processing {len(updates)} updates")
                    
                    for update in updates:
                        # Update offset to avoid processing the same update again
                        offset = max(offset, update["update_id"] + 1)
                        
                        # Check if update contains a message
                        if "message" in update:
                            message = update["message"]
                            
                            # Process the message
                            if telegram.process_message(message):
                                logger.info(f"Processed message from user {message.get('from', {}).get('id', 'unknown')}")
                            else:
                                logger.warning(f"Failed to process message: {message}")
                
                # Small delay to avoid overwhelming the API
                time.sleep(1)
                
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in bot loop: {e}")
                time.sleep(5)  # Wait before retrying
                
    except Exception as e:
        logger.error(f"Fatal error in bot: {e}")
    finally:
        # Send shutdown message
        shutdown_message = f"""
🤖 <b>Polymarket Bot Arena - Telegram Bot Desconectado</b>

❌ Bot desconectado.
📅 <b>Desconectado:</b> {commands_handler.get_current_time_brt()}

<i>O bot será reiniciado automaticamente.</i>
"""
        telegram.send_message(shutdown_message)
        logger.info("Bot shutdown complete")


if __name__ == "__main__":
    main()