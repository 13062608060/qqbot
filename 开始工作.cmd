@echo off
setlocal
title QQ Bot - START WORK (pull + launch)
cd /d "%~dp0"
echo ============================================
echo  START WORK  -  pull latest data, then launch
echo ============================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\handoff-in.ps1" %*
echo.
pause
