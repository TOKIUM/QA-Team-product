# API テスト追加手順

新しい API をテスト対象に追加する3つの方法。

## 方法 A: CSV 仕様書を配置（推奨）

既存の TOKIUM API 仕様 CSV と同じ形式で `document/` に配置。

### CSV フォーマット

| 列 | 説明 |
|----|------|
| 番号 | API の通し番号 |
| API名 | API の日本語名 |
| URL | フルパス（例: `/api/v2/groups.json`） |
| メソッド | `GET` / `POST` / `PUT` / `DELETE` / `PATCH` |
| リソース名 | レスポンスのルートキー（例: `groups`） |
| 項目名 | パラメータの日本語名 |
| パラメータ名 | 実際のパラメータ名（例: `name`） |
| データ型 | `整数` / `文字列` / `真偽値` / `配列` / `オブジェクト` |
| 必須 | `〇`（必須）または空 |
| 備考 | 制約情報（例: `最大1000`、`"all" or "active"`） |

### 手順

1. CSV ファイルを `document/` に配置
2. `python -m api_test_runner parse` で解析結果を確認
3. 必要に応じて `config.yaml` の `test.search.overrides` に環境固有値を追加
4. `python -m api_test_runner run --dry-run` でテストケース一覧を確認
5. `python -m api_test_runner run` で実行

## 方法 B: OpenAPI 仕様から変換

OpenAPI (Swagger) JSON/YAML がある場合、自動変換可能。

```bash
# CSV に変換
python -m api_test_runner convert openapi.json -o document/new_api.csv

# YAML もサポート
python -m api_test_runner convert openapi.yaml -o document/new_api.csv

# 標準出力で確認
python -m api_test_runner convert openapi.json
```

変換後は方法 A と同様に `parse` → `run --dry-run` → `run` で実行。

### 制限事項

- `$ref` による参照解決は未対応（事前に [swagger-cli bundle](https://github.com/APIDevTools/swagger-cli) 等で解決してください）
- ネストされた requestBody は1階層のみ変換

## 方法 C: config.yaml の custom_tests

CSV 仕様がない、または特殊なテストケースを直接定義。

```yaml
custom_tests:
  - name: health-check
    url_path: payment_requests/reports
    method: GET
    use_auth: true
    expected_status: 200

  - name: create-item
    url_path: items.json
    method: POST
    use_auth: true
    expected_status: 200
    request_body:
      name: "テストアイテム"
      price: 1000

  - name: search-with-params
    url_path: items.json
    method: GET
    use_auth: true
    expected_status: 200
    query_params:
      status: active
      limit: 10
```

### フィールド

| フィールド | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| `name` | Yes | - | テスト名（結果ファイル名にも使用） |
| `url_path` | Yes | - | API パス（`base_url` からの相対パス） |
| `method` | No | `GET` | HTTP メソッド |
| `use_auth` | No | `true` | Bearer トークン付与 |
| `expected_status` | No | `200` | 期待するステータスコード |
| `query_params` | No | `{}` | クエリパラメータ |
| `request_body` | No | `null` | リクエストボディ |

## どの方法を選ぶか

| 条件 | 推奨 |
|------|------|
| TOKIUM 標準 API（CSV 仕様あり） | **方法 A** |
| OpenAPI/Swagger 仕様がある | **方法 B** → A |
| 1-2件の簡易テスト | **方法 C** |
| 外部 API やカスタムエンドポイント | **方法 C** |
