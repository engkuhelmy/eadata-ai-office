<#
.SYNOPSIS
    Buang Scheduled Task "AI Office Hub" (lawan kepada register-autostart.ps1).

.DESCRIPTION
    USER kena run sendiri (ia ubah sistem). Tak stop service yang tengah running --
    guna scripts\stop-office.ps1 untuk tu.

.PARAMETER Dry
    Print sahaja, tak buang.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\unregister-autostart.ps1
#>
[CmdletBinding()]
param(
    [switch]$Dry
)

$ErrorActionPreference = 'Stop'
$TaskName = 'AI Office Hub'

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Host "Task '$TaskName' tak wujud. Takde apa nak buang." -ForegroundColor DarkGray
    exit 0
}

Write-Host "Akan buang Scheduled Task '$TaskName'."
if ($Dry) {
    Write-Host '[DRY] Tiada apa dibuang.' -ForegroundColor Yellow
    exit 0
}

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "Siap: task '$TaskName' dibuang." -ForegroundColor Green
