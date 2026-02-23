import requests

try:
    response = requests.get('http://127.0.0.1:8510/api/bots')
    data = response.json()
    
    print(f"Total de bots no dashboard: {len(data)}")
    print("\nBots ativos:")
    
    for bot in data:
        config = bot['config']
        bot_name = config['bot_name']
        strategy_type = config['strategy_type']
        active = config['active']
        
        print(f"- {bot_name} | Tipo: {strategy_type} | Ativo: {active}")
        
    # Verificar especificamente orderflow
    orderflow_bots = [b for b in data if 'orderflow' in b['config']['bot_name']]
    print(f"\n✅ Orderflow bots encontrados: {len(orderflow_bots)}")
    
except Exception as e:
    print(f"❌ Erro ao acessar dashboard: {e}")
    print("Verifique se o servidor está rodando em http://127.0.0.1:8510")