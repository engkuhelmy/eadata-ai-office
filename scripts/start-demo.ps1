<#
  start-demo.ps1: mulakan demo 5 staff (office:demo) di latar, 24 jam.
  Mesyuarat ramai-ramai, kerja di meja, chill. Sesi demo TIDAK ditamatkan.
  Guna: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start-demo.ps1 [-Hours 24] [-Speed 1] [-Dry]
  Prasyarat: web, Reverb, queue worker dan scheduler jalan (scripts\start-office.ps1).
#>
param([int]$Hours = 24, [double]$Speed = 1, [switch]$Dry)

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$php = (Get-Command php -ErrorAction SilentlyContinue).Source
if (-not $php) { $php = (Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\PHP.PHP.8.3_*\php.exe" -ErrorAction SilentlyContinue | Select-Object -First 1).FullName }
if (-not $php) { Write-Error 'php tak dijumpai'; exit 1 }

$running = Get-CimInstance Win32_Process -Filter "Name='php.exe'" | Where-Object { $_.CommandLine -match 'office:demo' }
if ($running) { Write-Host "[SKIP] demo dah jalan (PID $($running.ProcessId -join ','))"; exit 0 }

# Path projek ada ruang ("ai office virtual 3D"): mesti dipetik supaya php dapat baca artisan
$demoArgs = @("`"$root\artisan`"", 'office:demo', "--hours=$Hours", "--speed=$Speed")
$log = Join-Path $root 'storage\logs\ops-demo.out.log'
if ($Dry) { Write-Host "[DRY] $php $($demoArgs -join ' ')"; Write-Host "      log -> $log"; exit 0 }

$p = Start-Process -FilePath $php -ArgumentList $demoArgs -WorkingDirectory $root -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $log -RedirectStandardError (Join-Path $root 'storage\logs\ops-demo.err.log')
Write-Host "[START] demo PID $($p.Id), $Hours jam, speed $Speed. Log: $log"
