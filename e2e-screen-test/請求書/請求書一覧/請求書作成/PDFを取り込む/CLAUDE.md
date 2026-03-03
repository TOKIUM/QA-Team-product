# PDFを取り込む E2Eテストプロジェクト

## 作業ルール（必ず守ること）

### タスク分割ルール
- **1回の応答では1タスクだけ実行する**。複数タスクの指示を受けた場合、最初のタスクのみ実行し、完了後に「次のタスクに進みますか？」とユーザーに確認する。

### コンテキスト節約ルール
- ANALYSIS_REPORT_PDF_ORGANIZER.md は**必要なセクションだけ**を読む。全体を一度に読まない。
- テストファイルの内容確認が必要な場合、対象ファイルだけを読む。

## プロジェクト概要
TOKIUM PDFを取り込む画面（ステージング環境）のE2Eテスト自動化。Playwright + Python (pytest) を使用。

- **対象URL**:
  - ファイル分割: `https://invoicing-staging.keihi.com/invoices/pdf-organizer/separation`
  - ファイルリネーム: `https://invoicing-staging.keihi.com/invoices/pdf-organizer/rename`
- **認証**: 環境変数 `TEST_EMAIL` / `TEST_PASSWORD`（.envは `../../../../ログイン/.env`）

## フォルダ構成

```
請求書/請求書一覧/請求書作成/PDFを取り込む/
├── CLAUDE.md                          # 本ファイル
├── ANALYSIS_REPORT_PDF_ORGANIZER.md   # 画面解析レポート
├── conftest.py                        # pytest共通fixture（logged_in_page + .env読込）
├── pytest.ini                         # testpaths=.
├── test_pdf_organizer.py              # PDFを取り込むテスト（27テスト）
└── debug_iframe.py                    # iframe調査用デバッグスクリプト
```

## テスト実行方法

```bash
# PDFを取り込むテスト（conftest.pyのlogged_in_pageを使用）
cd 請求書/請求書一覧/請求書作成/PDFを取り込む
pytest test_pdf_organizer.py -v
```

## テスト一覧（27テスト、全PASS、約364秒）

| # | テスト名 | カテゴリ |
|---|---------|---------|
| 1 | test_ファイル分割モードにURL直接アクセスできる | 分割モード基本表示 |
| 2 | test_pdf_organizerリダイレクト | 分割モード基本表示 |
| 3 | test_ファイル分割モードの見出し | 分割モード基本表示 |
| 4 | test_ファイル分割モードのパンくず | 分割モード基本表示 |
| 5 | test_ファイル分割モードのモード切替リンク | 分割モード基本表示 |
| 6 | test_ファイルリネームモードにURL直接アクセスできる | リネームモード基本表示 |
| 7 | test_ファイルリネームモードの見出し | リネームモード基本表示 |
| 8 | test_ファイルリネームモードのパンくず | リネームモード基本表示 |
| 9 | test_ファイルリネームモードのモード切替リンク | リネームモード基本表示 |
| 10 | test_分割モードからリネームモードに切替できる | モード切替 |
| 11 | test_リネームモードから分割モードに切替できる | モード切替 |
| 12 | test_パンくず請求書リンクで一覧画面に遷移 | パンくず遷移 |
| 13 | test_パンくずPDFを取り込むリンクで遷移 | パンくず遷移 |
| 14 | test_ヘッダーが表示される | ヘッダー |
| 15 | test_サイドバーが表示される | サイドバー |
| 16 | test_サイドバーから請求書画面に遷移できる | ナビゲーション |
| 17 | test_organizer_iframeが存在する_分割モード | iframe存在確認 |
| 18 | test_organizer_iframeが存在する_リネームモード | iframe存在確認 |
| 19 | test_organizer_iframeのsrcが正しい | iframe存在確認 |
| 20 | test_分割モードのステッパー表示 | iframe内（分割） |
| 21 | test_分割モードの案内テキスト | iframe内（分割） |
| 22 | test_分割モードのキャンセルボタン | iframe内（分割） |
| 23 | test_分割モードの次へボタン | iframe内（分割） |
| 24 | test_リネームモードのステッパー表示 | iframe内（リネーム） |
| 25 | test_リネームモードの案内テキスト | iframe内（リネーム） |
| 26 | test_リネームモードのキャンセルボタン | iframe内（リネーム） |
| 27 | test_リネームモードの次へボタン | iframe内（リネーム） |

