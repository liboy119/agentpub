<#
.SYNOPSIS
    Uninstall the AgentPub ngrok Windows service (created by install_ngrok_service.ps1).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\uninstall_ngrok_service.ps1
#>

[CmdletBinding()]
param(
    [string]$ServiceName = "AgentPubNgrok"
)

$ErrorActionPreference = "Stop"

function Log($msg)  { Write-Host "[$(Get-Date -Format 'HH:mm:ss')]  $msg" -ForegroundColor Cyan }
function Warn($msg) { Write-Host "[$(Get-Date -Format 'HH:mm:ss')]  $msg" -ForegroundColor Yellow }

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $isAdmin) {
    Write-Host "ERROR: must run as Administrator." -ForegroundColor Red; exit 1
}

# find nssm
$nssm = $null
foreach ($p in @("$env:ProgramFiles\nssm-2.24\win64\nssm.exe", "$env:ProgramFiles\nssm\win64\nssm.exe", "C:\tools\nssm\nssm.exe", "C:\nssm\win64\nssm.exe")) {
    if (Test-Path $p) { $nssm = $p; break }
}
if (-not $nssm) { Write-Host "ERROR: nssm.exe not found (use install_ngrok_service.ps1 first or install nssm manually)." -ForegroundColor Red; exit 1 }

$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $svc) {
    Log "Service '$ServiceName' not present. Nothing to do."
    exit 0
}

Log "Stopping $ServiceName ..."
& $nssm stop   $ServiceName 2>&1 | Out-Null
Start-Sleep 2

Log "Removing $ServiceName ..."
& $nssm remove $ServiceName confirm 2>&1 | Out-Null
Start-Sleep 1

$check = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($check) {
    Warn "Service still present, trying sc delete..."
    sc.exe delete $ServiceName
    Start-Sleep 1
}

$final = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($final) {
    Write-Host "ERROR: could not remove service. Run 'sc.exe delete $ServiceName' manually." -ForegroundColor Red
    exit 1
}

Log "DONE  ✅  Service '$ServiceName' removed."
