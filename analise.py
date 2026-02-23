import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# Configurações de exibição do Pandas
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)
pd.set_option('display.max_rows', 100)

# Conecta ao banco de dados
db_path = 'bot_arena_paper_test_10.db'  # Verifique se o nome do arquivo é este mesmo
conn = sqlite3.connect(db_path)

try:
    print(f"--- RELATÓRIO DE TRADES (ÚLTIMAS 24H) ---")
    
    # Query SQL melhorada
    query = """
    SELECT 
        id,
        bot_name,
        substr(market_question, 1, 35) || '...' as question,
        side,
        amount,
        shares_bought,
        outcome,
        pnl,
        datetime(created_at, 'localtime') as entry_time,
        datetime(resolved_at, 'localtime') as exit_time
    FROM trades
    WHERE created_at >= datetime('now', '-24 hours')
    ORDER BY created_at DESC
    """
    
    df = pd.read_sql_query(query, conn)
    
    if df.empty:
        print("Nenhuma trade encontrada nas últimas 24 horas.")
    else:
        # 1. Calcular Preço Médio de Entrada
        # (Amount / Shares Bought). Se shares_bought for 0 ou nulo, fica 0.
        df['entry_price'] = df.apply(
            lambda x: x['amount'] / x['shares_bought'] if x['shares_bought'] and x['shares_bought'] > 0 else 0, 
            axis=1
        )
        
        # 2. Formatação de Valores
        df['pnl'] = df['pnl'].fillna(0).map('${:,.4f}'.format)
        df['amount'] = df['amount'].map('${:,.4f}'.format)
        df['entry_price'] = df['entry_price'].map('${:,.4f}'.format)
        
        # 3. Selecionar e Reordenar Colunas Finais
        cols_final = [
            'entry_time', 
            'bot_name', 
            'side', 
            'entry_price', 
            'outcome', 
            'pnl', 
            'exit_time', 
            'question'
        ]
        
        # Mostra o relatório
        print(df[cols_final].to_string(index=False))
        print("-" * 120)
        print(f"Total de Trades: {len(df)}")

except Exception as e:
    print(f"Erro ao ler o banco de dados: {e}")
finally:
    if 'conn' in locals():
        conn.close()
