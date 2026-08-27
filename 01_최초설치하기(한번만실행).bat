@echo off
chcp 65001 > nul
cd /d "%~dp0"
title 카카오톡 환경 설치기

echo ======================================================
echo   카카오톡 고객 자동관리 환경 설치를 시작합니다.
echo ======================================================
echo.

python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ======================================================
echo   설치가 완료되었습니다!
echo ======================================================
pause