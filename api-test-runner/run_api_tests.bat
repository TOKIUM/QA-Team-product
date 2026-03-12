@echo off
REM タスクスケジューラ用APIテスト自動実行バッチ
REM 終了コード: 0=全PASS、1=FAIL有り

cd /d "%~dp0"

REM results ディレクトリ確認
if not exist results mkdir results

REM 読み取り系テストを非対話実行（JSON出力をファイル保存）
python -m api_test_runner run --pattern auth,pagination,search,boundary,missing_required --output-json-file results\latest_run.json

exit /b %ERRORLEVEL%
