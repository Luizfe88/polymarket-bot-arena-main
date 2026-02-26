import subprocess
import time
import logging
import sys
import os
from datetime import datetime

# Tenta importar o notificador, mas não falha se der erro
try:
    from telegram_notifier import get_telegram_notifier
    telegram_available = True
except ImportError:
    telegram_available = False

# Configuração de logging para o watchdog
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [WATCHDOG] - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("watchdog.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

MAX_RETRIES = 10
RETRY_WINDOW = 3600  # 1 hora
restart_timestamps = []

def notify_telegram(message):
    if telegram_available:
        try:
            notifier = get_telegram_notifier()
            if notifier:
                notifier.send_message(f"🐕 [WATCHDOG] {message}")
        except Exception as e:
            logging.error(f"Falha ao enviar notificação Telegram: {e}")

def should_restart():
    """Verifica se não excedemos o limite de reinícios na última hora."""
    now = time.time()
    # Limpa timestamps antigos (mantém apenas os da janela atual)
    global restart_timestamps
    restart_timestamps = [t for t in restart_timestamps if now - t < RETRY_WINDOW]
    
    if len(restart_timestamps) >= MAX_RETRIES:
        return False
    return True

def start_arena():
    """Inicia o processo da Arena."""
    # Usa o mesmo interpretador Python que está rodando o watchdog
    cmd = [sys.executable, "arena.py"]
    
    # Passar argumentos adiante se houver (ex: --mode live)
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])
        
    logging.info(f"Iniciando Arena: {' '.join(cmd)}")
    
    # Define variáveis de ambiente para garantir output sem buffer
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    
    return subprocess.Popen(cmd, env=env)

def main():
    logging.info("Watchdog iniciado. Monitorando arena.py...")
    notify_telegram("Iniciado e monitorando arena.py")
    
    while True:
        process = start_arena()
        
        try:
            # Espera o processo terminar
            return_code = process.wait()
            
            # Se chegou aqui, o processo terminou
            if return_code == 0:
                logging.info("Arena encerrou normalmente (código 0). Watchdog encerrando.")
                notify_telegram("Arena encerrou normalmente. Watchdog parando.")
                break
            else:
                logging.error(f"⚠️ Arena caiu com código de erro: {return_code}")
                
                if should_restart():
                    restart_timestamps.append(time.time())
                    delay = 10  # Espera 10s antes de reiniciar
                    
                    msg = f"Arena CRASH (código {return_code}). Reiniciando em {delay}s... (Tentativa {len(restart_timestamps)}/{MAX_RETRIES} na última hora)"
                    logging.info(msg)
                    notify_telegram(msg)
                    
                    time.sleep(delay)
                else:
                    msg = f"⛔ Muitos erros consecutivos ({len(restart_timestamps)} em 1h). Desistindo para evitar loop."
                    logging.critical(msg)
                    notify_telegram(msg)
                    break
                    
        except KeyboardInterrupt:
            logging.info("Watchdog interrompido pelo usuário. Encerrando Arena...")
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logging.warning("Arena não respondeu ao terminate. Forçando kill...")
                process.kill()
            
            logging.info("Arena encerrada. Watchdog finalizado.")
            break
        except Exception as e:
            logging.error(f"Erro inesperado no Watchdog: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
