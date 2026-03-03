# ページ解析レポート: TOKIUM 請求書発行 - 請求書一覧画面

**URL**: https://invoicing-staging.keihi.com/invoices
**タイトル**: TOKIUM 請求書発行
**解析日**: 2026-02-16

---

## 1. ページ構成概要

```
┌──────────────────────────────────────────────────────┐
│ [banner] ヘッダー                                      │
│   ロゴ | ユーザー名 | ヘルプ | 事業所切替               │
├──────────┬───────────────────────────────────────────┤
│ [nav]    │ [main] メインコンテンツ                      │
│ サイドバー │                                           │
│          │  見出し「請求書」+ 新規作成ボタン群            │
│ ・請求書  │                                           │
│ ・取引先  │  検索条件フォーム                            │
│ ・帳票    │                                           │
│ レイアウト │  請求書テーブル（100件表示）                  │
│          │                                           │
│          │  ページネーション + 一括操作ボタン群           │
└──────────┴───────────────────────────────────────────┘
```

---

## 2. エリア別 要素一覧

### 2-1. ヘッダー（banner）

| 要素 | ロケーター | 推奨Playwright API |
|------|-----------|-------------------|
| ロゴ | image "TOKIUM 請求書発行" | `page.get_by_role("img", name="TOKIUM 請求書発行")` |
| ユーザー名表示 | text "池田尚人" | `page.get_by_text("池田尚人")` |
| ヘルプリンク | link "TOKIUM 請求書発行 - ヘルプセンター" | `page.get_by_role("link", name="TOKIUM 請求書発行 - ヘルプセンター")` |
| 事業所切替ボタン | button containing email | `page.get_by_text("ikeda_n+th1@tokium.jp")` |

### 2-2. サイドバー（navigation）

| 要素 | href | 推奨Playwright API |
|------|------|-------------------|
| 請求書 | /invoices | `page.get_by_role("link", name="請求書")` |
| 取引先 | /partners | `page.get_by_role("link", name="取引先")` |
| 帳票レイアウト | /invoices/design | `page.get_by_role("link", name="帳票レイアウト")` |

### 2-3. ページ見出し＆アクションボタン

| 要素 | 推奨Playwright API |
|------|-------------------|
| 見出し「請求書」 | `page.get_by_role("heading", name="請求書")` |
| CSVから新規作成 | `page.get_by_role("link", name="CSVから新規作成")` |
| PDFを取り込む | `page.get_by_role("link", name="PDFを取り込む")` |

### 2-4. 検索条件フォーム

#### テキスト入力フィールド

| フィールド | label | 推奨Playwright API |
|-----------|-------|-------------------|
| 送付方法 | label "送付方法" | `page.get_by_label("送付方法")` |
| 取引先コード | label "取引先コード" | `page.get_by_label("取引先コード")` |
| 取引先名 | label "取引先名" | `page.get_by_label("取引先名")` |
| 自社担当部署 | label "自社担当部署" | `page.get_by_label("自社担当部署")` |
| 自社担当者名 | label "自社担当者名" | `page.get_by_label("自社担当者名")` |
| 請求書番号 | label "請求書番号" | `page.get_by_label("請求書番号")` |
| 合計金額 | label "合計金額" | `page.get_by_label("合計金額")` |
| ファイル名 | label "ファイル名 （添付ファイル名）" | `page.get_by_label("ファイル名 （添付ファイル名）")` |
| メモ | placeholder "メモ" | `page.get_by_placeholder("メモ")` |

#### セレクトボックス（combobox）

| フィールド | 選択肢 | 推奨Playwright API |
|-----------|--------|-------------------|
| 送付方法 | 全て, メール, Web送付, 郵送代行, FAX送付, その他 | `page.get_by_label("送付方法")` |
| 承認状況 | 全て, 承認済み, 未承認 | `page.get_by_label("承認状況")` |
| Web送付 ダウンロード状況 | 全て, ダウンロード済み, 未ダウンロード | `page.get_by_label("Web送付 ダウンロード状況")` |

#### 日付フィールド

| フィールド | 推奨Playwright API |
|-----------|-------------------|
| 請求日（開始） | `page.get_by_label("請求日").locator('input[type="date"]').first` |
| 請求日（終了） | `page.get_by_label("請求日").locator('input[type="date"]').last` |
| 支払期日（開始） | `page.get_by_label("支払期日").locator('input[type="date"]').first` |
| 支払期日（終了） | `page.get_by_label("支払期日").locator('input[type="date"]').last` |

