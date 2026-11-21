<#
  stop-demo.ps1: hentikan proses office:demo. Staff demo TIDAK ditamatkan: mereka kekal dalam office
  (sweep akan chill mereka ke bilik bermain). Guna: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\stop-demo.ps1
#>
$procs = Get-CimInstance Win32_Process -Filter "Name='php.exe'" | Where-Object { $_.CommandLine -match 'office:demo' }
if (-not $procs) { Write-Host '[INFO] tiada demo berjalan'; exit 0 }
foreach ($p in $procs) { Stop-Process -Id $p.ProcessId -Force; Write-Host "[STOP] demo PID $($p.ProcessId)" }
