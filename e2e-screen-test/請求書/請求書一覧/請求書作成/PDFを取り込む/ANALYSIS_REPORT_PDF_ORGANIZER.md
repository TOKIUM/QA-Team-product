# PDF取り込み画面 解析レポート

**対象URL**:
- ファイル分割: `https://invoicing-staging.keihi.com/invoices/pdf-organizer/separation`
- ファイルリネーム: `https://invoicing-staging.keihi.com/invoices/pdf-organizer/rename`

**解析日**: 2026-02-18
**解析方法**: Claude in Chrome（アクセシビリティツリー + JavaScript DOM解析 + スクリーンショット）

---

## 1. 画面概要

PDF取り込み画面は、請求書一覧画面のアクションリンク「PDFを取り込む」から遷移する画面。
2つのモードがあり、相互に切り替え可能：

| モード | URL | ステップ数 | 説明 |
|--------|-----|-----------|------|
| ファイル分割 | /invoices/pdf-organizer/separation | 3 | ①ファイルアップロード → ②ファイルの分割 → ③プレビュー |
| ファイルリネーム | /invoices/pdf-organizer/rename | 2 | ①ファイルアップロード → ②ファイル名の変換 |

**重要**: `/invoices/pdf-organizer` にアクセスすると `/invoices/pdf-organizer/separation` にリダイレクトされる。

---

## 2. ページ構造

### 2.1 親ページ（TOKIUM側）

親ページは他画面と共通のヘッダー/サイドバー構造に加え、以下の要素を持つ：

#### ヘッダー（banner）
- ロゴ: `link href="/"`（TOKIUM 請求書発行）
- ユーザー名: `池田尚人`
- ヘルプリンク: `link "TOKIUM 請求書発行 - ヘルプセンター"`
- 事業所切替: `button`（TOKIUM設定用 / ikeda_n+th1@tokium.jp）

#### サイドバー（complementary > navigation）
- 請求書: `link href="/invoices"`
- 取引先: `link href="/partners"`
- 帳票レイアウト: `link href="/invoices/design"`

#### メインコンテンツ（main#main-content）

**パンくず（navigation）**:
- ファイル分割モード: `請求書` > `PDFを取り込む` > `ファイル分割`
- ファイルリネームモード: `請求書` > `PDFを取り込む` > `ファイルリネーム`

**モード切替リンク**:
- ファイル分割モード時: `link "ファイルリネームに切り替える" href="/invoices/pdf-organizer/rename"`
- ファイルリネームモード時: `link "ファイル分割に切り替える" href="/invoices/pdf-organizer/separation"`

**見出し（h1）**:
- ファイル分割モード: `PDFを分割して取り込む`
- ファイルリネームモード: `PDFをリネームして取り込む`

**iframe（メインコンテンツ）**:
- `iframe#organizer`（name属性なし）
- src: `https://tpmlyr.dev.components.asaservice.inc/report/organizer/tpmlyr/invoice/{tenant_id}/{token}`

---

### 2.2 iframe内コンテンツ（organizer iframe）

iframe内はクロスオリジンのため、Chrome拡張のアクセシビリティツリーからは取得不可。
スクリーンショットからの目視解析結果：

#### ファイル分割モード（Step 1: ファイルアップロード）
- **ステッパー**: ①ファイルアップロード → ②ファイルの分割 → ③プレビュー
- **案内テキスト**: 「アップロードするファイルを選択し、「次へ」を押下してください。」
- **アップロード可能なファイル**: ドロップダウン（詳細情報）
- **コンパクトモード**: トグルスイッチ（OFF→20ページ制限、OFF時50ページまで）
- **コンパクトモード説明文**:
  - 画面で操作可能なページを20ページまでに制限します。（分割はすべてのページで実行されます。）
  - ファイルの分割設定で処理が止まったり、ブラウザがフリーズするような場合にONにしてください。
  - コンパクトモードを利用しない場合、画面で操作可能なページ数は50ページまでです。
- **アップロードするファイル**: ドラッグ&ドロップ領域 / ファイル選択
- **キャンセル**: ボタン
- **次へ**: ボタン（disabled状態、ファイル選択後に有効化と想定）

