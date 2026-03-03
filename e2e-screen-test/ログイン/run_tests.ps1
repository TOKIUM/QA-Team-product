# =============================================================
# テスト実行スクリプト
# 使い方: .\run_tests.ps1
# =============================================================

# .env ファイルから環境変数を読み込み
$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
            Write-Host "  SET $key" -ForegroundColor Green
        }
    }
    Write-Host ""
} else {
    Write-Host "[ERROR] .env ファイルが見つかりません" -ForegroundColor Red
    exit 1
}

# テスト実行
Write-Host "テスト実行中..." -ForegroundColor Cyan
pytest generated_tests/test_tokium_login.py -v --headed
