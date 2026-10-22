@echo off
rem Start AstrBot first (OneBot reverse-WS server on 6199), then SnowLuma.
setlocal
set "ROOT=%~dp0"
start "AstrBot" /min cmd /c ""%ROOT%start-astrbot.bat""
timeout /t 8 /nobreak >nul
start "SnowLuma" /min cmd /c ""%ROOT%start-snowluma.bat""
echo AstrBot: http://127.0.0.1:6185
echo SnowLuma: http://127.0.0.1:5099
timeout /t 5 /nobreak >nul
