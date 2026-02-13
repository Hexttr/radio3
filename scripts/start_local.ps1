# NavoRadio — запуск для локальной разработки
# Запускает Icecast, broadcaster и Flask в отдельных окнах

$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $projectRoot

$icecastExe = "C:\Program Files\Icecast\icecast.exe"
$icecastConfig = Join-Path $projectRoot "local\icecast.xml"

if (-not (Test-Path $icecastExe)) {
    Write-Host "Icecast не найден: $icecastExe" -ForegroundColor Red
    Write-Host "Скачай и установи: https://icecast.org/download/" -ForegroundColor Yellow
    exit 1
}

Write-Host "Запуск Icecast..." -ForegroundColor Cyan
$icecastDir = Split-Path $icecastExe
Start-Process -FilePath $icecastExe -ArgumentList "-c", $icecastConfig -WorkingDirectory $icecastDir -WindowStyle Normal

Start-Sleep -Seconds 2

Write-Host "Запуск Broadcaster..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; .\.venv\Scripts\Activate.ps1; python run_broadcaster.py" -WindowStyle Normal

Start-Sleep -Seconds 2

Write-Host "Запуск Flask..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; .\.venv\Scripts\Activate.ps1; python run.py" -WindowStyle Normal

Write-Host "`nГотово! Открой http://127.0.0.1:5000" -ForegroundColor Green