#### ステータスチェックボックス

| ステータス | value | 推奨Playwright API |
|-----------|-------|-------------------|
| 登録中 | processing | `page.get_by_label("登録中")` |
| 未送付 | available | `page.get_by_label("未送付")` |
| 送付中 | sending | `page.get_by_label("送付中")` |
| 送付済み | sent | `page.get_by_label("送付済み")` |
| 送付待ち | scheduled | `page.get_by_label("送付待ち")` |
| 登録失敗 | failed_to_process | `page.get_by_label("登録失敗")` |
| 送付失敗 | failed_to_send | `page.get_by_label("送付失敗")` |

#### 検索実行ボタン

| 要素 | 推奨Playwright API |
|------|-------------------|
| この条件で検索 | `page.get_by_role("button", name="この条件で検索")` |
| リセット | `page.get_by_role("button", name="リセット")` |
| 帳票エラーをチェック | `page.get_by_role("button", name="帳票エラーをチェック")` |
| 検索条件（開閉トグル） | `page.get_by_role("button", name="検索条件")` |

### 2-5. 請求書テーブル

#### テーブルヘッダーカラム

| カラム | 内容 |
|--------|------|
| チェックボックス | 全選択 |
| 取引先 | 取引先名 |
| 送付先 | 送付先コード |
| ステータス | 未送付 / 送付中 / 送付済み 等 |
| 承認状況 | 未承認 / 承認済み |
| 請求書番号 | 番号 |
| 合計金額 | 金額 |
| 請求日 | 日付 |
| 支払期日 | 日付 |
| ファイル名 | PDF名 |

#### テーブル行操作

| 操作 | 推奨Playwright API |
|------|-------------------|
| 行チェックボックス | `page.locator('table checkbox').nth(N)` |
| 特定取引先の行を選択 | `page.get_by_text("鈴木通信合同会社").first` |
| 請求書番号で行を特定 | `page.get_by_text("請求番号: 202601231807")` |

#### 検出されたデータ（一部）

| 取引先 | コード | ステータス | 承認 | 請求書番号 | ファイル名 |
|--------|--------|-----------|------|-----------|-----------|
| ひらがな | TH9002 | 未送付 | 未承認 | 202601231807 | 2.pdf |
| ﾊﾝｶｸｶﾀｶﾅ | TH9003 | 未送付 | 未承認 | 202601231808 | 3.pdf |
| 全角カタカナ | TH9004 | 未送付 | 未承認 | 202601231809 | 4.pdf |
| （名前なし） | TH9005 | 未送付 | 未承認 | 202601231810 | 5.pdf |
| 1234567890 | TH9006 | 未送付 | 未承認 | 202601231811 | 6.pdf |
| ＡＢＣＤＥＦＧ | TH9007 | 未送付 | 未承認 | 202601231813 | 8.pdf |
| abcdefg | TH9008 | 未送付 | 未承認 | 202601231814 | 9.pdf |
| !@#$%&()=~ | TH9009 | 未送付 | 未承認 | 202601231815 | 10.pdf |
| 未設定（×4件） | — | 未送付 | 未承認 | 202601231818〜 | 13〜15.pdf |
| 株式会社吉田電気 | TH2001 | 未送付 | 未承認 | — | 1.pdf |
| 鈴木通信合同会社 | TH003 | 未送付 | 未承認 | test1001〜 | TH003_鈴木通信合同会社_... |

### 2-6. ページネーション＆一括操作

| 要素 | 推奨Playwright API |
|------|-------------------|
| 件数表示 "8013件中 1〜100件" | `page.get_by_text("8013件中")` |
| 表示件数セレクト | `page.locator('combobox').filter(has_text="100")` ※10/20/50/100 |
| 前ページボタン | `page.locator('button').nth(-前ページ位置)` |
| 次ページボタン | `page.locator('button').nth(-次ページ位置)` |
| 請求書を送付する | `page.get_by_role("button", name="請求書を送付する")` |
| 送付済みにする | `page.get_by_role("button", name="送付済みにする")` |
| その他の操作 | `page.get_by_role("button", name="その他の操作")` |
| 選択解除 | `page.get_by_role("button", name="選択解除")` |

---

## 3. ロケーター品質評価

