# =====================================================
# run-both.ps1 - Arena foreground + Monitor intercalado a cada 5 min
# =====================================================

Write-Host "Iniciando Arena + Monitor Bankroll" -ForegroundColor Cyan
Write-Host "Arena rodando normalmente. Atualizações do bankroll a cada 5 min." -ForegroundColor Yellow
Write-Host "Pressione Ctrl+C para parar" -ForegroundColor Yellow
Write-Host ""

# Configurações do monitor
$apiUrl            = "http://127.0.0.1:8510/api/wallet"
$intervaloMinutos  = 1
$intervaloSegundos = $intervaloMinutos * 60
$perc_por_bot      = 0.15
$perc_global       = 0.50

$ultimaAtualizacao = Get-Date -Date "2000-01-01"

function Update-Bankroll {
    try {
        $response = Invoke-WebRequest -Uri $apiUrl -Method Get -TimeoutSec 5 -UseBasicParsing
        $json = $response.Content | ConvertFrom-Json
        
        $bankroll = if ($json.virtual_equity) { [double]$json.virtual_equity }
                    elseif ($json.virtual_available -and $json.invested_open) { [double]$json.virtual_available + [double]$json.invested_open }
                    else { 0 }

        if ($bankroll -gt 0) {
            $loss_por_bot = [math]::Round($bankroll * $perc_por_bot, 2)
            $loss_global = [math]::Round($bankroll * $perc_global, 2)

            Write-Host "" -NoNewline
            Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
            Write-Host "BANKROLL ATUALIZADO (a cada $intervaloMinutos min)" -ForegroundColor Green
            Write-Host "Bankroll atual          : `$$bankroll" -ForegroundColor Green
            Write-Host "Limite perda por bot    : `$$loss_por_bot  (15%)" -ForegroundColor Green
            Write-Host "Limite perda global     : `$$loss_global (30%)" -ForegroundColor Green
            Write-Host "Última atualização: $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Cyan
            Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
            Write-Host "" -NoNewline
        }
    } catch {
        Write-Host "Erro ao atualizar bankroll: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Roda o arena diretamente em foreground (logs fluem normalmente)
try {
    python arena.py
}
catch {
    Write-Host "Arena interrompido." -ForegroundColor Yellow
}
finally {
    Write-Host ""
    Write-Host "Sessão encerrada." -ForegroundColor Green
}