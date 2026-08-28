@echo off
chcp 65001 > nul
cd /d "%~dp0"
title 신한라이프 카카오톡 고객 관리 프로그램

>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
    echo [안내] 마우스 및 카카오톡 제어를 위해 관리자 권한으로 실행합니다...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

taskkill /f /im pythonw.exe >nul 2>&1
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im 카카오톡_고객자동관리.exe >nul 2>&1

timeout /t 1 > nul
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" main_app.py
) else (
    start "" "카카오톡_고객자동관리.exe"
)

timeout /t 1 > nul
start chrome http://127.0.0.1:15899
exit