✅ **良好な点:**
- フォームの `<label>` が全フィールドに設定済み → `get_by_label()` が使える
- ボタンにテキスト名あり → `get_by_role("button", name=...)` が使える
- サイドバーのリンクにテキストあり → `get_by_role("link", name=...)` が使える

⚠️ **注意が必要な点:**
- テーブルの行に `data-testid` がない → 行特定にはテキストマッチングが必要
- ページネーションの前/次ボタンにテキストラベルがない（imgのみ）
- 日付フィールドが同じ placeholder "YYYY-MM-DD" で、`.first` / `.last` で区別が必要
- 「空白検索」チェックボックスの label が暗黙的（ネスト構造）

---

## 4. テスト可能な操作シナリオ

### A. 検索・フィルタリング
- 取引先名で検索 → テーブルに結果が表示される
- ステータスチェックボックスで絞り込み
- 送付方法セレクトで絞り込み
- 日付範囲で絞り込み
- リセットボタンで条件クリア

### B. テーブル操作
- 行クリックで請求書詳細に遷移
- チェックボックスで複数選択
- 全選択チェックボックス

### C. 一括操作
- 選択した請求書を送付
- 送付済みにする
- その他の操作メニュー

### D. ナビゲーション
- サイドバーから取引先/帳票レイアウト画面へ遷移
- CSVから新規作成/PDFを取り込むへ遷移
- ページネーションで次ページへ移動
- 表示件数の変更

---

## 5. 「その他の操作」メニュー詳細分析

**分析日**: 2026-02-17
**トリガー**: チェックボックスで1件以上選択 → 「その他の操作」ボタンクリック

### 5-1. メニュー構造

| 属性 | 値 |
|------|------|
| フレームワーク | Headless UI |
| コンテナ | `div[role="menu"]` class=`_menuItems_11t25_1` |
| メニュー項目 | `div[role="menuitem"]` class=`_menuItemPopover_11t25_20` |

### 5-2. メニュー項目一覧

| # | メニュー項目 | DOM構造 | Playwright操作 |
|---|-------------|---------|---------------|
| 1 | 共通添付ファイルの一括添付 | `div[role="menuitem"]` > `span._trigger` > `button` | `page.locator('[role="menuitem"]').filter(has_text="共通添付ファイルの一括添付").click()` |
| 2 | 一括承認 | 同上 | `page.locator('[role="menuitem"]').filter(has_text="一括承認").click()` |
| 3 | 一括削除 | 同上 | `page.locator('[role="menuitem"]').filter(has_text="一括削除").click()` |

### 5-3. メニュー項目のネスト構造

```
div[role="menu"]._menuItems_11t25_1
  ├── div[role="menuitem"]._menuItemPopover_11t25_20
  │     └── span._trigger_ohszv_1 (aria-expanded)
  │           └── button._button_1e3w6_1  ← 実際のクリック対象
  │                 ├── svg (アイコン: fa-paperclip)
  │                 └── "共通添付ファイルの一括添付"
  ├── div[role="menuitem"]._menuItemPopover_11t25_20
  │     └── span._trigger_ohszv_1
  │           └── button._button_1e3w6_1
  │                 ├── svg (アイコン: fa-circle, text-primary)
  │                 └── "一括承認"
  └── div[role="menuitem"]._menuItemPopover_11t25_20
        └── span._trigger_ohszv_1
              └── button._button_1e3w6_1
                    ├── svg (アイコン: fa-trash-can, text-danger)
                    └── "一括削除"
```

---

## 6. 「共通添付ファイルの一括添付」モーダル詳細分析

**分析日**: 2026-02-17
**トリガー**: 「その他の操作」→「共通添付ファイルの一括添付」クリック
**スクリーンショット**: `bulk_attach_step2_modal.png`

### 6-1. モーダル全体構造

| 属性 | 値 |
|------|------|
| フレームワーク | Headless UI |
| ルート | `div[role="dialog"]` id=`headlessui-dialog-:r3b:` class=`_dialog_1er8r_1` |
| パネル | `div._dialogPanel_1er8r_44` |
| コンテナ | `article._bigCard_vnnpk_1._modal_1du64_1` |
| iframe | なし（純粋なDOMモーダル） |

### 6-2. ステップウィザード

```
[1 ファイル選択] ──── [2 確認] ──── [3 完了]
     ↑ Active
```

