# テンプレートファイル集

MODEL_EXPORT.md で記載されているテンプレートの実体ファイル。
新システム適用時にコピーして使用する。

## 使い方

```powershell
# 1. プロジェクトフォルダを作成
mkdir C:\path\to\{システム名}

# 2. テンプレートをコピー
copy templates\CLAUDE_TEMPLATE.md C:\path\to\{システム名}\CLAUDE.md
copy templates\config_template.py C:\path\to\{システム名}\config.py
copy templates\conftest_template.py C:\path\to\{システム名}\conftest.py
copy templates\pytest.ini C:\path\to\{システム名}\pytest.ini
copy templates\test_template_standalone.py C:\path\to\{システム名}\{機能名}\test_{機能}_{カテゴリ}.py

# 3. 各ファイル内の {プレースホルダー} を実際の値に置換
```

## ファイル一覧

| # | ファイル | 対応方式 | MODEL_EXPORT.md セクション | 説明 |
|---|---------|---------|-------------------------|------|
| 1 | CLAUDE_TEMPLATE.md | 共通 | 1.5 | セッション管理・タスク分割ルール |
| 2 | config_template.py | 方式A | - | BASE_URL・認証情報・Playwright設定 |
| 3 | conftest_template.py | 方式A | - | logged_in_page fixture |
| 4 | pytest.ini | 方式A | - | pytest設定 |
| 5 | test_template_standalone.py | 方式B | 5-2 | 独立スクリプト形式テストコード |
| 6 | .env.example | 共通 | - | 環境変数サンプル |
