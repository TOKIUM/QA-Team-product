# API仕様書ディレクトリ

## 情報源（Single Source of Truth）

**Excel API仕様書（原本）** を情報源とし、`excel_to_csv.py` でCSVを自動生成する。

| Excel | 対象プロダクト | シート数 | CSV出力先 |
|-------|--------------|---------|----------|
| 【TOKIUM】標準API仕様書（最新版）.xlsx | TOKIUM経費精算 | 50 | `document/` (2-17), `expansion/` (18+) |
| 【TOKIUM電子帳簿保存】API仕様書（最新版）.xlsx | 電子帳簿保存 | 3 | `dencho/` |
| ※最新版※【TOKIUMインボイス・電子帳簿保存】標準API仕様書.xlsx | インボイス+電子帳簿保存 | 17 | `invoicing/` |

## ディレクトリ構成

```
document/
├── *.xlsx              # Excel原本（3ファイル）
├── *.csv               # TOKIUM経費精算 テスト対象API (2-17, 16件)
├── expansion/          # TOKIUM経費精算 拡張API (18+, 将来テスト対象)
├── invoicing/          # TOKIUMインボイス・電子帳簿保存
├── dencho/             # TOKIUM電子帳簿保存
├── archive/            # 旧バージョンCSV (20260630版)
└── README.md
```

## CSV再生成手順

Excel更新時にCSVを再生成する:

```bash
# 全Excel→CSV変換（プロダクト別に自動振り分け）
python excel_to_csv.py

# 既存CSV削除後に再生成
python excel_to_csv.py --clean

# 変換対象の確認のみ
python excel_to_csv.py --dry-run
```

## テスト対象API（document/ 直下、16件）

| # | API名 | メソッド | エンドポイント |
|---|-------|---------|-------------|
| 2 | 従業員取得 | GET | /api/v2/members.json |
| 3 | 部署取得 | GET | /api/v2/groups.json |
| 4 | 役職取得 | GET | /api/v2/posts.json |
| 5 | プロジェクト取得 | GET | /api/v2/projects.json |
| 6 | 承認フロー取得 | GET | /api/v2/approval_flows.json |
| 7 | 申請フォーム取得 | GET | /api/v2/request_types.json |
| 8-9 | 従業員登録バッチ | GET/POST | /api/v2/members/bulk_create_job.json |
| 10-11 | 従業員更新バッチ | GET/POST | /api/v2/members/bulk_update_job.json |
| 12-13 | プロジェクト登録バッチ | GET/POST | /api/v2/projects/bulk_create_job.json |
| 14-15 | プロジェクト更新バッチ | GET/POST | /api/v2/projects/bulk_update_job.json |
| 16-17 | プロジェクト削除バッチ | GET/POST | /api/v2/projects/bulk_delete_job.json |