| Step | ラベル | CSS状態クラス |
|------|--------|-------------|
| 1 | ファイル選択 | `_stepActive_s8cyc_6` (現在のステップ) |
| 2 | 確認 | `_step_s8cyc_2` |
| 3 | 完了 | `_step_s8cyc_2` |

### 6-3. Step 1: ファイル選択画面

#### タブ切替

| タブ名 | アイコン | 状態 | Playwright操作 |
|--------|---------|------|---------------|
| 新規アップロード | fa-cloud-arrow-up | **Active** (`_tabButtonActive_7ra6u_62`) | — |
| 既存から選択 | fa-magnifying-glass | 非選択 | `page.get_by_role("button", name="既存から選択").click()` |

#### 左ペイン: ファイルアップロード

| 要素 | 種類 | 詳細 | Playwright操作 |
|------|------|------|---------------|
| 見出し | `<h3>` | 「ファイルをアップロードして選択」 | — |
| ドロップゾーン | `div._dropZone_1yvt8_2` | D&D対応エリア | — |
| 案内テキスト | `<p>` | 「ファイルをドラッグ＆ドロップ、または」 | — |
| ファイル選択ボタン | `<button>` | 「ファイルを選択」 | `page.get_by_role("button", name="ファイルを選択").click()` |
| 隠しファイルinput | `input[type="file"]` | **multiple=true**, accept制限なし, class=`_hiddenInput_1yvt8_35` | `page.locator('input[type="file"]').set_input_files([...])` |

#### 右ペイン: 選択済みファイル一覧

| 要素 | 種類 | 詳細 |
|------|------|------|
| 見出し | `<h3>` | 「選択済みファイル（0件）」 |
| 空メッセージ | `<p>._emptyMessage_11ukp_13` | 「ファイルが選択されていません」 |

#### フッター

| ボタン | 状態 | 位置 | Playwright操作 |
|--------|------|------|---------------|
| 閉じる | enabled | 左側 | `page.get_by_role("button", name="閉じる").click()` |
| 確認へ進む | **disabled**（ファイル未選択時） | 右側 | `page.get_by_role("button", name="確認へ進む").click()` |
| ×ボタン | enabled | 右上 | `page.locator('button._closeButton_vnnpk_31').click()` |

#### バリデーション

| 条件 | 動作 |
|------|------|
| ファイル未選択 | 「確認へ進む」disabled + 「ファイルを選択してください」表示 |
| ファイル選択済み | 「確認へ進む」enabled（想定） |

### 6-4. DOM構造ツリー

```
div[role="dialog"]._dialog_1er8r_1  (id=headlessui-dialog-:r3b:)
  ├── div._dialogBackdrop_1er8r_6  (背景オーバーレイ)
  └── div._dialogScroller_1er8r_17
        └── div._dialogVerticalAlign_1er8r_38
              └── div._dialogPanel_1er8r_44  (id=headlessui-dialog-panel-:r3i:)
                    └── article._bigCard_vnnpk_1._modal_1du64_1
                          ├── header._header_vnnpk_16
                          │     ├── h2  "共通添付ファイルの一括添付"
                          │     └── button._closeButton_vnnpk_31  (×ボタン)
                          ├── nav (ステップウィザード: 1→2→3)
                          │     ├── div > span._stepNumber "1" + span._stepLabel "ファイル選択"
                          │     ├── div._connector + span "2" + "確認"
                          │     └── div._connector + span "3" + "完了"
                          ├── nav._tabs_7ra6u_1 (タブ切替)
                          │     ├── button._tabButtonActive "新規アップロード"
                          │     └── button._tabButton "既存から選択"
                          ├── section._body_10aan_1 (コンテンツ)
                          │     └── div._container_yrdrf_1
                          │           ├── div._leftPane (アップロード)
                          │           │     ├── h3 "ファイルをアップロードして選択"
                          │           │     ├── div._dropZone_1yvt8_2
                          │           │     │     ├── svg (クラウドアイコン)
                          │           │     │     ├── p "ファイルをドラッグ＆ドロップ、または"
                          │           │     │     ├── button "ファイルを選択"
                          │           │     │     └── input[type="file"]._hiddenInput (hidden, multiple)
                          │           │     └── (矢印 ">" アイコン)
                          │           └── div._rightPane (選択済み)
                          │                 ├── h3 "選択済みファイル（0件）"
                          │                 └── p._emptyMessage "ファイルが選択されていません"
                          └── div (フッター)
                                ├── button "閉じる"
                                ├── p "ファイルを選択してください"
                                └── button "確認へ進む" (disabled)
```

