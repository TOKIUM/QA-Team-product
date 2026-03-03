# QA-Team-product

QAチームが作成したテスト自動化ツール群。

## ツール一覧

| ブランチ | ツール | 概要 |
|---|---|---|
| `tool/pdf-test-data-generator` | PDFテストデータ生成 | ファイルアップロードテスト用のPDF・各種ファイルを生成 |
| `tool/api-test-runner` | APIテスト自動化 | TOKIUM標準APIの自動テスト（CSV→テスト生成→実行→レポート） |

## 使い方

各ツールはブランチごとに管理しています。使いたいツールのブランチをチェックアウトしてください。

```bash
git clone https://github.com/TOKIUM/QA-Team-product.git
cd QA-Team-product
git checkout tool/api-test-runner  # 使いたいツールのブランチ
```

詳細は各ブランチの README.md を参照してください。
