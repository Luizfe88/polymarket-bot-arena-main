# =====================================================
# monitor-bankroll.ps1 - Relógio em Tempo Real
# =====================================================

$apiUrl = "http://127.0.0.1:8510/api/wallet"

# Configurações
$intervaloMinutos = 1
$perc_por_bot = 0.15   # 15%
$perc_global = 0.50    # 30% (Ajustado para igualar o bot)

# Variáveis de controle de tempo
$proximaAtualizacaoAPI = [DateTime]::MinValue
$bankrollCache = 0
$lossPorBotCache = 0
$lossGlobalCache = 0
$statusMsg = "Iniciando..."

while ($true) {
    $agora = Get-Date

    # --- LÓGICA DE ATUALIZAÇÃO DA API (Roda a cada X minutos) ---
    if ($agora -ge $proximaAtualizacaoAPI) {
        $statusMsg = "🔄 Atualizando dados..."
        try {
            $response = Invoke-WebRequest -Uri $apiUrl -Method Get -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
            
            if ($response) {
                $json = $response.Content | ConvertFrom-Json
                
                # Tenta pegar o valor do bankroll
                if ($json.virtual_equity) {
                    $bankrollCache = [double]$json.virtual_equity
                } elseif ($json.virtual_available -and $json.invested_open) {
                    $bankrollCache = [double]$json.virtual_available + [double]$json.invested_open
                }
                
                # Calcula os limites se tiver saldo
                if ($bankrollCache -gt 0) {
                    $lossPorBotCache = [math]::Round($bankrollCache * $perc_por_bot, 2)
                    $lossGlobalCache = [math]::Round($bankrollCache * $perc_global, 2)
                    $statusMsg = "✅ Dados atualizados"
                }
            }
        } catch {
            $statusMsg = "⚠️ Tentando conectar..."
        }
        
        # Define a próxima atualização para daqui a 1 minuto
        $proximaAtualizacaoAPI = $agora.AddMinutes($intervaloMinutos)
    }

    # --- LÓGICA DE DESENHO NA TELA (Roda a cada 1 segundo) ---
    Clear-Host
    
    # Cálculo do tempo restante para próxima atualização da API
    $tempoRestante = $proximaAtualizacaoAPI - $agora
    $segundosRestantes = [math]::Ceiling($tempoRestante.TotalSeconds)

    Write-Host "===========================================" -ForegroundColor Green
    
    if ($bankrollCache -gt 0) {
        Write-Host "Bankroll atual (real-time): `$$bankrollCache" -ForegroundColor Green
        Write-Host "Limite perda por bot      : `$$lossPorBotCache  (15%)" -ForegroundColor Green
        Write-Host "Limite perda global       : `$$lossGlobalCache (50%)" -ForegroundColor Green
    } else {
        Write-Host "Aguardando dados do servidor..." -ForegroundColor Yellow
    }

    # AQUI ESTÁ O RELÓGIO QUE VOCÊ QUERIA
    Write-Host "Hora atual                : $($agora.ToString('HH:mm:ss'))" -ForegroundColor Green
    Write-Host "===========================================" -ForegroundColor Green
    
    # Barra de status e contagem regressiva
    Write-Host "Status: $statusMsg" -ForegroundColor Cyan
    Write-Host "Próxima verificação do saldo em: $segundosRestantes segundos..." -ForegroundColor DarkGray
    
    # Pausa de 1 segundo para fazer o relógio andar
    Start-Sleep -Seconds 1
}