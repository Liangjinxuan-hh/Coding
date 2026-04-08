@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -Command "Stop-Job -Name bridge,web -ErrorAction SilentlyContinue; Remove-Job -Name bridge,web -ErrorAction SilentlyContinue; Write-Host 'DripMotion jobs stopped.'"
endlocal
