@echo off
setlocal
set ROOT=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%scripts\start_dripmotion.ps1"
if errorlevel 1 (
  echo.
  echo [ERROR] Start failed. Press any key to close.
  pause >nul
)
endlocal
