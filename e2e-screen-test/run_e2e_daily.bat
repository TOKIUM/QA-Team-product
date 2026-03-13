@echo off
chcp 65001 >nul
setlocal

set "BASE_DIR=%~dp0"
set "LOG_FILE=%BASE_DIR%e2e_daily.log"

echo [%date% %time%] === E2E Daily Test Start === >> "%LOG_FILE%"

cd /d "%BASE_DIR%"

REM Slack Webhook URL（設定済みならコメント解除）
REM set E2E_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXXXX/XXXXX/XXXXX

echo [%date% %time%] Running E2E tests... >> "%LOG_FILE%"
python -X utf8 run_all_e2e.py >> "%LOG_FILE%" 2>&1
set "E2E_RESULT=%ERRORLEVEL%"

echo [%date% %time%] E2E result: %E2E_RESULT% >> "%LOG_FILE%"

echo [%date% %time%] Running trend analysis... >> "%LOG_FILE%"
python -X utf8 analyze_trends.py >> "%LOG_FILE%" 2>&1

echo [%date% %time%] === E2E Daily Test End === >> "%LOG_FILE%"
exit /b %E2E_RESULT%
