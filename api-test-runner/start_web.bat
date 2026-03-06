@echo off
cd /d "%~dp0"
start "" http://127.0.0.1:8000
ping -n 3 127.0.0.1 >nul
python -m api_test_runner web
