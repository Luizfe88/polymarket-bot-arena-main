import sqlite3
import datetime
import os
from dateutil import parser

# Caminho do seu banco de dados
DB_PATH = r"C:\Users\luizf\Documents\polymarket\polymarket-bot-arena-main\bot_arena_paper_test_10.db"
# O intervalo que você definiu no PowerShell (em horas)
INTERVALO_HORAS = 4 

def verificar_tempo():
    if not os.path.exists(DB_PATH):
        print("Erro: Banco de dados não encontrado.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Busca a data da última evolução salva no estado da arena
    cursor.execute("SELECT value FROM arena_state WHERE key='last_evolution_at'")
    row = cursor.fetchone()
    conn.close()

    if not row:
        print("Nenhum registro de evolução anterior encontrado. A primeira acontecerá em breve.")
        return

    # Processa as datas
    last_evo_str = row['value']
    last_evo = parser.parse(last_evo_str)
    
    # O banco salva em UTC ou local? Geralmente os logs mostram UTC, vamos assumir local para o cálculo simples
    # Se der erro de fuso, usamos datetime.now() simples
    try:
        agora = datetime.datetime.now(datetime.timezone.utc)
        if last_evo.tzinfo is None:
            last_evo = last_evo.replace(tzinfo=datetime.timezone.utc)
    except:
        agora = datetime.datetime.now()

    proxima_evo = last_evo + datetime.timedelta(hours=INTERVALO_HORAS)
    tempo_restante = proxima_evo - agora

    print("-" * 40)
    print(f"Última Evolução:  {last_evo.strftime('%H:%M:%S')}")
    print(f"Próxima Evolução: {proxima_evo.strftime('%H:%M:%S')} (Meta de {INTERVALO_HORAS}h)")
    print("-" * 40)

    if tempo_restante.total_seconds() > 0:
        horas, resto = divmod(int(tempo_restante.total_seconds()), 3600)
        minutos, segundos = divmod(resto, 60)
        print(f"⏳ FALTA: {horas}h {minutos}m {segundos}s")
    else:
        print(f"🚀 A EVOLUÇÃO ESTÁ ATRASADA POR {abs(int(tempo_restante.total_seconds() / 60))} MINUTOS.")
        print("   Ela ocorrerá assim que você ligar o 'arena.py'.")

if __name__ == "__main__":
    verificar_tempo()
