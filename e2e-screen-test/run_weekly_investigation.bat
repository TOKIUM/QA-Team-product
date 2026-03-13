@echo off
chcp 65001 >nul
setlocal

set "BASE_DIR=%~dp0"
set "LOG_FILE=%BASE_DIR%weekly_investigation.log"

echo [%date% %time%] === Weekly Investigation Start === >> "%LOG_FILE%"

cd /d "%BASE_DIR%"

REM Slack Webhook URL（設定済みならコメント解除）
REM set E2E_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXXXX/XXXXX/XXXXX

echo [%date% %time%] Running investigation scripts... >> "%LOG_FILE%"
python -X utf8 run_weekly_investigation.py >> "%LOG_FILE%" 2>&1
set "RESULT=%ERRORLEVEL%"

echo [%date% %time%] Result: %RESULT% >> "%LOG_FILE%"
echo [%date% %time%] === Weekly Investigation End === >> "%LOG_FILE%"
exit /b %RESULT%
