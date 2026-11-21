<#
.SYNOPSIS
    Daftar Scheduled Task "AI Office Hub" (per-user, At log on) untuk auto-start semua service.

.DESCRIPTION
    PENTING: script ini MENGUBAH SISTEM (cipta Scheduled Task). USER sendiri kena run
    -- bukan dijalankan automatik oleh mana-mana tool/agent.

    Apa yang dibuat:
      - Trigger : At log on (user semasa sahaja)
      - Action  : powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass
                  -File "<projek>\scripts\start-office.ps1"
      - Run level: Limited (BUKAN admin), hanya bila user log on (Interactive)
      - Setting : boleh start di bateri, tak henti bila bateri, restart 3x kalau gagal

    Script print rancangan dulu. Guna -Dry untuk print sahaja. Kalau task dah wujud,
    guna -Force untuk ganti.

    Buang semula: scripts\unregister-autostart.ps1

.PARAMETER Dry
    Print apa yang akan dibuat, tak daftar apa-apa.

.PARAMETER Force
    Ganti task sedia ada (kalau tak, script berhenti bila task dah wujud).

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\register-autostart.ps1 -Dry
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\register-autostart.ps1
#>
[CmdletBinding()]
param(
    [switch]$Dry,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$TaskName = 'AI Office Hub'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$StartScript = Join-Path $Root 'scripts\start-office.ps1'
if (-not (Test-Path $StartScript)) { throw "start-office.ps1 tak jumpa: $StartScript" }

$user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$psExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$arguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$StartScript`""

Write-Host 'Rancangan:'
Write-Host "  Task name : $TaskName"
Write-Host "  User      : $user (Limited, Interactive)"
Write-Host '  Trigger   : At log on'
Write-Host "  Action    : $psExe $arguments"
Write-Host "  Work dir  : $Root"
Write-Host ''

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Task '$TaskName' dah wujud." -ForegroundColor Yellow
}

if ($Dry) {
    Write-Host '[DRY] Tiada apa didaftar.' -ForegroundColor Yellow
    exit 0
}

if ($existing -and -not $Force) {
    Write-Host 'Guna -Force untuk ganti, atau unregister-autostart.ps1 dulu.' -ForegroundColor Red
    exit 1
}

$action = New-ScheduledTaskAction -Execute $psExe -Argument $arguments -WorkingDirectory $Root
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $user
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Seconds 0)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings `
    -Description 'Start AI Office Hub (serve, reverb, queue, schedule) bila log on.' -Force | Out-Null

Write-Host "Siap: task '$TaskName' didaftar. Test sekarang: Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Green
