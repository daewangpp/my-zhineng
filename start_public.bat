@echo off
chcp 65001 >nul
title CodeTutor Starter
cd /d "%~dp0"
echo ============================================
echo   CodeTutor 一键启动(服务+隧道+守护)
echo ============================================

:: 1. Flask 服务(若 5050 未在监听则启动)
netstat -ano | findstr ":5050" | findstr "LISTENING" >nul
if errorlevel 1 (
  start "CodeTutor-Flask" /min py web_app.py
  echo [1/3] Flask starting...
) else (
  echo [1/3] Flask already running
)

:: 2. Cloudflare 隧道(若未运行则启动,日志写入 TEMP)
tasklist /fi "imagename eq cloudflared.exe" | find /i "cloudflared.exe" >nul
if errorlevel 1 (
  start "CodeTutor-Tunnel" /min cmd /c "cloudflared.exe tunnel --url http://127.0.0.1:5050 > \"%TEMP%\cloudflared.log\" 2>&1"
  echo [2/3] Tunnel starting...
) else (
  echo [2/3] Tunnel already running
)

:: 3. 守护进程(每分钟保活,域名变化自动同步材料)
start "CodeTutor-Watchdog" /min powershell -WindowStyle Hidden -ExecutionPolicy Bypass -File "%~dp0watchdog.ps1"
echo [3/3] Watchdog started

echo.
echo Waiting 18s for tunnel...
timeout /t 18 /nobreak >nul
echo.
echo Local :  http://127.0.0.1:5050
echo Public:
findstr /i "trycloudflare.com" "%TEMP%\cloudflared.log"
echo.
echo Done. You can close this window.
pause
