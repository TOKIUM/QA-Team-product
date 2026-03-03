# ページ解析レポート: TOKIUM 請求書発行 - 請求書詳細画面 & 請求書作成自動化

**URL**: https://invoicing-staging.keihi.com/invoices/{UUID}
**タイトル**: TOKIUM 請求書発行
**解析日**: 2026-02-16
**最終更新**: 2026-02-17（統合スクリプト作成・debugファイル削除完了）
**タブ切替**: `?tab=attachment` で添付ファイルタブに切替

---

# Part A: 請求書作成（CSVインポート）自動化 整理

## A-1. 自動化フロー全体像

```
[1. CSV生成]  →  [2. CSVインポート]  →  [3. 作成結果確認]  →  [4. メモ記入]
generate_        import_3000.py        check_3000_          write_memo_
3000_csv.py                            status.py             v2.py

★ 統合実行: run_csv_import.py（STEP1〜3を一括実行、パラメータ対応）
```

### 処理フロー詳細（import_3000.py の7ステップ）

```
STEP1: ログイン
  └→ /login → メールアドレス/パスワード入力 → /invoices

STEP2: レイアウト選択
  └→ /invoices/import → gallery iframe → .MuiGrid-item[0]クリック
  └→ /invoices/import/{layout_id} へ遷移

STEP3: CSVアップロード
  └→ datatraveler iframe → input[type="file"] でCSVセット
  └→ 「項目のマッピングへ」クリック → 自動マッピング
  ※ CSVヘッダーがレイアウト設定と一致していれば自動マッピング

STEP4: データの確認
  └→ 「データの確認へ」クリック → 問題なし/エラー件数表示
  ※ bounding_box() + page.mouse.click() でiframe内ボタン操作

STEP5: 帳票プレビュー
  └→ 「帳票プレビューへ」クリック → プレビュー表示
  └→ 「帳票作成を開始する」ボタン表示

STEP6: 帳票作成開始 ★重要
  └→ 「帳票作成を開始する」クリック → 確認ダイアログ表示
  └→ 「作成開始」ボタンクリック ★★これがないと作成されない★★
  └→ サーバー側バックグラウンド処理開始

STEP7: 一覧確認
  └→ /invoices で requestSubmit() 検索 → 件数確認
```

---

## A-2. 最終版スクリプト一覧

`請求書画面\請求書作成\` 配下

### 本番用スクリプト

| ファイル | 用途 | 実行方法 | 確認結果 |
|---|---|---|---|
| `run_csv_import.py` | **統合実行（CSV生成→インポート→結果確認）** | `python run_csv_import.py --count 100 --prefix TEST100` | OK（3件テスト成功） |
| `generate_3000_csv.py` | CSV生成（単独） | `python generate_3000_csv.py` | OK |
| `import_3000.py` | CSVインポート（単独） | `python import_3000.py` | OK（3000件作成） |
| `import_and_verify_v2.py` | 少量CSV(3件)インポート+確認 | `python import_and_verify_v2.py` | OK（3件作成） |
| `write_memo_v2.py` | 検索→各請求書にメモ記入 | `python write_memo_v2.py` | OK（3件メモ保存） |
| `check_3000_status.py` | 作成結果ポーリング確認（単独） | `python check_3000_status.py` | OK（3000件確認） |
| `test_invoice_creation.py` | pytest形式テスト(5テスト) | `pytest test_invoice_creation.py` | 5テスト全PASS |

### 統合スクリプト `run_csv_import.py` の使い方

```bash
# デフォルト: 3000件, AUTO3K
python run_csv_import.py

# 件数・プレフィックスを指定
python run_csv_import.py --count 100 --prefix TEST100

# 日付・備考もカスタマイズ
python run_csv_import.py --count 50 --prefix DEMO --date 2025/03/01 --due 2025/04/30 --remark テスト用

# ステップ個別スキップ
python run_csv_import.py --skip-generate      # CSV生成をスキップ（既存CSV使用）
python run_csv_import.py --skip-import         # 結果確認のみ
python run_csv_import.py --skip-check          # 結果確認なし

# ブラウザ表示モード
python run_csv_import.py --headed --count 3

