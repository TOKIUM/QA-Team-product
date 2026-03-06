@echo off
REM E2Eテスト毎日自動実行バッチ
REM タスクスケジューラから実行される

cd /d "C:\Users\池田尚人\ClaudeCode用\QA-Team-product-e2e-screen-test\e2e-screen-test"

REM Slack Webhook URL（設定済みならコメント解除）
REM set E2E_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXXXX/XXXXX/XXXXX

python -X utf8 run_all_e2e.py

REM テスト完了後にトレンド分析を実行
python -X utf8 analyze_trends.py

exit /b %ERRORLEVEL%