### 6-5. テスト操作フロー（Playwright）

```python
# Step 1: メニュー経由でモーダルを開く
page.get_by_role("button", name="その他の操作").click()
page.locator('[role="menuitem"]').filter(has_text="共通添付ファイルの一括添付").click()
page.locator('[role="dialog"]').wait_for(state="visible")

# Step 2: ファイルをアップロード
page.locator('input[type="file"]').set_input_files(["test_file.pdf"])

# Step 3: 確認へ進む
page.get_by_role("button", name="確認へ進む").click()

# Step 4: モーダルを閉じる
page.get_by_role("button", name="閉じる").click()
```

---

## 7. 「共通添付ファイルの一括添付」正常系テスト結果

**実行日**: 2026-02-17 11:03:59 ～ 11:05:49 (約1分50秒)
**スクリプト**: `請求書作成/共通添付ファイル/test_bulk_attachment_normal.py`
**結果**: **全4テスト PASS** ✓

### 7-1. テスト結果サマリー

| TC-ID | テスト名 | ファイル数 | 使用請求書 | 結果 |
|-------|---------|-----------|-----------|------|
| TC-01 | PDF 1ファイルアップロード | 1件 (sample.pdf) | index=0 | **PASS** ✓ |
| TC-02 | 複数ファイル同時アップロード | 3件 (pdf, png, jpg) | index=1 | **PASS** ✓ |
| TC-03 | 各種拡張子ファイル | 4件 (jpg, png, xlsx, docx) | index=2 | **PASS** ✓ |
| TC-04 | 日本語ファイル名 | 3件 (ひらがな.pdf, 全角カタカナ.pdf, 漢字.pdf) | index=3 | **PASS** ✓ |

### 7-2. テストフロー（3ステップウィザード）

各テストケースで以下の全ステップを自動検証:

```
Step 1: ファイル選択
  ├─ input[type="file"].set_input_files() でファイル設定
  ├─ 「選択済みファイル(N件)」表示を確認
  └─ 「確認へ進む」ボタン enabled を確認

Step 2: 確認画面（非同期判定）
  ├─ 2-a: 「添付可否を判定中...」表示（「添付を実行する」disabled）
  ├─ 2-b: 判定完了後（約2秒）→「添付を実行する」enabled
  ├─ 検証項目:
  │   ├─ 「添付するファイル(N件)」セクション + ファイル名チップ
  │   ├─ 「添付先の帳票一覧」テーブル（取引先/送付方法/請求書番号/金額/判定）
  │   ├─ 判定結果: 「添付可能」
  │   └─ ステータス: 「添付を実行可能です」
  └─ 「添付を実行する」クリック → 添付処理実行

Step 3: 完了画面
  ├─ 「添付が完了しました」表示確認
  ├─ 「共通添付ファイルが N 件の請求書に添付されました」表示確認
  └─ 「閉じる」ボタンでモーダル終了

一覧画面復帰後:
  └─ テーブル行の添付件数が増加していることをログ出力で記録
```

### 7-3. 確認された仕様

| 項目 | 詳細 |
|------|------|
| Step 2 非同期判定 | 「添付可否を判定中...」→ 約2秒で完了、ボタンがenabledに |
| Step 2 テーブル表示 | ヘッダー: 取引先 / 送付方法 / 請求書番号 / 金額 / 判定 |
| Step 2 判定結果 | 添付可能 → 「添付を実行可能です」、上限超過 → 「添付数上限を超過しています」 |
| 完了メッセージ | 「添付が完了しました」+「共通添付ファイルが N 件の請求書に添付されました」 |
| 添付数上限 | 同一請求書に繰り返し添付すると「添付数上限を超過しています」エラー |
| accept制限 | input[type="file"]に accept 属性なし → 全ファイル形式受付 |
| multiple属性 | input[type="file"]に multiple=true → 複数ファイル同時選択可 |
| 日本語ファイル名 | ひらがな/全角カタカナ/漢字 すべて正常に添付完了 |

### 7-4. テスト実装上の知見

