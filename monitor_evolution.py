#!/usr/bin/env python3
"""
Monitor de Sistema de Evolução de Bots

Mostra status em tempo real do sistema de evolução baseado em trades.
"""

import sys
import time
import json
import argparse
from datetime import datetime, timedelta

# Adiciona o diretório atual ao path para importar módulos locais
sys.path.insert(0, '.')

from evolution_integration import get_evolution_status
from bot_evolution_manager import BotEvolutionManager
import db


def format_timedelta(td):
    """Formata timedelta em string legível"""
    if isinstance(td, str):
        return td
    
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"


def get_progress_bar(percent, width=20):
    """Cria barra de progresso visual"""
    filled = int(width * percent / 100)
    empty = width - filled
    return f"[{'█' * filled}{'░' * empty}] {percent:.1f}%"


def display_status():
    """Mostra status completo do sistema"""
    try:
        status = get_evolution_status()
        
        print("\n" + "="*60)
        print("🧬 SISTEMA DE EVOLUÇÃO DE BOTS")
        print("="*60)
        
        # Métricas principais
        print(f"📊 Trades Resolvidos: {status['global_trade_count']}/{status['target_trades']}")
        print(f"   {get_progress_bar(status['progress_percent'])}")
        
        # Tempo desde última evolução
        last_evolution = datetime.fromisoformat(status['last_evolution_time'])
        time_since = format_timedelta(status['time_since_last_evolution'])
        print(f"⏰ Última Evolução: {time_since} atrás")
        
        # Cooldown
        if status['cooldown_active']:
            next_evolution = datetime.fromisoformat(status['next_evolution_time'])
            remaining = next_evolution - datetime.now()
            print(f"🔒 Cooldown Ativo: Próxima em {format_timedelta(remaining)}")
        else:
            print(f"✅ Cooldown Livre")
        
        # Gatilhos de evolução
        print(f"\n🎯 Gatilhos de Evolução:")
        print(f"   • Trade Threshold: {'✅' if status['global_trade_count'] >= status['target_trades'] else '❌'} "
              f"({status['global_trade_count']}/{status['target_trades']})")
        
        # Safety net (8 horas)
        safety_net_trigger = (datetime.now() - last_evolution) >= timedelta(hours=8)
        print(f"   • Safety Net (8h): {'✅' if safety_net_trigger else '❌'} "
              f"({format_timedelta(datetime.now() - last_evolution)})")
        
        # Status atual
        print(f"\n🔥 Status: {'PODE EVOLUIR' if status['can_evolve'] else 'AGUARDANDO'}")
        if status['trigger_reason']:
            reason_map = {
                'trade_threshold': 'Limite de Trades',
                'safety_net': 'Safety Net (8h)',
                'manual': 'Manual'
            }
            print(f"   Razão: {reason_map.get(status['trigger_reason'], status['trigger_reason'])}")
        
        # Se evolução em progresso
        if status['evolution_in_progress']:
            print(f"\n⚡ EVOLUÇÃO EM PROGRESSO!")
        
        # Estatísticas adicionais
        print(f"\n📈 Estatísticas (24h):")
        try:
            stats = db.get_resolved_trades_stats(hours=24)
            total_stats = stats['total']
            print(f"   • Total de Trades: {total_stats['count']}")
            print(f"   • PnL Total: ${total_stats['total_pnl'] or 0:.2f}")
            print(f"   • PnL Médio: ${total_stats['avg_pnl'] or 0:.4f}")
            
            if stats['by_bot']:
                print(f"   • Por Bot:")
                for bot_stat in sorted(stats['by_bot'], key=lambda x: x['count'], reverse=True)[:5]:
                    print(f"     - {bot_stat['bot_name']}: {bot_stat['count']} trades, "
                          f"${bot_stat['total_pnl'] or 0:.2f}")
        except Exception as e:
            print(f"   Erro ao carregar estatísticas: {e}")
        
        # Histórico de evoluções
        print(f"\n📚 Histórico de Evoluções:")
        try:
            history = db.get_evolution_history(limit=5)
            if history:
                for event in history:
                    created = datetime.fromisoformat(event['created_at'])
                    trigger = event.get('trigger_reason', 'unknown')
                    survivors = len(json.loads(event['survivors']))
                    new_bots = len(json.loads(event['new_bots']))
                    print(f"   • {created.strftime('%d/%m %H:%M')} - {trigger} - "
                          f"{survivors} sobreviventes, {new_bots} novos")
            else:
                print("   Nenhuma evolução registrada")
        except Exception as e:
            print(f"   Erro ao carregar histórico: {e}")
        
        print("="*60)
        
    except Exception as e:
        print(f"❌ Erro ao obter status: {e}")
        import traceback
        traceback.print_exc()


def monitor_continuous(interval=30):
    """Monitora continuamente o sistema"""
    print("🔍 Monitor de Evolução iniciado")
    print(f"📊 Atualizando a cada {interval} segundos")
    print("Pressione Ctrl+C para sair\n")
    
    try:
        while True:
            display_status()
            time.sleep(interval)
            # Limpa a tela (funciona na maioria dos terminais)
            print("\033[2J\033[H", end="")
            
    except KeyboardInterrupt:
        print("\n\n👋 Monitor encerrado")


def main():
    parser = argparse.ArgumentParser(description='Monitor de Sistema de Evolução de Bots')
    parser.add_argument('--continuous', '-c', action='store_true',
                       help='Monitorar continuamente')
    parser.add_argument('--interval', '-i', type=int, default=30,
                       help='Intervalo de atualização em segundos (padrão: 30)')
    parser.add_argument('--force-evolution', '-f', action='store_true',
                       help='Forçar evolução manual')
    parser.add_argument('--status', '-s', action='store_true',
                       help='Mostrar status uma vez')
    
    args = parser.parse_args()
    
    if args.force_evolution:
        from evolution_integration import force_evolution
        success = force_evolution()
        if success:
            print("✅ Evolução forçada iniciada")
        else:
            print("❌ Falha ao forçar evolução")
            sys.exit(1)
    
    elif args.continuous:
        monitor_continuous(args.interval)
    
    else:
        display_status()


if __name__ == "__main__":
    main()