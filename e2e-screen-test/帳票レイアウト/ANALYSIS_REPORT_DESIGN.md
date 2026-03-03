# 帳票レイアウト画面 解析レポート

**URL**: `https://invoicing-staging.keihi.com/invoices/design`
**解析日**: 2026-02-18
**解析方法**: Claude in Chrome（スクリーンショット・DOM解析・JS実行）

---

## 1. 画面概要

帳票レイアウト画面は、請求書の帳票テンプレート（レイアウト）を管理する画面。
サイドバー「帳票レイアウト」から遷移する。

### 画面構成
- **ヘッダー**: TOKIUM ロゴ、ユーザー名（池田尚人）、ヘルプ、事業所切替
- **サイドバー**: 請求書、取引先、帳票レイアウト（アクティブ）
- **ユーティリティバー（親ページ）**: 「戻る」ボタン、パンくず（帳票レイアウト > レイアウト選択）
- **gallery iframe**: レイアウトカード一覧（検索・切替・並べ替え・新規作成）

### 重要な技術的特徴
- **メインコンテンツは外部ドメインiframe内に存在**
  - iframe id: `gallery`
  - iframe src: `https://tpmlyr.dev.components.asaservice.inc/report/gallery/...`
  - CSVインポート画面（/invoices/import）と同じドメイン
- 親ページにあるのは「戻る」ボタンとパンくずのみ
- iframe内のUI操作はPlaywrightの `page.frame(name="gallery")` 経由で行う

---

## 2. 親ページ要素（/invoices/design）

### 2.1 ユーティリティバー

| 要素 | ロケーター | 備考 |
|------|-----------|------|
| 戻るボタン | `page.get_by_role("button", name="戻る")` | ブラウザバック動作 |
| パンくず「帳票レイアウト」リンク | `page.get_by_role("link", name="帳票レイアウト")` | /invoices/design へ |
| パンくず「レイアウト選択」 | テキストノード | 現在のページ |

### 2.2 サイドバー

| 要素 | ロケーター |
|------|-----------|
| 請求書 | `page.get_by_role("link", name="請求書")` → /invoices |
| 取引先 | `page.get_by_role("link", name="取引先")` → /partners |
| 帳票レイアウト | `page.get_by_role("link", name="帳票レイアウト")` → /invoices/design |

### 2.3 ヘッダー

| 要素 | ロケーター |
|------|-----------|
| ロゴ | `page.get_by_role("link").first` → / |
| ユーザー名 | テキスト「池田尚人」 |
| ヘルプ | `page.get_by_role("link", name="TOKIUM 請求書発行 - ヘルプセンター")` |
| 事業所切替 | `page.get_by_role("button")` （TOKIUM設定用 テキスト含む） |

---

## 3. gallery iframe内の要素（レイアウト選択画面）

### 3.1 ツールバー

| 要素 | 説明 | 推定ロケーター（iframe内） |
|------|------|--------------------------|
| 検索バー | テキスト入力「レイアウト名で検索」 | `frame.get_by_placeholder("レイアウト名で検索")` |
| グリッド表示ボタン | 左側（選択中=青） | `frame.locator("button")` でアイコン判定 |
| リスト表示ボタン | 右側 | 同上 |
| 並べ替え | ドロップダウン「並べ替え」 | `frame.get_by_text("並べ替え")` |
| 新規作成ボタン | 青ボタン＋▼ドロップダウン | `frame.get_by_text("新規作成")` |

### 3.2 レイアウトカード

- 表示形式: グリッド（3列）またはリスト
- 確認時点で5件のレイアウトが存在:
  - 1行目: 「サンプルレイアウト_担当者情報あ…」×3
  - 2行目: 別デザイン ×2
- カードにはサムネイル画像とレイアウト名が表示
- **カードクリックで レイアウト編集/詳細画面に遷移する可能性あり**

### 3.3 MUI Grid構造（CSVインポートと同系統）

