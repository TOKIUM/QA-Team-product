# QA-Team-product

QAチームが作成したテスト自動化ツール群。

## ツール一覧

| ブランチ | ツール | 概要 |
|---|---|---|
| `tool/api-test-runner` | APIテスト自動化 | TOKIUM標準APIの自動テスト。CSV仕様書→テスト自動生成→実行→レポート。CLI/GUI/Web UI対応。46API・398テスト・段階展開(`--stage`)・JSONスキーマ検証・Excel→CSV自動変換 |
| `tool/e2e-screen-test` | E2E画面テスト | PlaywrightによるE2Eテスト自動化（19画面・300テスト・5カテゴリ・毎朝自動実行） |
| `tool/testcase-evaluator` | テストケース評価 | テスト項目書（Excel）を100点満点で自動評価。6チェック項目+観点評価。テスト項目書の自動生成機能付き |
| `tool/pdf-test-data-generator` | PDFテストデータ生成 | ファイルアップロードテスト用のPDF・各種ファイルを生成 |
| `tool/qa-bug-replay` | QA Bug Replay | バグ発見時に直近30秒の動画+Consoleログ+Networkリクエストを自動保存するChrome拡張 |

## 使い方

各ツールはブランチごとに管理しています。使いたいツールのブランチをチェックアウトしてください。

```bash
git clone https://github.com/TOKIUM/QA-Team-product.git
cd QA-Team-product
git checkout tool/api-test-runner  # 使いたいツールのブランチ
```

詳細は各ブランチの README.md を参照してください。