# ポーリング設定
python run_csv_import.py --max-check 20 --check-interval 60
```

### 補助ファイル

| ファイル | 用途 |
|---|---|
| `auto3k_invoices.csv` | 生成済み3000件CSV（cp932） |
| `test_verify2.csv` | 少量テスト用CSV（3件） |
| `*_result.txt` | 各スクリプトの実行結果ログ |
| `3k_*.png` | 3000件インポート時のスクリーンショット |

### デバッグファイル

削除済み（2026-02-17）: debug_*.py x19, verify_created_invoices*.py x7, 旧バージョンファイル x3, 関連出力ファイル多数

---

## A-3. 自動化の完成度評価

### 各処理の自動化状況

| 処理 | 単独実行 | パラメータ化 | エラーハンドリング | 備考 |
|---|---|---|---|---|
| CSV生成 | OK | **統合スクリプトで対応済み** | 最低限 | --count, --prefix等 |
| CSVインポート | OK | **統合スクリプトで対応済み** | ステップごとの確認あり | 3000件で約13分 |
| 結果確認 | OK | **統合スクリプトで対応済み** | ポーリングリトライあり | --max-check, --check-interval |
| メモ記入 | OK | 検索キー VERIFY2 固定 | UUID取得→各件処理 | 3000件には未対応 |

### 統合実行

```bash
# 一括実行（推奨）
python run_csv_import.py --count 3000 --prefix AUTO3K

# 個別実行も可能
python generate_3000_csv.py
python import_3000.py          # 約13分
python check_3000_status.py    # 約5.5分（ポーリング）
```

### 課題一覧（残存）

| # | 課題 | 影響度 | 備考 |
|---|---|---|---|
| 1 | ~~統合実行スクリプトがない~~ | ~~中~~ | **解決済み: run_csv_import.py** |
| 2 | ~~パラメータがハードコード~~ | ~~中~~ | **解決済み: argparseで対応** |
| 3 | write_memo_v2.pyがVERIFY2固定 | 低 | 3000件はCSV備考欄に「自動生成」入力済みで不要 |
| 4 | ~~debugファイルが15個以上残存~~ | ~~低~~ | **解決済み: 全削除完了** |
| 5 | pytest形式と独立スクリプト混在 | 低 | conftest.py活用は一覧/詳細テストのみ |

---

## A-4. 技術的な知見（CSVインポート固有）

### iframe操作の攻略法

CSVインポート画面は2つのiframeで構成されている：

```
メインページ (/invoices/import/{layout_id})
├── gallery iframe  — レイアウト選択画面（MUI Grid）
└── datatraveler iframe — CSVアップロード〜作成操作
    ※ 外部ドメイン: tpmlyr.dev.components.asaservice.inc
```

**最も有効な操作手法:**
```python
# iframe内のボタンはPlaywright標準クリックが効かない場合あり
# bounding_box() + page.mouse.click() が最も確実

btn = dt.query_selector('button:has-text("データの確認へ")')
box = btn.bounding_box()
page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
```

- `bounding_box()` はiframeオフセット含むページ絶対座標を返す
- ブラウザレベルのマウスイベントはiframe境界を通過しReactに到達

### 確認ダイアログの存在 ★最重要発見

「帳票作成を開始する」クリック後に確認ダイアログが表示される。
**「作成開始」をクリックしないと帳票は作成されない。**

```python
# 「帳票作成を開始する」→ 確認ダイアログ表示
create_btn = dt.query_selector('button:has-text("帳票作成を開始する")')
crbox = create_btn.bounding_box()
page.mouse.click(crbox['x'] + crbox['width']/2, crbox['y'] + crbox['height']/2)
page.wait_for_timeout(3000)

# 確認ダイアログ内の「作成開始」ボタンをクリック
start_btn = dt.query_selector('button:has-text("作成開始")')
sbox = start_btn.bounding_box()
page.mouse.click(sbox['x'] + sbox['width']/2, sbox['y'] + sbox['height']/2)
```

### CSV仕様

| 項目 | 値 |
|---|---|
| エンコーディング | cp932（Shift_JIS系） |
| 列数 | 19列 |
| 区切り | カンマ |
| 改行 | LF |

**列定義（0始まり）:**

```
[0]  請求書番号    [1]  請求日        [2]  期日
[3]  取引先コード  [4]  取引先名称    [5]  取引先敬称
[6]  取引先郵便番号 [7]  取引先都道府県 [8]  取引先住所１
[9]  取引先住所２  [10] 当月請求額    [11] 備考 ★
[12] 取引日付     [13] 内容         [14] 数量
[15] 単価        [16] 単位         [17] 金額
[18] 税率
```

**重要: 列11（備考）と列12（取引日付）を間違えるとエラーになる**
```
エラーメッセージ: 項目「請求明細.取引日付」：データ型が一致しませんでした。期待：日付,実際：文字列
```

正しいCSV行の例:
```
AUTO3K-0001,2025/02/16,2025/03/31,TH003,,,,,,,,自動生成,,,1,10030,式,10030,10
                                                         ↑[11]備考  ↑[12]取引日付(空)