#### ファイルリネームモード（Step 1: ファイルアップロード）
- **ステッパー**: ①ファイルアップロード → ②ファイル名の変換
- **案内テキスト**: 「アップロードするファイルを選択し、「次へ」を押下してください。」
- **アップロード可能なファイル**: ドロップダウン（詳細情報）
- **コンパクトモード**: トグルスイッチ
- **コンパクトモード説明文**:
  - 画面で操作可能なページを20ページまでに制限します。（ファイル名の変換はすべてのページで実行されます。）
  - キーワードの抽出で処理が止まったり、ブラウザがフリーズするような場合にONにしてください。
  - コンパクトモードを利用しない場合、画面で操作可能なページ数は50ページまでです。
- **アップロードするファイル**: ドラッグ&ドロップ領域 / ファイル選択
- **キャンセル**: ボタン
- **次へ**: ボタン（disabled状態）

---

## 3. Playwrightロケーター一覧

### 3.1 親ページ要素

```python
# パンくず
page.locator("#main-content").locator("nav")  # パンくずナビゲーション
page.get_by_role("link", name="請求書").first  # パンくず内「請求書」リンク
page.get_by_role("link", name="PDFを取り込む")  # パンくず内「PDFを取り込む」リンク

# 現在のモード表示（パンくず末尾テキスト）
# ファイル分割モード:
page.locator("span", has_text="ファイル分割")
# ファイルリネームモード:
page.locator("span", has_text="ファイルリネーム")

# モード切替リンク
page.get_by_role("link", name="ファイルリネームに切り替える")  # 分割→リネーム
page.get_by_role("link", name="ファイル分割に切り替える")      # リネーム→分割

# 見出し
page.get_by_role("heading", name="PDFを分割して取り込む")    # ファイル分割モード
page.get_by_role("heading", name="PDFをリネームして取り込む")  # ファイルリネームモード

# サイドバー
page.get_by_role("link", name="請求書", exact=True).first
page.get_by_role("link", name="取引先").first
page.get_by_role("link", name="帳票レイアウト").first

# ヘッダー
page.locator("text=池田尚人").first
page.get_by_role("link", name="TOKIUM 請求書発行 - ヘルプセンター")
```

### 3.2 iframe要素（Playwright経由）

```python
# iframe取得方法（name属性がないためURLパターンで取得）
organizer_frame = page.frame(url=lambda url: "organizer" in url)
# または
organizer_frame = page.frame(url=lambda url: "tpmlyr.dev.components.asaservice.inc" in url and "organizer" in url)

# iframe内要素（推定 - 実際のテスト実行時に検証が必要）
# ステッパー、ファイルアップロード領域、ボタン等はiframe内
# bounding_box() + page.mouse.click() パターンが必要になる可能性あり
```

---

## 4. DOM構造詳細

### 4.1 親ページHTML構造（JavaScript DOM解析結果）

```
<main#main-content class="_main_x4dgr_26 _filledFlex_x4dgr_38">
  <div class="_utilityBar_1lbmx_1">          // ユーティリティバー
    <nav class="_breadcrumbs_1t53b_1">       // パンくず
      <a> 請求書                              // href="/invoices"
      <svg>                                   // 区切り矢印
      <a> PDFを取り込む                       // href="/invoices/pdf-organizer"
      <svg>                                   // 区切り矢印
      <span class="_current_1t53b_19">        // 現在ページ（ファイル分割 or ファイルリネーム）
    <div class="_divider_6rirh_1">            // 区切り線（縦棒）
    <a class="_button_1e3w6_1">               // モード切替リンク
      <svg>                                   // アイコン
  <header>                                    // ヘッダー（見出し部分）
    <div>
      <h1> PDFを分割して取り込む              // or PDFをリネームして取り込む
    <aside>                                   // アクション領域（現状は空）
  <iframe#organizer>                          // メインコンテンツiframe
```

### 4.2 iframe詳細

