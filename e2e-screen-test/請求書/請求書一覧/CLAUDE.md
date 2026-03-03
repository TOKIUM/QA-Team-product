# 請求書一覧画面 E2Eテストプロジェクト

## 作業ルール（必ず守ること）

### タスク分割ルール
- **1回の応答では1タスクだけ実行する**。複数タスクの指示を受けた場合、最初のタスクのみ実行し、完了後に「次のタスクに進みますか？」とユーザーに確認する。
- タスクの区切りの目安:
  - ファイル1つの作成・修正 = 1タスク
  - テスト1スイートの実行・修正 = 1タスク
  - 画面1つの解析 = 1タスク
- 複数ファイルにまたがる変更でも、論理的に1つの変更であれば1タスクとして扱ってよい。

### コンテキスト節約ルール
- ANALYSIS_REPORT_*.md は**必要なセクションだけ**を読む。全体を一度に読まない。
- テストファイルの内容確認が必要な場合、対象ファイルだけを読む。関連ファイルを先回りで読まない。
- スクリーンショット（.png）は指示がない限り読み込まない。

## プロジェクト概要
TOKIUM 請求書発行（ステージング環境）のE2Eテスト自動化。Playwright + Python (pytest) を使用。

- **対象URL**: `https://invoicing-staging.keihi.com`
- **認証**: 環境変数 `TEST_EMAIL` / `TEST_PASSWORD`（.envはログインフォルダに配置）

## フォルダ構成

```
請求書/
└── 請求書一覧/
    ├── config.py                  # BASE_URL, 認証情報, Playwright設定
    ├── conftest.py                # pytest共通fixture（logged_in_page）
    ├── pytest.ini                 # testpaths=generated_tests
    ├── ANALYSIS_REPORT_INVOICES_1.md    # 一覧画面の詳細解析（※大きいので必要時のみ参照）
    ├── ANALYSIS_REPORT_INVOICE_DETAIL.md # 詳細画面+CSV自動化の詳細解析（※大きいので必要時のみ参照）
    ├── generated_tests/
    │   ├── test_invoice_list.py         # 一覧画面テスト（17テスト）
    │   └── test_invoice_detail.py       # 詳細画面テスト（15テスト）
    ├── 請求書作成/
    │   ├── CSVから新規作成/
    │   │   ├── test_invoice_creation.py  # CSVインポートテスト（5テスト）
    │   │   ├── run_csv_import.py         # 統合実行（CSV生成→インポート→確認）
    │   │   ├── generate_3000_csv.py      # 3000件CSV生成
    │   │   ├── import_3000.py            # CSVインポート実行
    │   │   └── write_memo_v2.py          # メモ記入
    │   └── PDFを取り込む/
    │       ├── conftest.py               # pytest共通fixture
    │       ├── test_pdf_organizer.py     # PDF取り込みテスト（27テスト）
    │       └── ANALYSIS_REPORT_PDF_ORGANIZER.md
    └── その他の操作/
        └── 共通添付ファイルの一括添付/
            ├── test_bulk_attachment_normal.py     # 正常系4テスト
            ├── test_bulk_attachment_error.py      # 異常系9テスト
            ├── test_bulk_attachment_filename.py   # ファイル名テスト
            ├── test_bulk_attachment_multi.py      # 複数請求書テスト
            ├── test_bulk_attachment_edge.py       # エッジケース
            ├── test_bulk_attachment_dom.py        # DOM検証
            ├── test_bulk_attachment_navigation.py # ナビゲーション
            ├── test_bulk_attachment_existing.py   # 既存タブテスト
            ├── ファイル名/     # テストデータ（14種のPDF）
            ├── 拡張子/         # テストデータ（13種+拡張子なし）
            └── ファイルサイズ/  # テストデータ（8パターン）
```

## テスト実行方法