```

### React検索フォームの操作

一覧画面の検索フォームはReact管理のため、通常のPlaywright操作では検索が発動しない。

```python
# ★ requestSubmit() を使った React 互換検索
page.evaluate("""() => {
    const input = document.querySelector('#documentNumber');
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype, 'value'
    ).set;
    nativeInputValueSetter.call(input, 'AUTO3K');
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
    const form = input.closest('form');
    if (form) { try { form.requestSubmit(); } catch(e) { form.submit(); } }
}""")
```

- `nativeInputValueSetter` でReactのstateを更新
- `form.requestSubmit()` でフォーム送信（`form.submit()`ではReactのイベントが発火しない）
- 検索後のURL: `/invoices?...&documentNumber=AUTO3K&page=1`

### メモ記入の操作

```python
# メモフィールド: <textarea name="memo" id="memo">
# 保存ボタン: 「メモを保存する」
# 成功メッセージ: 「メモを保存しました」

page.evaluate("""() => {
    const el = document.querySelector('#memo');
    el.focus();
    const setter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype, 'value'
    ).set;
    setter.call(el, '自動生成');
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
}""")
```

### 大量データ処理の待機時間

| 件数 | CSVアップロード | データ確認 | プレビュー | 作成処理 | 合計 |
|---|---|---|---|---|---|
| 3件 | 5秒 | 10秒 | 15秒 | 30秒 | 約1分 |
| 3000件 | 15秒 | 60秒 | 60秒 | 約10分（BG） | 約13分+BG |

3000件の帳票作成はサーバー側バックグラウンド処理となり、「請求書の作成に時間がかかっています」と表示される。実際に一覧に反映されるまで約5-6分の追加待機が必要。

---

## A-5. 実行実績

| 日時 | スクリプト | 結果 | 備考 |
|---|---|---|---|
| 2026-02-16 | import_and_verify_v2.py | VERIFY2-001〜003 作成成功 | 確認ダイアログ対応で突破 |
| 2026-02-16 | write_memo_v2.py | 3件全てメモ保存成功 | 「メモを保存しました」確認 |
| 2026-02-16 | import_3000.py | 3000件作成成功 | 問題なし:3000件, エラー:0件 |
| 2026-02-16 | check_3000_status.py | 3000件中3000件確認 | ポーリング10回目で全件発見 |
| 2026-02-17 | run_csv_import.py | INTEG3-001〜003 作成成功 | 統合スクリプト初回テスト、3.2分で完了 |

---

# Part B: 請求書詳細画面 解析レポート（既存）

---

## 1. ページ構成概要

```
┌──────────────────────────────────────────────────────┐
│ [banner] ヘッダー                                      │
│   ロゴ | ユーザー名 | ヘルプ | 事業所切替               │
├──────────┬───────────────────────────────────────────┤
│ [nav]    │ [main] メインコンテンツ                      │
│ サイドバー │                                           │
│          │  パンくず: 請求書 > 帳票情報                  │
│ ・請求書  │  ページ送り: 1 / 8013件 ← →                │
│ ・取引先  │                                           │
│ ・帳票    │  見出し「請求書」+ 取引先名                   │
│ レイアウト │  アクション: 送付済み / 承認 / 削除           │
│          │                                           │
│          │  タブ: [帳票情報] [添付ファイル]               │
│          │                                           │
│          │  === 帳票情報タブ ===                        │
│          │  ステータス: 未送付 / 未承認                   │
│          │  取引先情報セクション                         │
│          │  送付先情報セクション                         │
│          │  帳票項目セクション                           │
│          │  基本情報セクション                           │
│          │  メモ入力フォーム                            │
│          │                                           │
│          │  === 添付ファイルタブ ===                     │
│          │  ファイルアップロード領域                      │
│          │  添付ファイル一覧（空の場合メッセージ表示）      │
│          │  使用状況 / 注意事項                         │
└──────────┴───────────────────────────────────────────┘
```

---

## 2. エリア別 要素一覧

### 2-1. ヘッダー（banner）

| 要素 | 推奨Playwright API |
|------|-------------------|
| ロゴ | `page.get_by_role("img", name="TOKIUM 請求書発行")` |
| ユーザー名表示 | `page.get_by_text("池田尚人")` |
| ヘルプリンク | `page.get_by_role("link", name="TOKIUM 請求書発行 - ヘルプセンター")` |
| 事業所切替ボタン | `page.get_by_text("ikeda_n+th1@tokium.jp")` |

### 2-2. サイドバー（navigation）

| 要素 | href | 推奨Playwright API |
|------|------|-------------------|
| 請求書 | /invoices | `page.get_by_role("link", name="請求書").first` |
| 取引先 | /partners | `page.get_by_role("link", name="取引先")` |
| 帳票レイアウト | /invoices/design | `page.get_by_role("link", name="帳票レイアウト")` |

> ⚠️ サイドバーの「請求書」リンクとパンくずの「請求書」リンクが同名。`.first`（サイドバー）/ `.last`（パンくず）またはロケーター絞り込みが必要。

### 2-3. パンくず・ページ送り

| 要素 | 推奨Playwright API |
|------|-------------------|
| パンくず「請求書」リンク | `page.get_by_role("navigation").filter(has=page.get_by_text("帳票情報")).get_by_role("link", name="請求書")` |
| パンくず「帳票情報」 | `page.get_by_text("帳票情報").first` |
| ページ位置表示 | `page.get_by_text("1 / 8013件")` |
| 戻るボタン | `page.get_by_role("button", name="戻る")` |
| 前の請求書ボタン | `page.get_by_role("button", name="前の請求書")` |
| 次の請求書ボタン | `page.get_by_role("button", name="次の請求書")` |

### 2-4. 見出し＆アクションボタン

| 要素 | 推奨Playwright API |
|------|-------------------|
| 見出し「請求書」 | `page.get_by_role("heading", name="請求書")` |
| 取引先名見出し | `page.get_by_role("heading", name="ひらがな")` ※データ依存 |
| 送付済みにするボタン | `page.get_by_role("button", name="送付済みにする")` |
| 承認するボタン | `page.get_by_role("button", name="承認する")` |
| 削除ボタン | `page.get_by_role("button", name="削除")` |

### 2-5. タブナビゲーション

| 要素 | 推奨Playwright API |
|------|-------------------|
| 帳票情報タブ | `page.get_by_role("button", name="帳票情報")` |
| 添付ファイルタブ | `page.get_by_role("button", name="添付ファイル")` |

> タブ切替で URL パラメータ `?tab=attachment` が追加される。

---

## 3. 帳票情報タブ（デフォルト）

### 3-1. ステータス表示

| 要素 | 推奨Playwright API |
|------|-------------------|
| 送付ステータス「未送付」 | `page.get_by_text("未送付")` |
| 承認ステータス「未承認」 | `page.get_by_text("未承認")` |

### 3-2. 取引先情報セクション

| 要素 | 推奨Playwright API |
|------|-------------------|
| セクション見出し | `page.get_by_role("heading", name="取引先情報")` |
| 取引先コード（ラベル） | `page.get_by_text("取引先コード")` |
| 取引先コード（値） | `page.get_by_text("TH9002")` ※データ依存 |
| 取引先名（ラベル） | `page.get_by_text("取引先名").first` |
| 取引先名（値） | `page.get_by_text("ひらがな").first` ※データ依存 |
| 送付先担当者情報見出し | `page.get_by_role("heading", name="送付先担当者情報")` |
| 自社担当者情報見出し | `page.get_by_role("heading", name="自社担当者情報")` |
| 担当者名（ラベル） | `page.get_by_text("担当者名")` ※2箇所あり |
| 取引先を選択するボタン | `page.get_by_role("button", name="取引先を選択する")` |

### 3-3. 取引先選択ダイアログ

「取引先を選択する」ボタンクリックで表示されるダイアログ。

| 要素 | 推奨Playwright API |
|------|-------------------|
| ダイアログ見出し | `page.get_by_role("heading", name="取引先選択")` |
| 閉じるボタン | `page.get_by_role("article").get_by_role("button").first` |
| 現在の取引先表示 | `page.get_by_text("現在の取引先")` |
| 検索ボタン | `page.get_by_role("button", name="検索")` |
| 取引先ラジオボタン | `page.get_by_role("radio")` ※name属性がUUID形式 |

> ⚠️ ラジオボタンのname属性は `partner-{UUID}` 形式。ラベルテキストでの特定が必要。
> 各ラジオボタンには取引先名・取引先コード・送付方法が表示される。

### 3-4. 送付先情報セクション

| 要素 | 推奨Playwright API |
|------|-------------------|
| セクション見出し | `page.get_by_role("heading", name="送付先情報")` |
| 送付方法（ラベル） | `page.get_by_text("送付方法")` |
| 送付方法（値） | `page.get_by_text("メール")` ※データ依存 |
| 送付先メールアドレス | `page.get_by_text("ikeda_n@tokium.jp")` ※データ依存 |

### 3-5. 帳票項目セクション

| 要素 | 推奨Playwright API |
|------|-------------------|
| セクション見出し | `page.get_by_role("heading", name="帳票項目")` |
| 合計金額（ラベル） | `page.get_by_text("合計金額")` |
| 請求日（ラベル） | `page.get_by_text("請求日")` |
| 支払期日（ラベル） | `page.get_by_text("支払期日")` |
| 請求書番号（ラベル） | `page.get_by_text("請求書番号")` |
| 請求書番号（値） | `page.get_by_text("請求番号: 202601231807")` ※データ依存 |

### 3-6. 基本情報セクション

| 要素 | 推奨Playwright API |
|------|-------------------|
| セクション見出し | `page.get_by_role("heading", name="基本情報")` |
| 管理ID（ラベル） | `page.get_by_text("管理ID")` |
| 管理ID（値） | `page.get_by_text("1048e806-20a2-4feb-8f10-ae62c4c6700e")` ※データ依存 |
| 登録日時（ラベル） | `page.get_by_text("登録日時")` |
| 登録日時（値） | `page.get_by_text("2026-02-13 14:36:40")` ※データ依存 |
| 登録方法（ラベル） | `page.get_by_text("登録方法")` |
| 登録方法（値） | `page.get_by_text("PDF取り込み")` |
| 登録者（ラベル） | `page.get_by_text("登録者")` |
| 登録者（値） | `page.get_by_text("ikeda_n+th1@tokium.jp")` |

### 3-7. メモフォーム

| 要素 | 推奨Playwright API |
|------|-------------------|
| メモラベル | `page.get_by_text("メモ")` |
| メモ入力欄 | `page.get_by_role("textbox", name="メモ")` |
| メモを保存するボタン | `page.get_by_role("button", name="メモを保存する")` |

> メモ欄は `<textarea id="memo" name="memo">` で実装されている。

---

## 4. 添付ファイルタブ

URL: `{詳細URL}?tab=attachment`

### 4-1. ファイルアップロード

| 要素 | 推奨Playwright API |
|------|-------------------|
| ファイルを選択ボタン | `page.get_by_role("button", name="ファイルを選択")` |
| ドラッグ&ドロップ説明 | `page.get_by_text("ここにファイルをドラッグ&ドロップ")` |
| ファイルinput（非表示） | `page.locator('button[type="file"]')` |

### 4-2. 添付ファイル一覧

| 要素 | 推奨Playwright API |
|------|-------------------|
| 空状態メッセージ | `page.get_by_text("この帳票には添付ファイルがありません。")` |

### 4-3. 使用状況

| 要素 | 推奨Playwright API |
|------|-------------------|
| セクション見出し | `page.get_by_role("heading", name="添付ファイルの使用状況")` |
| 添付件数見出し | `page.get_by_role("heading", name="添付件数")` |
| 上限表示 | `page.get_by_text("/ 10件")` |
| ファイルサイズ見出し | `page.get_by_role("heading", name="ファイルサイズ")` |
| サイズ上限表示 | `page.get_by_text("/ 10MB 使用中")` |
| 残り容量説明 | `page.get_by_text("残り 9.97MB")` ※データ依存 |

### 4-4. 添付ファイルについて（説明）

| 要素 | 推奨Playwright API |
|------|-------------------|
| セクション見出し | `page.get_by_role("heading", name="添付ファイルについて")` |
| ファイル形式見出し | `page.get_by_role("heading", name="ファイル形式")` |
| 対応形式説明 | `page.get_by_text("画像（JPEG、PNG、GIF）、PDF、Excel、Word、PowerPoint、CSV、テキストファイル")` |
| 注意事項見出し | `page.get_by_role("heading", name="注意事項")` |
| 注意事項1 | `page.get_by_text("添付したファイルは帳票と一緒に送付されます。")` |
| 注意事項2 | `page.get_by_text("アップロード中に別のページに移動")` |

---

## 5. ロケーター品質評価

### ✅ 良好な点
- ボタンにテキスト名あり → `get_by_role("button", name=...)` が使える
- セクション見出し（heading）が明確 → `get_by_role("heading", name=...)` で特定可能
- メモ欄に `<label>` とid/name設定あり → `get_by_role("textbox", name="メモ")` が使える
- タブボタンにテキスト名あり → `get_by_role("button", name=...)` で切替可能
- ナビゲーションボタン（前/次/戻る）にテキスト名あり

### ⚠️ 注意が必要な点
- **「請求書」リンクが複数**: サイドバーとパンくずに同名リンク → `.first` / ロケーター絞り込みが必要
- **取引先選択ダイアログのラジオボタン**: name属性が `partner-{UUID}` → ラベルテキストで特定が必要
- **ステータス表示に `data-testid` なし**: 「未送付」「未承認」などはテキストマッチングで特定
- **帳票項目の値が空の場合がある**: 合計金額・請求日・支払期日が未入力の場合のテスト考慮が必要
- **「担当者名」ラベルが2箇所**: 送付先担当者と自社担当者で同じテキスト → 親セクションで絞り込みが必要
- **データ依存の値が多い**: 取引先名・コード・メールアドレス等はテストデータに依存

---

## 6. テスト可能な操作シナリオ

### A. ページ表示・基本検証
- 詳細画面の表示確認（見出し、ステータス、各セクションの存在）
- パンくず表示の確認
- ページ送り位置表示の確認

### B. ナビゲーション
- 「戻る」ボタンで一覧に戻る
- パンくず「請求書」リンクで一覧に戻る
- 「前の請求書」「次の請求書」でページ送り
- サイドバーから取引先/帳票レイアウト画面へ遷移

### C. タブ切替
- 「帳票情報」タブ → 「添付ファイル」タブ切替
- URL パラメータ `?tab=attachment` の確認
- タブ切替後のコンテンツ表示確認

### D. 取引先情報
- 取引先コード・取引先名の表示確認
- 「取引先を選択する」ボタンでダイアログ表示
- ダイアログ内の検索・ラジオボタン選択

### E. 送付先情報
- 送付方法・メールアドレスの表示確認

### F. 帳票項目
- 合計金額・請求日・支払期日・請求書番号の表示確認

### G. 基本情報
- 管理ID・登録日時・登録方法・登録者の表示確認

### H. メモ操作
- メモ入力欄にテキスト入力
- 「メモを保存する」ボタンでメモ保存

### I. アクションボタン
- 「送付済みにする」ボタンの動作確認
- 「承認する」ボタンの動作確認
- 「削除」ボタンの動作確認（確認ダイアログの表示等）

### J. 添付ファイル操作
- 「ファイルを選択」ボタンでファイル選択
- ドラッグ&ドロップ領域の表示確認
- 添付ファイルの使用状況（件数・サイズ）の表示確認
- ファイルなし時のメッセージ表示確認

---

## 7. 一覧画面からの遷移方法

### テーブル行クリックによる遷移
- 一覧画面のテーブル行は `<tr class="_tableRow _clickable">` で実装
- 行にはリンク要素(`<a>`)なし → JavaScriptのクリックイベントで遷移
- 遷移先URLは `/invoices/{UUID}` 形式

### Playwrightでの遷移方法
```python
# 方法1: テーブル行を直接クリック
page.locator('table tbody tr').first.click()

# 方法2: 特定のテキストを含む行をクリック
page.get_by_text("ひらがな").first.click()

# 方法3: URLを直接指定（テスト用）
page.goto("https://invoicing-staging.keihi.com/invoices/{UUID}")
```

> ⚠️ 行クリック時、チェックボックス列をクリックするとチェックボックスが反応してしまうため、取引先名やステータス列をクリックすること。
