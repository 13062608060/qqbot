@echo off
rem Start SnowLuma (WebUI http://127.0.0.1:5099)
rem Uses the bundled node.exe, no Node.js install required.
rem Console output (including the one-time WebUI bootstrap password) is written to
rem snowluma\logs\console.log so it can be looked up after the window scrolls.
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%snowluma"
title SnowLuma
echo Starting SnowLuma - WebUI initial password is in logs\console.log
"%ROOT%snowluma\node.exe" .\index.mjs > "%ROOT%snowluma\logs\console.log" 2>&1
pause
