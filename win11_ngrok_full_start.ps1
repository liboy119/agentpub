# Win11 PowerShell — Start ngrok forward to AgentPub on Kali
# 用法: powershell -ExecutionPolicy Bypass -File win11_ngrok_full_start.ps1
# 输出一行 "URL: https://xxxx.ngrok-free.dev"

$ErrorActionPreference = 'Stop'

$ngrok = Get-Command ngrok -ErrorAction SilentlyContinue
if (-not $ngrok) {
  $candidate = "C:\Program Files\ngrok\ngrok.exe"
  if (Test-Path $candidate) { $ngrok = $candidate }
  if (-not $ngrok) {
    $c2 = "$env:LOCALAPPDATA\ngrok\ngrok.exe"
    if (Test-Path $c2) { $ngrok = $c2 }
  }
}
if (-not $ngrok) {
  Write-Host "ngrok not found. Install from https://ngrok.com/download"
  Write-Host "Run as admin once:"
  Write-Host "  choco install ngrok"
  Write-Host "OR download ngrok.exe and put it in C:\tools\ngrok\"
  exit 1
}

$cfg = "$env:USERPROFILE\.ngrok2\ngrok.yml"
if (-not (Test-Path $cfg)) {
  Write-Host "$cfg missing. Steps:"
  Write-Host "  1. signup https://dashboard.ngrok.com/signup"
  Write-Host "  2. copy authtoken from https://dashboard.ngrok.com/get-started/your-authtoken"
  Write-Host "  3. run: ngrok config add-authtoken <TOKEN>"
  exit 1
}

Write-Host "starting: $ngrok http 192.168.2.11:7700"
Write-Host "Public URL appears at http://localhost:4040/api/tunnels (machine-local)"
Write-Host "Ngrok's API port 4040 is also forwarded to kali via watchdog cron"

& $ngrok http 192.168.2.11:7700
