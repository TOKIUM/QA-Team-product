# 帳票レイアウト E2Eテストプロジェクト

## 作業ルール（必ず守ること）

### タスク分割ルール
- **1回の応答では1タスクだけ実行する**。複数タスクの指示を受けた場合、最初のタスクのみ実行し、完了後に「次のタスクに進みますか？」とユーザーに確認する。

### コンテキスト節約ルール
- ANALYSIS_REPORT_DESIGN.md は**必要なセクションだけ**を読む。全体を一度に読まない。
- テストファイルの内容確認が必要な場合、対象ファイルだけを読む。

## プロジェクト概要
TOKIUM 帳票レイアウト（ステージング環境）のE2Eテスト自動化。Playwright + Python (pytest) を使用。

- **対象URL**: `https://invoicing-staging.keihi.com/invoices/design`
- **認証**: 環境変数 `TEST_EMAIL` / `TEST_PASSWORD`（.envは `../ログイン/.env`）

## フォルダ構成

```
帳票レイアウト/
├── CLAUDE.md                      # 本ファイル
├── ANALYSIS_REPORT_DESIGN.md      # 画面解析レポート
├── conftest.py                    # pytest共通fixture（logged_in_page + .env読込）
├── pytest.ini                     # testpaths=.
└── test_design_list.py            # 帳票レイアウトテスト（20テスト）
```

## テスト実行方法

```bash
# 帳票レイアウトテスト（conftest.pyのlogged_in_pageを使用）
cd 帳票レイアウト
pytest test_design_list.py -v
```

## テスト一覧（20テスト、全PASS、約292秒）

| # | テスト名 | カテゴリ |
|---|---------|---------|
| 1 | test_帳票レイアウト画面に遷移できる | 画面遷移 |
| 2 | test_URL直接アクセスで画面表示 | 画面遷移 |
| 3 | test_パンくずが正しく表示される | 基本表示 |
| 4 | test_戻るボタンが表示される | 基本表示 |
| 5 | test_サイドバーの帳票レイアウトがアクティブ | 基本表示 |
| 6 | test_gallery_iframeが存在する | iframe |
| 7 | test_gallery_iframeのURLが正しい | iframe |
| 8 | test_レイアウトカードが表示される | iframe内容 |
| 9 | test_レイアウトカードの件数確認 | iframe内容 |
| 10 | test_検索バーが存在する | iframe内容 |
| 11 | test_新規作成ボタンが存在する | iframe内容 |
| 12 | test_並べ替えコントロールが存在する | iframe内容 |
| 13 | test_表示切替ボタンが存在する | iframe内容 |
| 14 | test_検索バーに入力できる | 検索機能 |
| 15 | test_検索で一致するレイアウトが表示される | 検索機能 |
| 16 | test_レイアウトカードクリックで遷移する | カード操作 |
| 17 | test_リスト表示に切り替えできる | 表示切替 |
| 18 | test_ヘッダーが表示される | ヘッダー |
| 19 | test_サイドバーから請求書画面に遷移できる | ナビゲーション |
| 20 | test_サイドバーから取引先画面に遷移できる | ナビゲーション |

## 画面構造（要約）

### 親ページ (/invoices/design)
- ヘッダー: ロゴ、ユーザー名、ヘルプ、事業所切替
- サイドバー: 請求書、取引先、帳票レイアウト（アクティブ）
- ユーティリティバー: 「戻る」ボタン（ブラウザバック動作）、パンくず（帳票レイアウト > レイアウト選択）
- **gallery iframe**: メインコンテンツ全体

### gallery iframe内（外部ドメイン: tpmlyr.dev.components.asaservice.inc）
- ツールバー: 検索バー、グリッド/リスト切替、並べ替え、新規作成ボタン
- レイアウトカード: MUI Grid（.MuiGrid-item）、5件確認済み

## 技術的制約・知見

### iframe操作（最重要）
- gallery iframe は外部ドメイン（`tpmlyr.dev.components.asaservice.inc`）
- **`page.frame(name="gallery")` でiframe取得**
- iframe内のDOM直接アクセス不可（親ページJSから）
- Chrome拡張（Claude in Chrome）の read_page/find/click は iframe内で動作しない
- **Playwright の `page.frame()` 経由のみで操作可能**

### iframe内の操作パターン
```python
# iframe取得 + ロード待機
gallery_frame = page.frame(name="gallery")
gallery_frame.wait_for_load_state("networkidle")
page.wait_for_timeout(3000)

# MUI Gridカード取得
grid_items = gallery_frame.query_selector_all(".MuiGrid-item")

# カードクリック（bounding_box + page.mouse.click が最確実）
box = grid_items[0].bounding_box()
page.mouse.click(box["x"] + box["width"]/2, box["y"] + box["height"]/2)

# 検索バー入力（bounding_box + keyboard.type）
search = gallery_frame.locator('input[placeholder*="検索"]')
box = search.bounding_box()
page.mouse.click(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
page.keyboard.type("検索文字")
```

### ロケーター重複問題
- 「帳票レイアウト」リンク: サイドバーとパンくずで重複 → `.first` / `#main-content nav` で区別
- 「請求書」リンク: ロゴ・ヘルプ・サイドバーで3つにマッチ → `exact=True` + `.first`
- 「池田尚人」テキスト: ヘッダーと事業所パネルで重複 → `.first`

### iframe読み込み待機
- `IFRAME_LOAD_WAIT = 8000` ms（初回ロード）
- `IFRAME_ACTION_WAIT = 3000` ms（操作後待機）
- `networkidle` 待機も併用

## 注意事項
- `.env` は `../ログイン/.env` を参照（conftest.pyの `_load_env()` で読み込み）
- 「戻る」ボタンはブラウザバック動作（帳票レイアウトトップに戻るわけではない）
- iframe内の検索は `fill()` が効かない場合あり → `bounding_box + mouse.click + keyboard.type` で対応
- テスト実行時間が長い（約5分）のはiframe読み込み待機のため
