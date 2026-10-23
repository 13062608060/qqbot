@echo off
setlocal
title QQ Bot - END WORK (stop + commit + push)
cd /d "%~dp0"
echo ============================================
echo  END WORK  -  stop, commit data, push
echo ============================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\handoff-out.ps1" %*
echo.
pause