| 課題 | 対応方法 |
|------|---------|
| `role="dialog"` が visible 判定されない | Headless UI の dialog ラッパーは height=0 → ダイアログ内の `h2` タイトルで `wait_for(state="visible")` |
| Step 2 の「添付を実行する」が disabled | 非同期判定処理中 → `expect().to_be_enabled(timeout=30000)` で待機 |
| ポインタインターセプト | `headlessui-portal-root` が click をブロック → `click(force=True)` で回避 |
| 添付数上限エラー | テストケース間で異なる請求書を選択 (`select_invoice(page, index=N)`) |
| チェックボックスクリック | `checkboxes[N].click(force=True)` でインターセプト回避 |
| .env パス解決 | `共通添付ファイル/` は3階層深い → `os.path.join(SCRIPT_DIR, "..", "..", "..", "ログイン画面", ".env")` |

### 7-5. テスト用ファイル構成

```
請求書作成/共通添付ファイル/
├── test_bulk_attachment_normal.py    ← 正常系テストスクリプト
├── analyze_step2_step3_flow.py      ← Step 2→3 画面遷移分析スクリプト
├── test_results/                    ← テスト結果出力先
│   ├── test_normal_YYYYMMDD_HHMMSS.log   (実行ログ)
│   ├── test_normal_YYYYMMDD_HHMMSS.json  (JSON結果)
│   ├── flow_step*.png               (画面遷移分析スクリーンショット)
│   └── tc0N_step*.png               (各TCの各ステップスクリーンショット)
├── ファイル名/                      ← ファイル名テスト用 (14ファイル)
│   ├── ひらがな.pdf, 全角カタカナ.pdf, 漢字.pdf
│   ├── abcdefg.pdf, 1234567890.pdf, ＡＢＣＤＥＦＧ.pdf, ﾊﾝｶｸｶﾀｶﾅ.pdf
│   ├── １２３４５６７８９０.pdf
│   ├── !@#$%&()=~.pdf, %5Ct%5Cn%5Cr%5C0.pdf
│   ├── 200文字超ファイル名.pdf, 251文字(NTFS上限)ファイル名.pdf, 256文字(A連続).pdf
│   └── create_pdfs.py, create_longest_pdf.py (生成スクリプト)
├── 拡張子/                          ← 拡張子テスト用 (13ファイル+拡張子なし)
│   ├── sample.{jpg,jpeg,png,pdf,xlsx,xls,csv,txt,doc,docx,gif,pptx}
│   ├── _ (拡張子なし)
│   └── create_various_files.py (生成スクリプト)
└── ファイルサイズ/                   ← サイズテスト用 (8パターン)
    ├── 01_single_10MB_under/ (9.9MB)    ← 1ファイル上限以内
    ├── 02_single_10MB_over/  (10.1MB)   ← 1ファイル上限超過
    ├── 03_10files_upload/    (10ファイル) ← ファイル数上限
    ├── 04_11files_upload/    (11ファイル) ← ファイル数上限超過
    ├── 05_total_10MB_under/  (合計9.5MB) ← 合計サイズ上限以内
    ├── 06_total_10MB_over/   (合計10.5MB)← 合計サイズ上限超過
    ├── 07_single_5MB/        (5.0MB)     ← 中間サイズ
    ├── 08_single_5MB_over_10MB_under/ (5.1MB) ← 中間サイズ
    └── create_size_pdfs.py (生成スクリプト)
```

### 7-6. テスト結果ファイル一覧

| ファイル | 内容 |
|---------|------|
| `test_normal_20260217_110359.log` | **最新**正常系テスト実行ログ（4件全PASS） |
| `test_normal_20260217_110359.json` | 最新テスト結果JSON |
| `test_normal_20260217_103542.log` | 初回PASS時の実行ログ（参考保存） |
| `test_normal_20260217_103542.json` | 初回PASS時の結果JSON |
| `flow_step1.png` | 画面遷移分析: Step 1 ファイル選択 |
| `flow_step2a_judging.png` | 画面遷移分析: Step 2 判定中 |
| `flow_step2b_ready.png` | 画面遷移分析: Step 2 判定完了 |
| `flow_step3.png` | 画面遷移分析: Step 3 完了 |
| `tc0N_step1.png` | 各TC: ファイル選択後 |
| `tc0N_step2.png` | 各TC: 確認画面（判定中） |
| `tc0N_step2_ready.png` | 各TC: 確認画面（判定完了） |
| `tc0N_step3.png` | 各TC: 完了画面 |
| `tc0N_after_close.png` | 各TC: モーダル閉じた後の一覧画面 |

