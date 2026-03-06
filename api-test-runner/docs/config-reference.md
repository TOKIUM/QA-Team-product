# config.yaml リファレンス

config.yaml の全オプションの説明。

## api

API 接続設定。

| キー | 型 | デフォルト | 説明 |
|------|-----|-----------|------|
| `api.base_url` | string | (必須) | API のベース URL (例: `https://dev.keihi.com/api/v2`) |
| `api.auth.type` | string | `bearer` | 認証方式。現在は `bearer` のみ対応 |
| `api.auth.token_env` | string | `API_KEY` | Bearer トークンを格納する環境変数名。`.env` から読み込み |

## test

テスト実行設定。

### 基本設定

| キー | 型 | デフォルト | 説明 |
|------|-----|-----------|------|
| `test.methods` | list[string] | `["GET"]` | テスト対象の HTTP メソッド。`GET`, `POST`, `PUT`, `DELETE`, `PATCH` |
| `test.timeout` | int | `30` | HTTP リクエストタイムアウト（秒） |
| `test.concurrency` | int | `1` | 同時実行数。1=逐次実行、2以上=並行実行 |

### test.patterns

有効化するテストパターンのリスト。

| パターン名 | 説明 |
|-----------|------|
| `auth` | 認証あり(200) + 認証なし(401) テスト |
| `pagination` | offset/limit パラメータテスト |
| `search` | 各パラメータでの検索テスト |
| `boundary` | limit/offset の境界値テスト（負数/ゼロ/上限/上限超過） |
| `missing_required` | 必須パラメータ欠損テスト（400 を期待） |
| `post_normal` | POST 正常系テスト（実データ登録のためテスト環境でのみ有効化） |
| `put_normal` | PUT 正常系テスト |
| `delete_normal` | DELETE 正常系テスト |
| `patch_normal` | PATCH 正常系テスト |
| `crud_chain` | POST→GET→DELETE→GET チェーンテスト（`crud_chain.enabled: true` が別途必要） |
| `invalid_body` | 型不正値テスト（空ボディ、フィールド型不一致） |

### test.pagination

| キー | 型 | デフォルト | 説明 |
|------|-----|-----------|------|
| `test.pagination.offset` | int | `0` | pagination テストで使用する offset 値 |
| `test.pagination.limit` | int | `5` | pagination テストで使用する limit 値 |

### test.search

| キー | 型 | デフォルト | 説明 |
|------|-----|-----------|------|
| `test.search.overrides` | dict | `{}` | パラメータ名ごとのテスト値を上書き。環境依存値（UUID 等）の指定に使用 |

### test.boundary

| キー | 型 | デフォルト | 説明 |
|------|-----|-----------|------|
| `test.boundary.overflow_expected_status` | int | `400` | limit 上限超過時の期待ステータス |
| `test.boundary.offset_negative_expected_status` | int | `400` | offset 負数の期待ステータス |
| `test.boundary.offset_large_value` | int | `999999` | offset 巨大値テストの値 |
| `test.boundary.offset_large_expected_status` | int | `200` | offset 巨大値の期待ステータス（空配列） |
| `test.boundary.api_overrides` | dict | `{}` | API ごとの期待ステータス上書き |

`api_overrides` の各 API に設定可能なキー:

| キー | 説明 |
|------|------|
| `negative_expected_status` | limit 負数の期待ステータス |
| `zero_expected_status` | limit ゼロの期待ステータス |
| `overflow_expected_status` | limit 上限超過の期待ステータス |
| `offset_negative_expected_status` | offset 負数の期待ステータス |
| `offset_large_value` | offset 巨大値テストの値 |
| `offset_large_expected_status` | offset 巨大値の期待ステータス |

### test.missing_required

| キー | 型 | デフォルト | 説明 |
|------|-----|-----------|------|
| `test.missing_required.expected_status` | int | `400` | 必須パラメータ欠損時の期待ステータス |
| `test.missing_required.api_overrides` | dict | `{}` | API ごとの上書き |

`api_overrides` の各 API に設定可能なキー:

| キー | 説明 |
|------|------|
| `expected_status` | 期待ステータスの上書き |
| `skip_fields` | テスト対象から除外するフィールドパス（CSV 上は必須だが API 実装では任意な場合） |

### test.post_normal / put_normal / delete_normal / patch_normal

