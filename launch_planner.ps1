$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$url = "http://127.0.0.1:8765/"

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

$python = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $python) {
    $python = (Get-Command py.exe -ErrorAction SilentlyContinue).Source
}
if (-not $python) {
    throw "Python не найден в PATH."
}

Start-Process -FilePath $python -ArgumentList @("run.py") `
    -WorkingDirectory $root -WindowStyle Hidden

$ready = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
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
    throw "Планировщик не ответил вовремя: $url. Проверьте, не занят ли порт 8765 другим процессом."
}