---

## 8. 「共通添付ファイルの一括添付」異常系・境界値テスト結果

**実行日**: 2026-02-17 11:53:53 ～ 11:56:15 (約2分22秒)
**スクリプト**: `請求書作成/共通添付ファイル/test_bulk_attachment_error.py`
**結果**: **全9テスト PASS** ✓

### 8-1. テスト結果サマリー

| TC-ID | テスト名 | カテゴリ | 検証ステップ | 結果 |
|-------|---------|---------|------------|------|
| TC-E01 | ファイルサイズ超過 (10.1MB) | 異常系 | Step 1 エラー | **PASS** ✓ |
| TC-E04 | 拡張子なしファイル | 異常系 | Step 1 エラー | **PASS** ✓ |
| TC-E02 | 11ファイル同時選択 (ファイル数超過) | 異常系 | Step 2 エラー | **PASS** ✓ |
| TC-E03 | 合計サイズ超過 (5ファイル 10.5MB) | 異常系 | Step 2 エラー | **PASS** ✓ |
| TC-E05 | 9.9MB 1ファイル (ファイルサイズ超過) | 異常系 | Step 2 エラー | **PASS** ✓ |
| TC-E06 | 10ファイル同時 (境界値 OK) | 境界値 | Step 2 正常 | **PASS** ✓ |
| TC-E07 | 合計9.5MB (5ファイル) (境界値 OK) | 境界値 | Step 2 正常 | **PASS** ✓ |
| TC-E08 | 特殊記号ファイル名 (!@#$%&()=~.pdf) | 境界値 | Step 2 正常 | **PASS** ✓ |
| TC-E09 | 5.0MB 1ファイル (境界値 OK) | 境界値 | Step 2 正常 | **PASS** ✓ |

### 8-2. エラーバリデーション仕様（分析確定）

共通添付ファイルの一括添付には **2段階のバリデーション** が存在する：

#### Step 1 エラー（フロントエンド即時バリデーション）

ファイルセット直後にブラウザ側で即座に判定。以下の条件でブロック：

| 条件 | 検出方法 | エラー表示 |
|------|---------|-----------|
| 1ファイル10MB超過 (10.1MB = 10,590,617 bytes) | 即時 | ファイル横に「エラー」、「選択済みファイル(0件)」 |
| 拡張子なしファイル | 即時 | ファイル横に「エラー」、「選択済みファイル(0件)」 |

- **フッター**: 「選択済みファイルにエラーがあります。選択から削除してください」
- **「確認へ進む」ボタン**: disabled
- **CSSクラス**: `text-error`

#### Step 2 エラー（サーバー側非同期バリデーション）

「確認へ進む」クリック後、サーバー側で非同期判定。以下の条件でブロック：

| 条件 | エラーメッセージ（判定列） |
|------|------------------------|
| ファイル数11件以上 | 「添付数上限を超過しています」 |
| 合計サイズ超過 (10.5MB / 9.9MB) | 「ファイルサイズ上限を超過しています」 |
| 既添付ファイルとの合計で上限超過 | 「添付数上限を超過しています」 |

- **h4見出し**: 「添付先の帳票一覧」→「添付先の帳票一覧**エラー**」に変化
- **フッター**: 「エラーがあります。ファイルを再選択してください」
- **「添付を実行する」ボタン**: disabled

### 8-3. ファイルサイズ上限の詳細分析

サーバー側の判定は `(ファイルサイズ + 帳票オーバーヘッド約30〜33KB) / 1,048,576` を基に計算。

| テストデータ | 実バイト数 | 帳票込み概算 | 判定結果 |
|-------------|-----------|------------|---------|
| file_5.0MB.pdf | 5,211,130 bytes (4.97MB) | ~5.00MB | ✓ **添付可能** |
| file_5.1MB.pdf | 5,347,737 bytes (5.10MB) | ~5.13MB | ✓ **添付可能** |
| 合計9.5MB (5×1.9MB) | 9,961,470 bytes | ~9.53MB | ✓ **添付可能** |
| file_9.9MB.pdf | 10,380,902 bytes (9.90MB) | ~9.93MB | ✗ **サイズ上限超過** |
| 合計10.5MB (5×2.1MB) | 11,010,045 bytes | ~10.53MB | ✗ **サイズ上限超過** |
| file_10.1MB.pdf | 10,590,617 bytes (10.10MB) | — | ✗ **フロントでブロック** |

**ファイル数上限**: 10件（フロント側は10件までしかセットできない。11件指定→10件のみ受付）
**サイズ上限**: 帳票オーバーヘッド込みで合計10MB未満（9.9MB単体がNGのため、実効上限は~9.5MB程度）

### 8-4. テスト実装上の知見（異常系固有）

| 課題 | 対応方法 |
|------|---------|
| 既添付の請求書を使うと累積で「添付数上限」エラー | 正常系テスト(TC-01～04)で使ったindex 0-4を避け、index 5-9を使用 |
| Step 1 エラー系は既添付でも影響なし | Step 2に進まないため、同じindexを再利用可能 |
| モーダルオープン失敗 (間欠的) | 3回リトライ + Escapeキーでメニュー閉じ |
| 11ファイル指定→10件のみ受付 | フロント側で10件に制限される仕様。Step 2で「添付数上限を超過」 |
| Step 2 非同期判定待機 | エラー検出 or ボタンenabled を最大30秒ポーリング |

### 8-5. テスト結果ファイル一覧

| ファイル | 内容 |
|---------|------|
| `test_error_20260217_115353.log` | **最新**異常系テスト実行ログ（9件全PASS） |
| `test_error_20260217_115353.json` | 最新テスト結果JSON |
| `tc-e0N_step1.png` | 各TC: ファイル選択後 |
| `tc-e0N_step2_initial.png` | 各TC: 確認画面（判定中） |
| `tc-e0N_step2_final.png` | 各TC: 確認画面（判定完了） |

---

## 9. 今後のテスト計画（未実施）

### 9-1. 操作系テスト

| テスト観点 | 内容 |
|-----------|------|
| 「戻る」ボタン | Step 2 → Step 1 への戻り操作 |
| ×ボタン閉じる | 各ステップでの途中キャンセル |
| 複数請求書一括 | 2件以上の請求書を選択して一括添付 |
| 「既存から選択」タブ | 既アップロード済みファイルの選択 |

### 9-2. 追加ファイル名・拡張子テスト（要確認）

| テスト観点 | テストデータ | 状態 |
|-----------|------------|------|
| 最長ファイル名(200文字超) | `ファイル名/123...pdf` | 未実施 |
| NTFS上限(251文字) | `ファイル名/123...pdf` | 未実施 |
| 非対応拡張子 (.gif, .pptx等) | `拡張子/sample.gif, sample.pptx` | 未実施 |

---

## 10. 分析用スクリプト一覧

| スクリプト | 用途 | 出力先 |
|-----------|------|--------|
| `analyze_other_operations_modal.py` | 「その他の操作」メニューDOM分析 | `analyze_modal_result.txt` |
| `analyze_bulk_attachment_modal.py` | 一括添付モーダルDOM分析 | `analyze_bulk_attachment_result.txt` |
| `請求書作成/共通添付ファイル/analyze_step2_step3_flow.py` | Step 2→3 画面遷移分析 | `test_results/flow_step*.png` |
| `請求書作成/共通添付ファイル/test_bulk_attachment_normal.py` | 正常系E2Eテスト（4件） | `test_results/` |
| `請求書作成/共通添付ファイル/test_bulk_attachment_error.py` | 異常系・境界値テスト（9件） | `test_results/` |
| `請求書作成/共通添付ファイル/analyze_error_behavior.py` | エラー動作分析（5ケース） | `test_results/` |
| `請求書作成/共通添付ファイル/analyze_error_case1_retry.py` | 10.1MBケース再分析 | `test_results/` |
| `請求書作成/共通添付ファイル/analyze_error_case2_3_retry.py` | ケース2/3再分析（未使用請求書） | `test_results/` |
| `請求書作成/共通添付ファイル/analyze_size_boundary.py` | ファイルサイズ境界値分析 | `test_results/` |

### 分析時スクリーンショット

| ファイル | 内容 |
|---------|------|
| `modal_step1_checked.png` | チェックボックス選択後の一覧画面 |
| `modal_step2_modal_open.png` | 「その他の操作」メニュー表示 |
| `modal_step3_analysis.png` | メニュー分析完了時 |
| `bulk_attach_step1_menu.png` | 「その他の操作」メニュー |
| `bulk_attach_step2_modal.png` | 一括添付モーダル表示 |
| `bulk_attach_step3_analysis.png` | モーダル分析完了時 |
