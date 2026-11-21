<#
.SYNOPSIS
    Stop service AI Office Hub (serve, reverb, queue, scheduler).

.DESCRIPTION
    Hanya bunuh proses php.exe yang command line-nya:
      - mengandungi path projek ini, ATAU
      - ialah salah satu command artisan: serve / reverb:start / queue:work / schedule:work
        (termasuk child `php -S 127.0.0.1:8000` dari artisan serve).
    Proses php lain (projek lain) tak disentuh.

    Boleh dipanggil dari mana-mana cwd; root projek = $PSScriptRoot\..

.PARAMETER Dry
    Print proses yang akan dihentikan, tak bunuh apa-apa.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\stop-office.ps1
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\stop-office.ps1 -Dry
#>
[CmdletBinding()]
param(
    [switch]$Dry
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$rootEsc = [regex]::Escape($Root)
$artisanRe = 'artisan"?\s+(serve|reverb:start|queue:work|schedule:work)(\s|$)'
$builtinRe = '-S\s+127\.0\.0\.1:8000\b'   # child php -S dari artisan serve

$targets = Get-CimInstance Win32_Process -Filter "Name = 'php.exe'" -ErrorAction SilentlyContinue |
    Where-Object {
        $_.CommandLine -and (
            $_.CommandLine -match $rootEsc -or
            $_.CommandLine -match $artisanRe -or
            $_.CommandLine -match $builtinRe
        )
    }

if (-not $targets) {
    Write-Host 'Tiada proses AI Office Hub yang running.' -ForegroundColor DarkGray
    exit 0
}

foreach ($p in $targets) {
    $cmd = $p.CommandLine
    if ($cmd.Length -gt 110) { $cmd = $cmd.Substring(0, 107) + '...' }
    if ($Dry) {
        Write-Host ("[DRY ] akan stop PID {0}: {1}" -f $p.ProcessId, $cmd)
        continue
    }
    try {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
        Write-Host ("[STOP] PID {0}: {1}" -f $p.ProcessId, $cmd) -ForegroundColor Green
    } catch {
        # mungkin dah mati sebab parent-nya dibunuh dulu
        Write-Host ("[SKIP] PID {0} dah tiada" -f $p.ProcessId) -ForegroundColor DarkGray
    }
}

if ($Dry) { Write-Host '[DRY] Tiada apa dihentikan.' -ForegroundColor Yellow }
