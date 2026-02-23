#!/usr/bin/env python3
"""
Script de inicialização rápida para o Telegram Bot do Polymarket Bot Arena.

Uso:
    python start_telegram_bot.py          # Iniciar o bot
    python start_telegram_bot.py --test   # Testar comandos sem iniciar o bot
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_commands():
    """Test all Telegram commands."""
    print("🧪 Testando comandos do Telegram...")
    from test_telegram_commands import test_commands
    test_commands()

def start_bot():
    """Start the Telegram bot."""
    print("🚀 Iniciando Telegram Bot...")
    from telegram_bot import main
    main()

def main():
    parser = argparse.ArgumentParser(description='Polymarket Bot Arena - Telegram Bot')
    parser.add_argument('--test', action='store_true', help='Testar comandos sem iniciar o bot')
    
    args = parser.parse_args()
    
    if args.test:
        test_commands()
    else:
        start_bot()

if __name__ == "__main__":
    main()