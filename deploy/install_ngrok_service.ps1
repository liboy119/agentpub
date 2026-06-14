<#
.SYNOPSIS
    Install ngrok as a Windows service (NSSM). Auto-start on boot, auto-restart on crash.

.DESCRIPTION
    Registers an ngrok tunnel to the local AgentPub server (port 7700) as a Windows
    service. Uses NSSM (Non-Sucking Service Manager) to install/start it.

    Auto-restart on crash: NSSM is configured with AppThrottle=5000ms so a crashed
    ngrok is restarted within 5s.

    Idempotent: re-running updates the service config in place.

.PARAMETER NgrokExe
    Path to ngrok.exe. Default: C:\tools\ngrok\ngrok.exe

.PARAMETER Domain
    ngrok named tunnel domain. Default: flavia-asphyxial-unfamiliarly.ngrok-free.dev

.PARAMETER LocalPort
    Port to expose. Default: 7700  (the AgentPub uvicorn server)

.PARAMETER ServiceName
    Windows service name to register. Default: AgentPubNgrok

.PARAMETER NssmUrl
    NSSM download URL. Default: latest 2.24 win64 zip from nssm.cc

.EXAMPLE
    # Default (most common case):
    powershell -ExecutionPolicy Bypass -File .\install_ngrok_service.ps1

