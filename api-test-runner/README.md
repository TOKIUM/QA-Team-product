# API Test Runner

TOKIUM 標準 API の自動テストツール。CSV 仕様書からテストケースを自動生成し、CLI / GUI / Web UI の3モードで実行できます。

## セットアップ

```bash
pip install -r requirements.txt
pip install -r requirements-web.txt  # Web UI を使う場合
```

`.env.example` をコピーして `.env` を作成:

```bash
cp .env.example .env
```

```
BASE_URL=https://dev.keihi.com/api/v2
API_KEY=your_actual_api_key
```

## 使い方

### CLI

```bash
python -m api_test_runner run                     # 全 CSV を実行
python -m api_test_runner run path/to/csv_dir     # CSV ディレクトリ指定
python -m api_test_runner run --pattern auth,search  # パターン指定
python -m api_test_runner run --api groups,members   # API 指定
python -m api_test_runner run --env staging        # 環境切替（.env.staging）
python -m api_test_runner run --method POST,PUT     # メソッド指定
python -m api_test_runner run --failed-only        # 前回失敗分のみ再実行
python -m api_test_runner run --dry-run            # テストケース一覧のみ表示

python -m api_test_runner parse                    # CSV 仕様一覧
python -m api_test_runner check                    # プリフライトチェック（接続・認証・設定）
python -m api_test_runner diff                     # 直近2回のレスポンス差分
python -m api_test_runner diff --ts1 20260309 --ts2 20260308  # 指定回の差分
python -m api_test_runner trend                    # パフォーマンストレンド分析
python -m api_test_runner trend --last 20          # 直近20回分
```

### GUI

```bash
python -m api_test_runner gui
```

### Web UI

```bash
python -m api_test_runner web                      # http://127.0.0.1:8000
python -m api_test_runner web --port 3000          # ポート指定
start_web.bat                                      # Windows: ブラウザ自動起動
```

Web UI の機能:
- **テスト実行** (`/run`): CSV 選択・パターン選択・リアルタイム進捗・結果テーブル・詳細パネル
- **レスポンス閲覧** (`/response`): JSON シンタックスハイライト付きレスポンス表示
- **実行履歴** (`/history`): 過去の実行結果一覧
- **設定** (`/settings`): 接続先・パターン・Slack 通知の設定

## テストパターン

CSV 仕様書から以下のパターンでテストケースを自動生成します:

| パターン | 説明 | デフォルト |
|---------|------|-----------|
| `auth` | 認証あり(200) + 認証なし(401) | ON |
| `pagination` | offset/limit パラメータ検証 | ON |
| `search` | 各パラメータでの検索（overrides 値使用） | ON |
| `boundary` | limit/offset の境界値（負数/ゼロ/上限超過） | ON |
| `missing_required` | 必須パラメータ欠損で 400 を期待 | ON |
| `post_normal` | POST 正常系リクエスト + データ比較 | **OFF** |
| `put_normal` | PUT 正常系リクエスト | OFF |
| `delete_normal` | DELETE 正常系リクエスト | OFF |
| `patch_normal` | PATCH 正常系リクエスト | OFF |

> **注意**: `post_normal` / `put_normal` / `delete_normal` / `patch_normal` は実データを作成・変更・削除します。テスト環境でのみ有効化してください。

### カスタムテスト

`config.yaml` の `custom_tests` セクションで定義:

```yaml
custom_tests:
  - name: health-check
    url_path: payment_requests/reports
    method: GET
    use_auth: true
    expected_status: 200
    query_params:
      amount_from: 1000
    request_body:
      sort:
        - key: due_at
          order: asc
```

| フィールド | 必須 | 説明 |
|-----------|------|------|
| `name` | Yes | テスト名（結果ファイル名にも使用） |
| `url_path` | Yes | API パス（base_url に続く部分） |
| `method` | No | HTTP メソッド（default: GET） |
| `use_auth` | No | Bearer トークン付与（default: true） |
| `expected_status` | No | 期待するステータスコード（default: 200） |
| `query_params` | No | クエリパラメータ（dict） |
| `request_body` | No | JSON リクエストボディ（dict） |

## 設定 (config.yaml)

主要な設定項目:

```yaml
test:
  patterns: [auth, pagination, search, boundary, missing_required]
  timeout: 30
  concurrency: 3              # 並列スレッド数
  retry:
    max_retries: 2
    delay: 1.0
  response_validation:
    enabled: true
    required_fields_check: true
    pagination_count_check: true
  post_normal:
    data_comparison:
      enabled: true           # POST 前後のデータ比較
    individual_only: [...]    # --api 指定時のみ実行する API
    body_overrides: {...}     # API 別のリクエストボディ上書き
  boundary:
    api_overrides: {...}      # API 別の期待ステータス上書き

notification:
  slack:
    webhook_url: ""           # 設定すると Slack 通知
    on_failure_only: true
```

詳細: [docs/config-reference.md](docs/config-reference.md) | API 追加手順: [docs/how-to-add-api.md](docs/how-to-add-api.md)

## ディレクトリ構成

```
api-test-runner/
├── config.yaml               # テスト設定 + カスタムテスト定義
├── .env / .env.example        # 環境変数（API_KEY, BASE_URL）
├── requirements.txt           # CLI/GUI 依存（requests, pyyaml, pytest）
├── requirements-web.txt       # Web UI 依存（fastapi, uvicorn, jinja2）
├── start_web.bat              # Web UI 起動スクリプト
├── api_test_runner/           # メインパッケージ
│   ├── __main__.py            # CLI エントリポイント（7サブコマンド）
│   ├── csv_parser.py          # CSV 仕様書パーサー
│   ├── test_generator.py      # テストケース自動生成（9パターン）
│   ├── test_runner.py         # テスト実行エンジン
│   ├── http_client.py         # HTTP クライアント（リトライ・タイムアウト）
│   ├── validator.py           # JSON スキーマ検証
│   ├── reporter.py            # レポート生成（JSON/HTML/CSV）
│   ├── notifier.py            # Slack 通知
│   ├── preflight.py           # プリフライトチェック
│   ├── diff.py                # レスポンス差分検知
│   ├── trend.py               # パフォーマンストレンド分析
│   ├── gui.py                 # Tkinter GUI
│   └── web/                   # Web UI（FastAPI）
│       ├── app.py             # ルーティング・API エンドポイント
│       └── run_manager.py     # バックグラウンドテスト実行管理
├── static/                    # Web UI 静的ファイル（CSS/JS）
├── templates/                 # Jinja2 テンプレート
├── document/                  # API 仕様 CSV ファイル
├── results/                   # テスト実行結果（自動生成）
├── tests/                     # ユニットテスト（351件）
└── docs/                      # ドキュメント
```

## テスト

```bash
pytest                         # 全テスト実行
pytest -q                      # 簡潔出力
pytest tests/test_validator.py # 特定ファイル
pytest -k "search"             # キーワードフィルタ
```

## CI/CD

GitHub Actions で毎日 JST 9:00 に自動実行（現在は手動実行のみ有効）。

必要な GitHub Secrets:
- `BASE_URL`: API のベース URL
- `API_KEY`: API 認証キー
