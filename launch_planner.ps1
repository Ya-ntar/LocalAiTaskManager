$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$url = "http://127.0.0.1:8765/"
$logOut = Join-Path $root "startup-debug.log"
$logErr = Join-Path $root "startup-error.log"

$lmStudioCandidates = @(
    (Join-Path $env:LOCALAPPDATA "Programs\LM Studio\LM Studio.exe"),
    (Join-Path $env:LOCALAPPDATA "LM Studio\LM Studio.exe"),
    (Join-Path $env:ProgramFiles "LM Studio\LM Studio.exe")
)
$lmStudio = $lmStudioCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($lmStudio) {
    Start-Process -FilePath $lmStudio
    Start-Sleep -Seconds 3
} else {
    Write-Warning "LM Studio не найден. Укажите путь в launch_planner.ps1."
}

try {
    $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 1
    if ($response.StatusCode -eq 200) {
        Start-Process $url
        exit 0
    }
} catch {
    # Сервер еще не запущен — запускаем его ниже.
}

$pythonCandidates = @(
    (Join-Path $root ".venv\Scripts\python.exe"),
    ((Get-Command python.exe -ErrorAction SilentlyContinue).Source),
    ((Get-Command py.exe -ErrorAction SilentlyContinue).Source)
)
$python = $pythonCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $python) {
    throw "Python не найден в PATH."
}

if (Test-Path $logOut) { Remove-Item -LiteralPath $logOut -Force }
if (Test-Path $logErr) { Remove-Item -LiteralPath $logErr -Force }
Start-Process -FilePath $python -ArgumentList @("run.py") `
    -WorkingDirectory $root -WindowStyle Hidden `
    -RedirectStandardOutput $logOut -RedirectStandardError $logErr

$ready = $false
for ($attempt = 0; $attempt -lt 60; $attempt++) {
    try {
        $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 1
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        Start-Sleep -Milliseconds 500
    }
}

if ($ready) {
    Start-Process $url
} else {
    $details = if (Test-Path $logErr) {
        Get-Content -LiteralPath $logErr -Raw -ErrorAction SilentlyContinue
    } else { "" }
    throw "Планировщик не ответил вовремя: $url. Лог: $logOut. Ошибка: $details"
}