.EXAMPLE
    # Custom ngrok path / domain:
    powershell -ExecutionPolicy Bypass -File .\install_ngrok_service.ps1 `
        -NgrokExe "D:\apps\ngrok\ngrok.exe" `
        -Domain "mydomain.ngrok-free.dev" `
        -LocalPort 7700

.NOTES
    Requires:  PowerShell 5.1+  AND  Admin (right-click → "Run as administrator")
    Tested on: Windows 10/11
    Logs:      C:\tools\ngrok\service.log
    State:     Get-Service AgentPubNgrok
#>

[CmdletBinding()]
param(
    [string]$NgrokExe = "C:\tools\ngrok\ngrok.exe",
    [string]$Domain = "flavia-asphyxial-unfamiliarly.ngrok-free.dev",
    [int]$LocalPort = 7700,
    [string]$ServiceName = "AgentPubNgrok",
    [string]$NssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
)

$ErrorActionPreference = "Stop"
$ProgressPreference   = "SilentlyContinue"

function Log($msg) { Write-Host "[$(Get-Date -Format 'HH:mm:ss')]  $msg" -ForegroundColor Cyan }
function Warn($msg) { Write-Host "[$(Get-Date -Format 'HH:mm:ss')]  $msg" -ForegroundColor Yellow }
function Fail($msg) { Write-Host "[$(Get-Date -Format 'HH:mm:ss')]  $msg" -ForegroundColor Red; throw $msg }

# --- 0. Admin check ---
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $isAdmin) {
    Fail "Must run as Administrator. Right-click PowerShell → 'Run as administrator'."
}
Log "Admin: OK"

# --- 1. Locate or install NSSM ---
function Find-Nssm {
    # Common locations
    $candidates = @(
        "$env:ProgramFiles\nssm-2.24\win64\nssm.exe",
        "$env:ProgramFiles\nssm\win64\nssm.exe",
        "C:\tools\nssm\nssm.exe",
        "C:\nssm\win64\nssm.exe"
    )
    foreach ($p in $candidates) { if (Test-Path $p) { return $p } }
    return $null
}

$nssm = Find-Nssm
if (-not $nssm) {
    Log "NSSM not found, downloading from $NssmUrl ..."
    $tmp = Join-Path $env:TEMP "nssm-install"
    if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
    New-Item -ItemType Directory -Path $tmp | Out-Null
    $zip = Join-Path $tmp "nssm.zip"
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $NssmUrl -OutFile $zip -UseBasicParsing
    } catch {
        Fail "NSSM download failed: $_  (check firewall / try -NssmUrl manually)"
    }
    Expand-Archive -Path $zip -DestinationPath $tmp -Force
    $src = Get-ChildItem -Path $tmp -Recurse -Filter "nssm.exe" | Where-Object { $_.FullName -like "*win64*" } | Select-Object -First 1
    if (-not $src) { Fail "nssm.exe not found in zip (looked for *win64*)" }
    $destDir = "$env:ProgramFiles\nssm-2.24"
    New-Item -ItemType Directory -Path "$destDir\win64" -Force | Out-Null
    Copy-Item $src.FullName "$destDir\win64\nssm.exe" -Force
    $nssm = "$destDir\win64\nssm.exe"
    Log "NSSM installed to $nssm"
} else {
    Log "NSSM found: $nssm"
}

# --- 2. Validate ngrok.exe ---
if (-not (Test-Path $NgrokExe)) {
    Fail "ngrok.exe not found at $NgrokExe  (set -NgrokExe)"
}
Log "ngrok.exe: $NgrokExe"

# --- 3. Quick ngrok health ---
$ngrokVer = & $NgrokExe version 2>&1 | Select-Object -First 1
Log "ngrok version: $ngrokVer"

# --- 4. Remove existing service (clean install) ---
$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    Log "Service '$ServiceName' exists, stopping & removing for clean install..."
    & $nssm stop   $ServiceName 2>&1 | Out-Null
    Start-Sleep 2
    & $nssm remove $ServiceName confirm 2>&1 | Out-Null
    Start-Sleep 1
}

# --- 5. Install service ---
$ngrokDir = Split-Path $NgrokExe -Parent
$ngrokLog = Join-Path $ngrokDir "service.log"

Log "Installing service '$ServiceName'..."
& $nssm install $ServiceName $NgrokExe 2>&1 | Out-Null
& $nssm set $ServiceName AppParameters "http $LocalPort --domain=$Domain" 2>&1 | Out-Null
& $nssm set $ServiceName AppDirectory $ngrokDir 2>&1 | Out-Null
& $nssm set $ServiceName DisplayName "AgentPub ngrok tunnel ($Domain)" 2>&1 | Out-Null
& $nssm set $ServiceName Description  "Exposes local AgentPub server ($LocalPort) via $Domain. Auto-restart on crash." 2>&1 | Out-Null
& $nssm set $ServiceName Start SERVICE_AUTO_START 2>&1 | Out-Null
& $nssm set $ServiceName AppStdout $ngrokLog 2>&1 | Out-Null
& $nssm set $ServiceName AppStderr $ngrokLog 2>&1 | Out-Null
& $nssm set $ServiceName AppRotateFiles 1 2>&1 | Out-Null
& $nssm set $ServiceName AppRotateBytes 10485760 2>&1 | Out-Null       # 10 MB
& $nssm set $ServiceName AppRotateOnline 1 2>&1 | Out-Null
& $nssm set $ServiceName AppThrottle 5000 2>&1 | Out-Null              # 5 s between restarts
& $nssm set $ServiceName AppExitCodes Default 2>&1 | Out-Null
& $nssm set $ServiceName AppRestartDelay 0 2>&1 | Out-Null
& $nssm set $ServiceName AppNoConsole 0 2>&1 | Out-Null
& $nssm set $ServiceName AppStopMethodSkip 6 2>&1 | Out-Null           # skip Console / Ctrl-C handlers

Log "Service config applied."

# --- 6. Start service ---
& $nssm start $ServiceName 2>&1 | Out-Null
Start-Sleep 3

# --- 7. Verify ---
$svc = Get-Service -Name $ServiceName
Log "Service status: $($svc.Status)"
if ($svc.Status -ne "Running") {
    Warn "Service did not start cleanly. Last 30 lines of log ($ngrokLog):"
    if (Test-Path $ngrokLog) {
        Get-Content $ngrokLog -Tail 30
    }
    Fail "Service not running. See log above."
}

# --- 8. Quick health ping (optional, doesn't block) ---
Log "Service installed and running. Health check via:  curl https://$Domain/"
Log "Useful commands:"
Log "  Get-Service $ServiceName"
Log "  nssm edit $ServiceName   (GUI editor)"
Log "  nssm restart $ServiceName"
Log "  Remove-Service + reinstall:  .\install_ngrok_service.ps1"
Log ""
Log "DONE  ✅  ngrok now runs as a Windows service, auto-starts on boot, restarts on crash."
