@echo off
rem Stop AstrBot (6185/6199) and SnowLuma (5099) started from this folder.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "foreach ($p in 5099,6185,6199) { Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }; Write-Host 'stopped'"
timeout /t 2 /nobreak >nul
