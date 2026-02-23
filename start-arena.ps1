# =====================================================
# start-arena.ps1 - 100% AUTOMÁTICO (prioriza /api/wallet)
# =====================================================

$bankroll = $null

Write-Host "🔍 Buscando Bankroll em http://127.0.0.1:8510/api/wallet ..." -ForegroundColor Cyan

# === Prioriza /api/wallet ===
$baseUrl = "http://127.0.0.1:8510"
$priorityEndpoints = @("/api/wallet", "/api/overview", "/api/status", "/api/earnings", "/api/balance")

foreach ($ep in $priorityEndpoints) {
    try {
        $url = $baseUrl + $ep
        $response = Invoke-WebRequest -Uri $url -Method Get -TimeoutSec 4 -UseBasicParsing
        
        $body = $response.Content
        Write-Host "DEBUG: Response de ${url} (raw body): $body" -ForegroundColor Yellow  # DEBUG para ver o corpo
        
        # Parse como JSON
        try {
            $json = $body | ConvertFrom-Json
            if ($json.virtual_equity) { 
                $bankroll = [double]$json.virtual_equity 
            } elseif ($json.virtual_bankroll) {
                $bankroll = [double]$json.virtual_bankroll
            } elseif ($json.virtual_available -and $json.invested_open) {
                $bankroll = [double]$json.virtual_available + [double]$json.invested_open
            } elseif ($json.available -and $json.invested) {
                $bankroll = [double]$json.available + [double]$json.invested
            } elseif ($json.balance) {
                $bankroll = [double]$json.balance
            }
        } catch {
            Write-Host "DEBUG: Não é JSON válido" -ForegroundColor Yellow
        }
        
        if ($bankroll -and $bankroll -gt 0) {
            Write-Host "✅ Bankroll obtido de $ep" -ForegroundColor Green
            break
        }
    } catch {
        Write-Host "⚠️ Erro ao acessar ${url}: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# === Fallback: Lê do log mais recente ===
if (-not $bankroll -or $bankroll -le 0) {
    $latestLog = Get-ChildItem -Path "." -Filter "*.log" -Recurse | 
                 Sort-Object LastWriteTime -Descending | 
                 Select-Object -First 1
    
    if ($latestLog) {
        try {
            $lastLines = Get-Content $latestLog.FullName -Tail 300
            $available = $null
            $invested = $null
            foreach ($line in $lastLines) {
                if ($line -match "(?i)Bankroll.*?\$?([\d\.]+)") {
                    $bankroll = [double]$matches[1]
                    break
                } elseif ($line -match "(?i)Available.*?\$?([\d\.]+)") {
                    $available = [double]$matches[1]
                } elseif ($line -match "(?i)Invested.*?\$?([\d\.]+)") {
                    $invested = [double]$matches[1]
                }
                if ($available -and $invested) { $bankroll = $available + $invested; break }
            }
            if ($bankroll) { Write-Host "✅ Bankroll lido do log mais recente" -ForegroundColor Green }
        } catch {}
    }
}

# === Último fallback ===
if (-not $bankroll -or $bankroll -le 0) {
    $bankroll = 13.06
    Write-Host "⚠️ Usando fallback: `$13.06" -ForegroundColor Yellow
}

# ==============================================================================
# 3. GESTÃO DE RISCO DINÂMICA 10/10 (Tiered + Drawdown Scaling)
# ==============================================================================

# === Tiers automáticos baseados na banca real ===
if ($bankroll -lt 10)   { $riskProfile = "UltraSafe" }      # banca crítica
elseif ($bankroll -lt 25) { $riskProfile = "Conservative" } # nossa faixa atual ($13)
else                      { $riskProfile = "Balanced" }

# Porcentagens por perfil (ajustadas pro Polymarket 2026)
switch ($riskProfile) {
    "UltraSafe"     { 
        $pct_trade_size      = 0.015   # 1.5%
        $pct_bot_exposure    = 0.06
        $pct_global_exposure = 0.15
        $pct_loss_bot        = 0.10
        $pct_loss_global     = 0.22
    }
    "Conservative"  { 
        $pct_trade_size      = 0.023   # 2.3% ← ideal pra $13
        $pct_bot_exposure    = 0.075
        $pct_global_exposure = 0.20
        $pct_loss_bot        = 0.125
        $pct_loss_global     = 0.27
    }
    "Balanced"      { 
        $pct_trade_size      = 0.032
        $pct_bot_exposure    = 0.09
        $pct_global_exposure = 0.25
        $pct_loss_bot        = 0.14
        $pct_loss_global     = 0.30
    }
}

# Cálculos
$loss_por_bot     = [math]::Round($bankroll * $pct_loss_bot, 2)
$loss_global      = [math]::Round($bankroll * $pct_loss_global, 2)
$dyn_max_pos_global = [math]::Round($bankroll * $pct_global_exposure, 2)
$dyn_max_pos_bot  = [math]::Round($bankroll * $pct_bot_exposure, 2)
$dyn_trade_size   = [math]::Round($bankroll * $pct_trade_size, 2)

# === PISOS DE LIQUIDEZ REAIS (2026) ===
if ($dyn_trade_size -lt 0.90)   { $dyn_trade_size = 0.90 }   # mínimo viável
if ($dyn_max_pos_bot -lt 1.20)  { $dyn_max_pos_bot = 1.20 }
if ($dyn_max_pos_global -lt 2.50) { $dyn_max_pos_global = 2.50 }

# === DRAW DOWN SCALING 2.0 ===
$initialBankroll = if (Test-Path "$PSScriptRoot\arena_peak.json") {
    (Get-Content "$PSScriptRoot\arena_peak.json" | ConvertFrom-Json).peak
} else { $bankroll }
$dd_ratio = $bankroll / $initialBankroll 
 if ($dd_ratio -lt 0.85) { 
     $dyn_trade_size = [math]::Round($dyn_trade_size * 0.60, 2)   # -40% 
     $dyn_max_pos_global = [math]::Round($dyn_max_pos_global * 0.65, 2) 
     $env:BOT_ARENA_TRADE_MAX_SIZE = "$dyn_trade_size" 
     Write-Host "🚨 DRAW DOWN CRÍTICO ($([math]::Round((1-$dd_ratio)*100))%) - RISCO CORTADO 35-40%" -ForegroundColor Red 
 } 
 elseif ($dd_ratio -lt 0.92) { 
     $dyn_trade_size = [math]::Round($dyn_trade_size * 0.78, 2)   # -22% 
     Write-Host "⚠️ Drawdown moderado - risco reduzido 22%" -ForegroundColor Magenta
 }

# Salva peak (pra próxima execução)
@{ peak = [math]::Max($initialBankroll, $bankroll) } | ConvertTo-Json | Set-Content "$PSScriptRoot\arena_peak.json"

# === PAINEL 10/10 ===
Clear-Host
Write-Host "==========================================" -ForegroundColor Green
Write-Host " POLYMARKET ARENA 10/10 - $riskProfile MODE" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host "💰 Banca Atual      : `$$bankroll" -ForegroundColor White
Write-Host "📉 Perfil de Risco  : $riskProfile" -ForegroundColor Cyan
Write-Host "🛑 Stop Global      : `$$loss_global ($([math]::Round($pct_loss_global*100))%)" -ForegroundColor Red
Write-Host "📊 Max Global       : `$$dyn_max_pos_global" -ForegroundColor Yellow
Write-Host "🤖 Max por Bot      : `$$dyn_max_pos_bot" -ForegroundColor Yellow
Write-Host "🎲 Tamanho Trade    : `$$dyn_trade_size" -ForegroundColor Cyan
Write-Host "🔢 Máx Posições     : 4" -ForegroundColor White
Write-Host "==========================================" -ForegroundColor Green

# 4. Variáveis de ambiente (adicionadas as novas)
$env:BOT_ARENA_PAPER_DAILY_LOSS_LIMIT       = "$loss_por_bot"
$env:BOT_ARENA_PAPER_GLOBAL_DAILY_LOSS_LIMIT = "$loss_global"
$env:BOT_ARENA_PAPER_MAX_POSITION           = "$dyn_max_pos_global"
$env:BOT_ARENA_PAPER_MAX_POSITION_PER_BOT   = "$dyn_max_pos_bot"
$env:BOT_ARENA_TRADE_MAX_SIZE               = "$dyn_trade_size"
$env:BOT_ARENA_MAX_OPEN_TRADES              = "8"
$env:BOT_ARENA_TRADE_MIN_TTE_SECONDS        = "60"  # 30 segundos mínimo
$env:BOT_ARENA_TRADE_MAX_TTE_SECONDS        = "14400"  # 5 minutos para mercados 5min

Write-Host "🚀 Arena iniciando em modo $riskProfile (liquidez otimizada)..." -ForegroundColor Green
python arena.py
