@echo off
chcp 65001 > nul
cd /d "%~dp0"
title 신한라이프 카카오톡 고객 관리 프로그램 v2.0

>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
    echo [안내] 관리자 권한으로 실행 중입니다...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

taskkill /f /im pythonw.exe >nul 2>&1
start "" ".venv\Scripts\pythonw.exe" main_app.py
timeout /t 1 > nul
start chrome http://127.0.0.1:15888
exit