CSVインポートのレイアウト選択と同じ gallery iframe を使用:
```python
# iframe取得パターン
gallery_frame = page.frame(name="gallery")

# カード一覧取得（MUI Grid）
grid_items = gallery_frame.query_selector_all(".MuiGrid-item")
```

---

## 4. 技術的制約・操作方法

### 4.1 iframe操作

| 制約 | 詳細 |
|------|------|
| クロスオリジン | gallery iframe は `tpmlyr.dev.components.asaservice.inc` ドメイン |
| DOM直接アクセス不可 | 親ページJSからiframe内DOMを読めない |
| Chrome拡張制限 | Claude in Chrome の read_page / find / click がiframe内で動作しない |
| Playwright対応 | `page.frame(name="gallery")` で操作可能（CSVインポートと同じ） |

### 4.2 Playwrightでの操作パターン（推定）

```python
# iframe取得
gallery_frame = page.frame(name="gallery")
assert gallery_frame is not None

# iframe内のロード待機
gallery_frame.wait_for_load_state("networkidle")
page.wait_for_timeout(3000)

# 検索
search_input = gallery_frame.get_by_placeholder("レイアウト名で検索")
search_input.fill("サンプル")

# カード取得
grid_items = gallery_frame.query_selector_all(".MuiGrid-item")

# カードクリック（bounding_box + page.mouse.click が確実）
box = grid_items[0].bounding_box()
page.mouse.click(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
```

### 4.3 「戻る」ボタンの動作

- `page.get_by_role("button", name="戻る")` は**ブラウザバック**動作
- 帳票レイアウト画面のトップに戻るわけではない
- 前のページ（遷移元）に戻る

---

## 5. テスト観点

### 5.1 親ページ側（iframe外）

| # | テスト観点 | 内容 |
|---|-----------|------|
| 1 | 画面遷移 | サイドバー「帳票レイアウト」クリックで/invoices/designに遷移 |
| 2 | パンくず表示 | 「帳票レイアウト > レイアウト選択」が表示される |
| 3 | 戻るボタン | 前のページに戻る（ブラウザバック動作） |
| 4 | gallery iframe存在 | `page.frame(name="gallery")` が取得できる |
| 5 | サイドバーアクティブ状態 | 帳票レイアウトがアクティブ表示 |

### 5.2 gallery iframe内

| # | テスト観点 | 内容 |
|---|-----------|------|
| 6 | iframe読み込み | gallery iframeが正常にロードされる |
| 7 | レイアウトカード一覧 | MuiGrid-itemが1件以上表示される |
| 8 | 検索バー存在 | 「レイアウト名で検索」プレースホルダーの入力欄がある |
| 9 | グリッド/リスト切替 | 表示切替ボタンが存在する |
| 10 | 並べ替え | 「並べ替え」コントロールが存在する |
| 11 | 新規作成ボタン | 「新規作成」ボタンが存在する |
| 12 | 検索機能 | 検索バーに文字入力→カード絞り込み |
| 13 | カードクリック遷移 | カードクリック→URL変化 or 画面遷移 |

### 5.3 留意事項

- iframe内のロードに時間がかかる（8秒程度待機が必要）
- iframe内の要素はMUI (Material-UI) ベース
- `bounding_box()` + `page.mouse.click()` が最も確実なクリック方法
- リスト表示切替やカード詳細遷移の挙動はPlaywright実行時に検証

---

## 6. URL構造（推定）

| 画面 | URL |
|------|-----|
| レイアウト一覧（選択） | `/invoices/design` |
| レイアウト詳細/編集 | `/invoices/design/{id}` （推定） |
| CSVインポート | `/invoices/import` → レイアウト選択 → `/invoices/import/{id}` |

---

## 7. 関連ファイル

- CSVインポートテスト: `請求書画面/請求書作成/test_invoice_creation.py`
  - 同じgallery iframeを使用、MuiGrid-itemパターンの実績あり
- 請求書画面CLAUDE.md: iframe操作の技術知見記載あり
