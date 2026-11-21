<#
.SYNOPSIS
    Start semua service AI Office Hub (web, Reverb, queue, scheduler) dalam tetingkap tersembunyi.

.DESCRIPTION
    Service yang dimulakan (semua guna php dari PATH atau WinGet, log ke storage\logs\ops-*.log):
      1. serve     : php artisan serve --host=127.0.0.1 --port=8000 --no-reload   (PHP_CLI_SERVER_WORKERS=4)
      2. reverb    : php artisan reverb:start                                     (websocket, port 8081)
      3. queue     : php artisan queue:work --tries=3 --sleep=1
      4. schedule  : php artisan schedule:work

    Service yang dah running akan di-skip (detect ikut command line php.exe via
    Win32_Process), jadi selamat untuk run berulang kali. Lepas start, script tunggu
    dan print jadual health (HTTP /up & /login, TCP 8000 & 8081).

    Boleh dipanggil dari mana-mana cwd; root projek = $PSScriptRoot\..

    Nota: --no-reload diperlukan oleh Laravel supaya PHP_CLI_SERVER_WORKERS dihormati.
    Di Windows, PHP built-in server mungkin abaikan multi-worker (ia ciri fork/Unix) --
    tak rosakkan apa-apa, cuma kekal single worker.

.PARAMETER Dry
    Print apa yang akan dibuat sahaja, tak start apa-apa.

.PARAMETER WaitSeconds
    Berapa lama tunggu health check lepas (default 40).

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start-office.ps1
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start-office.ps1 -Dry
#>
[CmdletBinding()]
param(
    [switch]$Dry,
    [int]$WaitSeconds = 40
)

$ErrorActionPreference = 'Stop'

# ---------- Resolve root & php ----------
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Artisan = Join-Path $Root 'artisan'
$LogDir = Join-Path $Root 'storage\logs'

function Resolve-Php {
    $cmd = Get-Command php -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cmd -and $cmd.Source) { return $cmd.Source }
    $hit = Get-ChildItem -Path "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\PHP.PHP.8.3_*\php.exe" -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($hit) { return $hit.FullName }
    throw 'php.exe tak jumpa. Install: winget install PHP.PHP.8.3  (atau tambah php ke PATH).'
}

$Php = Resolve-Php
if (-not (Test-Path $Artisan)) { throw "artisan tak jumpa di $Root" }
if (-not $Dry -and -not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

# ---------- Definisi service ----------
# Pattern = regex untuk kenal command line php.exe yang berkaitan.
$Services = @(
    @{ Name = 'serve';    Args = @('serve', '--host=127.0.0.1', '--port=8000', '--no-reload'); Pattern = 'artisan"?\s+serve(\s|$)' }
    @{ Name = 'reverb';   Args = @('reverb:start');                                            Pattern = 'artisan"?\s+reverb:start' }
    @{ Name = 'queue';    Args = @('queue:work', '--tries=3', '--sleep=1');                    Pattern = 'artisan"?\s+queue:work' }
    @{ Name = 'schedule'; Args = @('schedule:work');                                           Pattern = 'artisan"?\s+schedule:work' }
)

function Get-PhpProcesses {
    Get-CimInstance Win32_Process -Filter "Name = 'php.exe'" -ErrorAction SilentlyContinue
}

function Test-Tcp([int]$Port) {
    $c = New-Object System.Net.Sockets.TcpClient
    try {
        $iar = $c.BeginConnect('127.0.0.1', $Port, $null, $null)
        if ($iar.AsyncWaitHandle.WaitOne(1000) -and $c.Connected) { return $true }
        return $false
    } catch { return $false } finally { $c.Close() }
}

function Test-Http([string]$Url) {
    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
        return [int]$r.StatusCode
    } catch {
        if ($_.Exception.Response) { return [int]$_.Exception.Response.StatusCode }
        return 0
    }
}

Write-Host "Projek : $Root"
Write-Host "PHP    : $Php"
Write-Host "Log    : $LogDir\ops-*.log"
if ($Dry) { Write-Host '[DRY] Tiada apa akan distart.' -ForegroundColor Yellow }
Write-Host ''

# ---------- Start ----------
$procs = Get-PhpProcesses
foreach ($svc in $Services) {
    $existing = $procs | Where-Object { $_.CommandLine -and $_.CommandLine -match $svc.Pattern }
    if ($existing) {
        $ids = ($existing | ForEach-Object { $_.ProcessId }) -join ','
        Write-Host ("[SKIP] {0,-9} dah running (PID {1})" -f $svc.Name, $ids) -ForegroundColor DarkGray
        continue
    }

    $argList = @("`"$Artisan`"") + $svc.Args
    $out = Join-Path $LogDir ("ops-{0}.out.log" -f $svc.Name)
    $err = Join-Path $LogDir ("ops-{0}.err.log" -f $svc.Name)

    if ($Dry) {
        Write-Host ("[DRY ] {0,-9} {1} {2}" -f $svc.Name, $Php, ($argList -join ' '))
        Write-Host ("       log -> {0} / {1}" -f $out, $err)
        continue
    }

    # Simpan log lama (satu generasi) supaya tak hilang bila restart
    foreach ($f in @($out, $err)) {
        if (Test-Path $f) { Move-Item -LiteralPath $f -Destination "$f.1" -Force -ErrorAction SilentlyContinue }
    }

    $prevWorkers = $env:PHP_CLI_SERVER_WORKERS
    if ($svc.Name -eq 'serve') { $env:PHP_CLI_SERVER_WORKERS = '4' }
    try {
        $p = Start-Process -FilePath $Php -ArgumentList $argList -WorkingDirectory $Root `
            -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput $out -RedirectStandardError $err
        Write-Host ("[START] {0,-9} PID {1}" -f $svc.Name, $p.Id) -ForegroundColor Green
    } finally {
        $env:PHP_CLI_SERVER_WORKERS = $prevWorkers
    }
}

if ($Dry) {
    Write-Host ''
    Write-Host '[DRY] Lepas start, health check: GET /up, GET /login (200), TCP 8000 & 8081.'
    exit 0
}

# ---------- Health table ----------
Write-Host ''
Write-Host "Tunggu health check (maks ${WaitSeconds}s)..."
$deadline = (Get-Date).AddSeconds($WaitSeconds)
do {
    $rows = @(
        [pscustomobject]@{ Check = 'HTTP /up';      OK = ((Test-Http 'http://127.0.0.1:8000/up') -eq 200) }
        [pscustomobject]@{ Check = 'HTTP /login';   OK = ((Test-Http 'http://127.0.0.1:8000/login') -eq 200) }
        [pscustomobject]@{ Check = 'TCP 8000 (web)';OK = (Test-Tcp 8000) }
        [pscustomobject]@{ Check = 'TCP 8081 (ws)'; OK = (Test-Tcp 8081) }
    )
    $allOk = -not ($rows | Where-Object { -not $_.OK })
    if ($allOk) { break }
    Start-Sleep -Seconds 2
} while ((Get-Date) -lt $deadline)

$rows | ForEach-Object {
    $st = if ($_.OK) { 'OK' } else { 'GAGAL' }
    $col = if ($_.OK) { 'Green' } else { 'Red' }
    Write-Host ("  {0,-16} {1}" -f $_.Check, $st) -ForegroundColor $col
}

Write-Host ''
if ($allOk) {
    Write-Host 'Semua sihat. Buka http://127.0.0.1:8000' -ForegroundColor Green
    exit 0
}
Write-Host "Ada yang gagal. Semak log: $LogDir\ops-*.err.log dan laravel.log" -ForegroundColor Red
exit 1