## 画面構造（要約）

### 2つのモード
- **ファイル分割** (`/invoices/pdf-organizer/separation`): PDFを分割して取り込む（3ステップ）
- **ファイルリネーム** (`/invoices/pdf-organizer/rename`): PDFをリネームして取り込む（2ステップ）
- `/invoices/pdf-organizer` にアクセスすると `/separation` にリダイレクト

### 親ページ（共通）
- ヘッダー: ロゴ、ユーザー名、ヘルプ、事業所切替
- サイドバー: 請求書、取引先、帳票レイアウト
- パンくず: 請求書 > PDFを取り込む > ファイル分割 / ファイルリネーム
- モード切替リンク: 「ファイルリネームに切り替える」/「ファイル分割に切り替える」
- 見出し: 「PDFを分割して取り込む」/「PDFをリネームして取り込む」
- **organizer iframe**: メインコンテンツ全体

### organizer iframe内（外部ドメイン: tpmlyr.dev.components.asaservice.inc）
- ステッパー: 分割モード=3ステップ（ファイルアップロード→ファイルの分割→プレビュー）、リネームモード=2ステップ（ファイルアップロード→ファイル名の変換）
- 案内テキスト: 「アップロードするファイルを選択し...」
- ボタン: キャンセル、次へ（初期状態disabled）

## 技術的制約・知見

### iframe操作（最重要）
- organizer iframe は外部ドメイン（`tpmlyr.dev.components.asaservice.inc`）
- **`page.frame(name="organizer")` でiframe取得**
- ⚠️ `page.frame(url=lambda url: "organizer" in url)` は使わないこと — メインページURL（`/pdf-organizer/separation`）にもマッチして親ページを返す
- Chrome拡張（Claude in Chrome）の read_page/find/click は iframe内で動作しない
- **Playwright の `page.frame()` 経由のみで操作可能**

### iframe内の操作パターン
```python
# iframe取得 + ロード待機
organizer_frame = page.frame(name="organizer")
organizer_frame.wait_for_load_state("networkidle")
page.wait_for_timeout(3000)

# テキスト要素の検索
organizer_frame.locator("text=ファイルアップロード")

# ボタン検索（2パターン）
organizer_frame.locator('button:has-text("キャンセル")')
organizer_frame.get_by_role("button", name="次へ")
```

### iframe名についての注意
- **解析時**: Chrome DevToolsやアクセシビリティツリーではname属性が空に見える場合がある
- **Playwright実行時**: `page.frame(name="organizer")` で正常に取得可能
- 他画面のiframe比較:

| 画面 | iframe id | name | Playwright取得 |
|------|-----------|------|---------------|
| PDF取り込み | organizer | organizer | `frame(name="organizer")` |
| CSVインポート | gallery / datatraveler | gallery / datatraveler | `frame(name=...)` |
| 帳票レイアウト | gallery | gallery | `frame(name="gallery")` |

### ロケーター重複問題
- 「請求書」リンク: サイドバーとパンくずで重複 → `exact=True` + `.first`
- 「池田尚人」テキスト: ヘッダーと事業所パネルで重複 → `.first`

### iframe読み込み待機
- `IFRAME_LOAD_WAIT = 8000` ms（初回ロード）
- `IFRAME_ACTION_WAIT = 3000` ms（操作後待機）
- `networkidle` 待機も併用

## 注意事項
- `.env` は `../../../../ログイン/.env` を参照（conftest.pyの `_load_env()` で読み込み）
- Intercom iframe (`#intercom-frame`) も存在するが無視してよい
- テスト実行時間が長い（約6分）のはiframe読み込み待機のため
- 「次へ」ボタンはファイル未アップロード状態で `disabled` になる
