# Robust GitHub Actions log fetch over a flaky tunnel DNS.
# Every HTTP call pins the host to an address resolved via a public resolver.
param([string[]]$RunIds)

$ErrorActionPreference = "Continue"
$token = (Get-Content "G:\AgentPub\.env.tokens" | Select-String "^GITHUB_TOKEN=").ToString() -replace "^GITHUB_TOKEN=", ""

function Resolve-HostIp([string]$HostName) {
    foreach ($srv in @("8.8.8.8", "223.5.5.5", "114.114.114.114", "1.1.1.1")) {
        $out = nslookup $HostName $srv 2>&1 | Out-String
        foreach ($m in [regex]::Matches($out, "Addresses?:\s*(\d+\.\d+\.\d+\.\d+)")) {
            if ($m.Groups[1].Value -ne $srv) { return $m.Groups[1].Value }
        }
    }
    # known-good fallbacks when every resolver is flaky
    if ($HostName -eq "api.github.com") { return "140.82.114.6" }
    if ($HostName -eq "github.com") { return "140.82.114.4" }
    return $null
}

function Get-Pinned([string]$Url, [string[]]$ExtraHeaders = @(), [string]$OutFile = "") {
    $u = [Uri]$Url
    $ip = Resolve-HostIp $u.Host
    if (-not $ip) { return $null }
    $args = @("-sS", "-m", "90", "--resolve", "$($u.Host):443:$ip",
        "-H", "Authorization: Bearer $token", "-H", "User-Agent: agentpub")
    foreach ($h in $ExtraHeaders) { $args += @("-H", $h) }
    if ($OutFile) { $args += @("-o", $OutFile) }
    $args += $Url
    & curl.exe @args 2>$null
}

$apiIp = Resolve-HostIp "api.github.com"
Write-Output "api.github.com -> $apiIp"
if (-not $apiIp) { Write-Output "cannot resolve api.github.com"; exit 1 }

foreach ($rid in $RunIds) {
    $jobsJson = Get-Pinned "https://api.github.com/repos/liboy119/agentpub/actions/runs/$rid/jobs?per_page=20"
    if (-not $jobsJson) { Write-Output "run $rid : jobs fetch failed"; continue }
    try { $jobs = ($jobsJson | ConvertFrom-Json).jobs } catch { Write-Output "run $rid : json parse failed"; continue }
    Write-Output "run $rid : $($jobs.Count) job(s)"
    foreach ($job in $jobs) {
        Write-Output ("=" * 72)
        Write-Output "$($job.name) | $($job.conclusion)"
        Write-Output ("=" * 72)
        $hdrFile = "$env:TEMP\ap_job_hdr.txt"
        $loc = $null
        for ($i = 0; $i -lt 5 -and -not $loc; $i++) {
            & curl.exe -sS -m 40 -D $hdrFile -o NUL --resolve "api.github.com:443:$apiIp" `
                -H "Authorization: Bearer $token" -H "User-Agent: agentpub" `
                "https://api.github.com/repos/liboy119/agentpub/actions/jobs/$($job.id)/logs" 2>$null
            $l = (Get-Content $hdrFile -ErrorAction SilentlyContinue | Select-String -Pattern "^location:" | Select-Object -First 1)
            if ($l) { $loc = $l.ToString() -replace "^location:\s*", "" -replace "\s+$", "" }
            else { Start-Sleep -Seconds 4 }
        }
        if (-not $loc) { Write-Output "  (no log redirect)"; continue }
        $u = [Uri]$loc
        $blobIp = Resolve-HostIp $u.Host
        if (-not $blobIp) { Write-Output "  (cannot resolve $($u.Host))"; continue }
        $text = & curl.exe -sS -m 90 --resolve "$($u.Host):443:$blobIp" "https://$($u.Host)$($u.PathAndQuery)" 2>$null
        if ($text) {
            ($text -split "`n") | Where-Object { $_.Trim() -ne "" } | Select-Object -Last 50
        } else { Write-Output "  (log body empty)" }
    }
}