```bash
# 一覧・詳細テスト（conftest.pyのlogged_in_pageを使用）
pytest generated_tests/ -v

# CSVインポートテスト（独自ログイン処理）
pytest 請求書作成/CSVから新規作成/test_invoice_creation.py -v

# PDF取り込みテスト
cd 請求書作成/PDFを取り込む && pytest test_pdf_organizer.py -v

# 共通添付ファイルテスト（独自スクリプト）
python その他の操作/共通添付ファイルの一括添付/test_bulk_attachment_normal.py
python その他の操作/共通添付ファイルの一括添付/test_bulk_attachment_error.py

# CSV一括インポート
python 請求書作成/CSVから新規作成/run_csv_import.py --count 3 --prefix TEST
```

## 画面構造（要約）

### 一覧画面 (/invoices)
- ヘッダー: ロゴ、ユーザー名、ヘルプ、事業所切替
- サイドバー: 請求書、取引先、帳票レイアウト
- 検索フォーム: 送付方法、取引先コード/名、請求書番号、日付範囲、ステータスCB等
- テーブル: 取引先/送付先/ステータス/承認状況/請求書番号/合計金額/請求日/支払期日/ファイル名
- 一括操作: 請求書を送付する、送付済みにする、その他の操作（一括添付/一括承認/一括削除）
- ページネーション: 表示件数（10/20/50/100）、前後ページ

### 詳細画面 (/invoices/{UUID})
- パンくず、ページ送り（前/次の請求書）、戻るボタン
- アクション: 送付済みにする、承認する、削除
- タブ: 帳票情報（デフォルト）/ 添付ファイル（?tab=attachment）
- 帳票情報タブ: 取引先情報、送付先情報、帳票項目、基本情報、メモフォーム
- 添付ファイルタブ: アップロード領域、一覧、使用状況（上限10件/10MB）

### CSVインポート画面 (/invoices/import)
- gallery iframe: レイアウト選択（MUI Grid）
- datatraveler iframe: CSVアップロード→マッピング→確認→プレビュー→作成

## 技術的制約・知見

### iframe操作（CSVインポート）
- datatraveler iframeは外部ドメイン (tpmlyr.dev.components.asaservice.inc)
- **`bounding_box()` + `page.mouse.click()` が最も確実**（標準クリックが効かない場合あり）
- 「帳票作成を開始する」後に確認ダイアログあり。**「作成開始」をクリックしないと作成されない**

### React管理フォーム操作（一覧画面の検索）
- `nativeInputValueSetter` でReactのstateを更新
- `form.requestSubmit()` でフォーム送信（`form.submit()`ではReactイベント未発火）

### Headless UI モーダル（一括添付等）
- `role="dialog"` のvisible判定が効かない → ダイアログ内 `h2` タイトルで `wait_for(state="visible")`
- ポインタインターセプト → `click(force=True)` で回避
- Step 2 非同期判定 → `expect().to_be_enabled(timeout=30000)` で待機

### 共通添付ファイルバリデーション仕様
- **Step 1（フロントエンド即時）**: 1ファイル10MB超、拡張子なし → エラー
- **Step 2（サーバー非同期）**: ファイル数11件以上、合計サイズ超過、既添付との累積超過 → エラー
- ファイル数上限: 10件、サイズ上限: 帳票オーバーヘッド込み10MB未満（実効~9.5MB）

### CSV仕様
- エンコーディング: cp932、19列、カンマ区切り
- **列11=備考、列12=取引日付（順序注意）**
- 3000件作成は約13分+BG処理5-6分

## 注意事項
- ANALYSIS_REPORT_*.md は大きい（27KB〜34KB）ので、特定セクションのロケーター情報が必要な場合のみ参照すること
- 共通添付ファイルの `.env` は4階層上の `ログイン/.env` を参照
- 一覧テーブルの行クリックは取引先名セル(nth(1))をクリック（nth(0)はチェックボックス）
- 「送付方法」ラベルは検索フォームと詳細画面で重複あり
- 「請求書」リンクはサイドバーとパンくずで重複あり → `.first` / `.last` で区別