| 属性 | 値 |
|------|-----|
| id | `organizer` |
| name | （空） |
| src | `https://tpmlyr.dev.components.asaservice.inc/report/organizer/tpmlyr/invoice/{tenant_id}/{token}` |
| style | `width: 100%; height: 100%; border: 0px;` |
| className | （空） |

**注意**: CSVインポートの`gallery`/`datatraveler` iframeは`name`属性があったが、`organizer` iframeは`name`が空。

---

## 5. テスト可能な項目

### 5.1 親ページテスト（iframe不要）

| # | テスト項目 | 対象要素 |
|---|-----------|---------|
| 1 | ページ表示・タイトル確認 | h1見出し、URLパス |
| 2 | パンくず表示 | nav内リンク3つ |
| 3 | パンくず「請求書」遷移 | link → /invoices |
| 4 | パンくず「PDFを取り込む」遷移 | link → /invoices/pdf-organizer |
| 5 | モード切替（分割→リネーム） | link → /pdf-organizer/rename |
| 6 | モード切替（リネーム→分割） | link → /pdf-organizer/separation |
| 7 | 見出し変化確認（分割モード） | h1 "PDFを分割して取り込む" |
| 8 | 見出し変化確認（リネームモード） | h1 "PDFをリネームして取り込む" |
| 9 | サイドバー表示 | 3つのリンク |
| 10 | ヘッダー表示 | ロゴ、ユーザー名、ヘルプ |
| 11 | iframe存在確認 | iframe#organizer |
| 12 | iframeのsrc確認 | tpmlyr.dev.components.asaservice.inc含む |

### 5.2 iframeテスト（organizer iframe経由）

| # | テスト項目 | 備考 |
|---|-----------|------|
| 13 | iframe読み込み確認 | frameオブジェクト取得 |
| 14 | ステッパー表示（分割3ステップ） | テキスト確認 |
| 15 | ステッパー表示（リネーム2ステップ） | テキスト確認 |
| 16 | 案内テキスト確認 | 「アップロードするファイルを選択し...」 |
| 17 | コンパクトモードトグル存在 | switch/toggle要素 |
| 18 | ファイルアップロード領域存在 | input[type="file"] or ドロップゾーン |
| 19 | キャンセルボタン | ボタン要素 |
| 20 | 次へボタン（初期disabled） | ボタン要素のdisabled状態 |

---

## 6. 技術的制約・知見

### 6.1 iframe name属性の不在
- `iframe#organizer` には `name` 属性がない
- Playwrightでの取得: `page.frame(url=lambda url: "organizer" in url)` を使用
- 代替: `page.frames` リストからURL/IDで特定

### 6.2 クロスオリジンiframe
- 外部ドメイン: `tpmlyr.dev.components.asaservice.inc`
- CSVインポート（gallery/datatraveler）・帳票レイアウト（gallery）と同一ドメイン
- Chrome拡張のread_page/find/clickはiframe内で動作しない
- Playwright: `frame.locator()` で操作可能（CSVインポートで実証済み）

### 6.3 操作パターン
- iframe内要素のクリック: `bounding_box()` + `page.mouse.click()` が最も確実
- iframe内テキスト入力: `bounding_box` + `mouse.click` + `keyboard.type`
- iframe読み込み待機: `wait_for_load_state("networkidle")` + 固定待機

### 6.4 Intercom iframe
- `iframe#intercom-frame` が別途存在（チャットサポートウィジェット）
- name属性なし、srcも空
- テスト対象外だがフレーム取得時に注意（URLフィルタで除外）

---

## 7. 他画面との比較

| 項目 | PDF取り込み | CSVインポート | 帳票レイアウト |
|------|-----------|-------------|-------------|
| URL | /invoices/pdf-organizer/* | /invoices/import | /invoices/design |
| iframe id | organizer | gallery + datatraveler | gallery |
| iframe name | （空） | gallery / datatraveler | gallery |
| iframe domain | tpmlyr.dev... | tpmlyr.dev... | tpmlyr.dev... |
| Playwright取得 | frame(url=...) | frame(name=...) | frame(name=...) |
| ステップ数 | 2-3（モードにより） | 5 | なし |
