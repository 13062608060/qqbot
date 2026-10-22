@echo off
rem Start AstrBot (WebUI http://127.0.0.1:6185, OneBot reverse WS 127.0.0.1:6199)
setlocal
set "ROOT=%~dp0"
set "PATH=%ROOT%runtime\bin;%PATH%"
cd /d "%ROOT%astrbot"
title AstrBot
astrbot run
pause
