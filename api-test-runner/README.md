# API Test Runner

TOKIUM 標準 API の自動テストツールです。CSV 仕様書からテストケースを自動生成し、CLI / GUI / スタンドアロン exe で実行できます。

## セットアップ

### 1. Python 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env.example` をコピーして `.env` を作成し、接続先の値を入力します。

```bash
cp .env.example .env
```

`.env` を編集:

```
BASE_URL=https://dev.keihi.com/api/v2
API_KEY=your_actual_api_key
```

## 使い方

### CLI でテスト実行

```bash
# CSV 仕様書 + カスタムテストをすべて実行
python -m api_test_runner run

# CSV ディレクトリを指定
python -m api_test_runner run path/to/csv_dir

# CSV 仕様の一覧を表示（テストは実行しない）
python -m api_test_runner parse
```

### GUI で実行

```bash
python -m api_test_runner gui
```

### スタンドアロン exe（ビルド済みの場合）

```
dist\API Test Runner\API Test Runner.exe
```

## テストの種類

### CSV ベーステスト（自動生成）

`document/` フォルダ内の CSV 仕様書から、以下のパターンで自動生成されます:

- **auth**: 認証あり（200 OK）+ 認証なし（401）
- **pagination**: offset/limit パラメータ付きリクエスト

### カスタムテスト

`config.yaml` の `custom_tests` セクションで定義します:

```yaml
custom_tests:
  - name: health-check
    url_path: payment_requests/reports
    method: GET
    use_auth: true
    expected_status: 200

  - name: get-reports-with-sort
    url_path: payment_requests/reports
    method: GET
    query_params:
      amount_from: 1000
    request_body:
      sort:
        - key: due_at
          order: asc
    use_auth: true
    expected_status: 200
```

各フィールド:

| フィールド | 必須 | 説明 |
|-----------|------|------|
| `name` | Yes | テスト名（結果ファイル名にも使用） |
| `url_path` | Yes | API パス（base_url に続く部分） |
| `method` | No | HTTP メソッド（default: GET） |
| `use_auth` | No | Bearer トークン付与（default: true） |
| `expected_status` | No | 期待するステータスコード（default: 200） |
| `query_params` | No | クエリパラメータ（dict） |
| `request_body` | No | JSON リクエストボディ（dict） |

## ディレクトリ構成

```
api-tests/
├── .env.example          # 環境変数テンプレート
├── .env                  # 環境変数（git 管理外）
├── config.yaml           # テスト設定 + カスタムテスト定義
├── requirements.txt      # Python 依存パッケージ
├── README.md
├── api_test_runner/      # メインパッケージ
│   ├── __init__.py
│   ├── __main__.py       # CLI エントリポイント
│   ├── gui.py            # Tkinter GUI
│   ├── csv_parser.py     # CSV 仕様書パーサー
│   ├── http_client.py    # HTTP クライアント
│   ├── models.py         # データモデル
│   ├── test_runner.py    # テスト実行エンジン
│   └── reporter.py       # レポート生成
├── document/             # API 仕様 CSV ファイル
├── results/              # テスト実行結果（自動生成）
└── docs/
    └── gui-manual.md     # GUI マニュアル
```

## CI/CD

GitHub Actions で毎日 JST 9:00 に自動実行されます。手動実行も可能です。

必要な GitHub Secrets:
- `BASE_URL`: API のベース URL
- `API_KEY`: API 認証キー