各メソッドの正常系テスト設定。構造は共通。

| キー | 型 | デフォルト | 説明 |
|------|-----|-----------|------|
| `test.<method>_normal.expected_status` | int | `200` | 正常系の期待ステータス |
| `test.<method>_normal.api_overrides` | dict | `{}` | API ごとの期待ステータス上書き |

### test.crud_chain

| キー | 型 | デフォルト | 説明 |
|------|-----|-----------|------|
| `test.crud_chain.enabled` | bool | `false` | CRUD チェーンテストの有効化 |
| `test.crud_chain.id_field` | string | `"id"` | POST レスポンスから ID を取得するフィールド名 |
| `test.crud_chain.delete_url_pattern` | string | `"{url_path}/{id}"` | DELETE/GET(確認) の URL パターン |
| `test.crud_chain.post_expected_status` | int | `200` | POST ステップの期待ステータス |
| `test.crud_chain.delete_expected_status` | int | `200` | DELETE ステップの期待ステータス |
| `test.crud_chain.verify_delete_expected_status` | int | `404` | 削除確認 GET の期待ステータス |
| `test.crud_chain.api_overrides` | dict | `{}` | API ごとの上書き |

### test.invalid_body

| キー | 型 | デフォルト | 説明 |
|------|-----|-----------|------|
| `test.invalid_body.expected_status` | int | `400` | 型不正値の期待ステータス |
| `test.invalid_body.api_overrides` | dict | `{}` | API ごとの上書き |

### test.response_validation

レスポンスボディの内容検証設定（WARN 判定、テスト結果には影響しない）。

| キー | 型 | デフォルト | 説明 |
|------|-----|-----------|------|
| `test.response_validation.enabled` | bool | `false` | レスポンスボディ検証の有効化 |
| `test.response_validation.pagination_count_check` | bool | `true` | limit=N のとき結果が N 件以下かチェック |
| `test.response_validation.required_fields_check` | bool | `true` | リソース配列の各要素で同じキーが存在するかチェック |
| `test.response_validation.json_schema_check` | bool | `false` | APISpec パラメータ定義からフィールド名・型を検証 |
| `test.response_validation.json_schema_skip_params` | list[string] | `[]` | 型検証から追加で除外するパラメータ名。`offset`, `limit`, `fields` は常に除外 |

> **注意**: `pagination_count_check`, `required_fields_check`, `json_schema_check` はすべて `enabled: true` が前提条件です。`enabled: false` の場合、個別オプションの値に関わらず検証は実行されません。

### test.error_body_validation

| キー | 型 | デフォルト | 説明 |
|------|-----|-----------|------|
| `test.error_body_validation` | bool | `false` | エラーレスポンス（400/401）のボディ構造検証 |

### test.retry

| キー | 型 | デフォルト | 説明 |
|------|-----|-----------|------|
| `test.retry.max_retries` | int | `2` | 5xx/接続エラー時の最大リトライ回数 |
| `test.retry.delay` | float | `1.0` | 初回リトライ待機秒（指数バックオフ） |

## output

| キー | 型 | デフォルト | 説明 |
|------|-----|-----------|------|
| `output.results_dir` | string | `"results"` | テスト結果の保存ディレクトリ |
| `output.json_indent` | int | `4` | レスポンス JSON のインデント幅 |

## notification

Slack 通知設定。

| キー | 型 | デフォルト | 説明 |
|------|-----|-----------|------|
| `notification.slack.webhook_url` | string | `""` | Slack Incoming Webhook URL。空なら通知しない |
| `notification.slack.on_failure_only` | bool | `true` | `true` なら FAIL 時のみ通知 |

## custom_tests

手動定義のテストケースリスト。CSV 仕様に含まれない API のテストに使用。

各エントリのフィールド:

| キー | 型 | 必須 | デフォルト | 説明 |
|------|-----|------|-----------|------|
| `name` | string | Yes | - | テスト名（結果ファイル名に使用） |
| `url_path` | string | Yes | - | API パス（base_url からの相対パス） |
| `method` | string | No | `"GET"` | HTTP メソッド |
| `query_params` | dict | No | `{}` | クエリパラメータ |
| `request_body` | dict | No | `null` | リクエストボディ |
| `use_auth` | bool | No | `true` | 認証トークンを付与するか |
| `expected_status` | int | No | `200` | 期待する HTTP ステータスコード |
