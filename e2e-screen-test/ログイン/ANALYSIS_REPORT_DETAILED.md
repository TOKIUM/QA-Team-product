# ログイン画面 詳細分析レポート

**URL**: https://invoicing-staging.keihi.com/login
**タイトル**: TOKIUM 請求書発行
**分析日**: 2026-03-02
**前回分析**: 2026-02-13（ANALYSIS_REPORT.md）
**差分**: 前回はアクセシビリティツリー + ロケーター品質のみ。今回はDOM構造・CSS・レイアウト・技術スタック・状態遷移を網羅

---

## 1. 技術スタック

| 項目 | 詳細 |
|------|------|
| **フレームワーク** | React（`#root` マウント、`__reactFiber` / `__reactProps` 確認済み） |
| **CSS方式** | CSS Modules（`_className_hash_N` 形式のクラス名） |
| **CSS-in-JS** | goober（`#_goober` styleタグ、react-hot-toast用） |
| **アイコン** | Font Awesome 6（Free / Pro / Brands / Sharp / Duotone）+ インラインSVG |
| **バンドル** | Vite（`/assets/index-DbGt5k5I.css`, `/assets/index-DnEv538W.js`） |
| **トースト通知** | react-hot-toast（gooberキーフレーム `go2264125279` 等5本確認） |
| **言語** | `lang="ja"`, `charset="UTF-8"` |
| **レスポンシブ** | `<meta name="viewport" content="width=device-width, initial-scale=1.0">` |

### CSS Moduleクラス一覧（ページ内で使用されている全20クラス）

| クラス名 | 推定コンポーネント |
|---------|------------------|
| `_layout_q1awf_1` | ページ全体のレイアウトラッパー |
| `_header_q1awf_12` | ヘッダー（ロゴ + タイトル） |
| `_main_q1awf_29` | メインコンテンツ（フォーム領域） |
| `_stack_l2w3v_1` | Stackレイアウトコンポーネント（汎用） |
| `_directionColumn_l2w3v_13` | Stack方向: 縦 |
| `_directionRow_l2w3v_9` | Stack方向: 横 |
| `_gapDefault_l2w3v_21` | Stack間隔: デフォルト |
| `_gapSmall_l2w3v_29` | Stack間隔: 小 |
| `_itemsBaseline_l2w3v_49` | align-items: baseline |
| `_button_1ed6y_1` | Buttonコンポーネント |
| `_colorPrimary_1ed6y_89` | ボタン色: プライマリ |
| `_alignCenter_1ed6y_312` | ボタン配置: 中央 |
| `_sizeMedium_1ed6y_331` | ボタンサイズ: M |
| `_block_1ed6y_32` | ボタン表示: block（幅100%） |
| `_textInput_ry80f_1` | テキスト入力コンポーネント |
| `_label_mj1ag_1` | ラベルコンポーネント |
| `_anchor_1ke6d_1` | アンカーリンクコンポーネント |
| `_divider_6rirh_1` | 区切り線コンポーネント |
| `_horizontal_6rirh_6` | 区切り線方向: 水平 |
| `_marginNone_6rirh_20` | 区切り線マージン: なし |

---

## 2. レイアウト構成

### 2-1. 全体グリッド

```
┌─────────────────────────────────┬──────────────┐
│                                 │              │
│     グレー背景エリア              │  白パネル     │
│     (ロゴ + 「ログイン」)          │  (フォーム)   │
│                                 │              │
│     _layout_q1awf_1 (CSS Grid)  │  _main       │
│     ├── _header (ロゴ部)         │  width:416px │
│     └── _main (フォーム部)        │  padding:32px│
│                                 │              │
└─────────────────────────────────┴──────────────┘
```

| 領域 | CSS | サイズ | 配色 |
|------|-----|--------|------|
| **全体ラッパー** | `display: grid` | 幅100vw × 高さ100vh | — |
| **左エリア（背景）** | グリッドの残り領域 | 可変 | `rgb(241, 241, 241)` 薄グレー |
| **ヘッダー（ロゴ）** | `display: block` | 240×57px | 透明背景 |
| **右エリア（フォーム）** | `display: grid; align-items: center` | 固定幅 416px × 全高 | `rgb(255, 255, 255)` 白 |
| **フォーム** | `display: flex; flex-direction: column` | 352px | — |

### 2-2. ロゴ表示

- **画像**: `TOKIUM` ロゴ + 「請求書発行」バッジ（`alt="TOKIUM 請求書発行"`）
- **タイトル**: `<h1>` 内の `<span>` で「ログイン」を表示
- **構造**: `<h1>` > `<a href="/">` > `<img>` + `<span>"ログイン"`
- ロゴクリックで `/` (トップページ) に遷移

---

## 3. フォーム要素の詳細

### 3-1. 構造

```
<form method="get" action="/login">     ← GET送信（Reactが制御、実際はSPA遷移）
  ├── <div> (Stack vertical, gap-small)
  │   ├── <label for="email">メールアドレス</label>
  │   └── <input#email type="email" autocomplete="email">
  │
  ├── <div> (Stack vertical, gap-small)
  │   ├── <label for="password">パスワード</label>
  │   └── <input#password type="password" placeholder="8文字以上のパスワードを入力">
  │
  ├── <p>
  │   └── <button type="submit">
  │       ├── <svg> (ログインアイコン)
  │       └── "ログイン"
  │
  ├── <a href="/recovery">パスワードを忘れた場合</a>
  │
  ├── <hr> (divider)
  │
  ├── <a href="/auth-redirect">
  │   └── <button type="button">
  │       ├── <svg> (ログインアイコン)
  │       └── "TOKIUM ID でログイン"
  │
  └── <a href="/registration">新規登録はこちら</a>
</form>
```

### 3-2. 入力フィールド詳細

| 属性 | メールアドレス (`#email`) | パスワード (`#password`) |
|------|--------------------------|-------------------------|
| **type** | `email` | `password` |
| **name** | `email` | `password` |
| **id** | `email` | `password` |
| **placeholder** | （なし） | `8文字以上のパスワードを入力` |
| **autocomplete** | `email` | `on` |
| **required** | `false` ⚠ | `false` ⚠ |
| **pattern** | なし | なし |
| **minLength / maxLength** | なし | なし |
| **CSSクラス** | `_textInput_ry80f_1` | `_textInput_ry80f_1` |
| **幅** | 352px | 352px |
| **高さ** | 40px | 40px |
| **ボーダー** | `1px solid rgb(213, 213, 211)` | 同左 |
| **角丸** | `4px` | `4px` |
| **内側影** | `rgba(52,58,64,0.1) 0px 1px 4px inset` | 同左 |
| **文字サイズ** | 16px | 16px |
| **背景色** | `rgb(232, 240, 254)` ※ブラウザ自動補完時 | `rgb(255, 255, 255)` |
| **文字色** | `rgb(52, 74, 64)` | 同左 |
| **パディング** | `7px 12px` | `7px 12px` |

> ⚠ `required` 属性なし → HTMLネイティブバリデーションは無効。バリデーションはReact側（JavaScript）で処理されていると推測

### 3-3. ボタン詳細

| 属性 | ログインボタン | TOKIUM ID でログインボタン |
|------|--------------|---------------------------|
| **テキスト** | `ログイン` | `TOKIUM ID でログイン` |
| **type** | `submit` | `button` |
| **SVGアイコン** | あり（右矢印） | あり（右矢印） |
| **背景色** | `rgb(0, 155, 155)` ティール | `rgb(0, 155, 155)` ティール |
| **文字色** | `rgb(255, 255, 255)` 白 | `rgb(255, 255, 255)` 白 |
| **幅** | 352px（100%） | 352px（100%） |
| **高さ** | 44px | 44px |
| **角丸** | 4px | 4px |
| **ボーダー** | `1px solid rgb(0, 155, 155)` | 同左 |
| **文字サイズ** | 16px | 16px |
| **文字太さ** | 700 (bold) | 700 (bold) |
| **親要素** | `<p>` | `<a href="/auth-redirect">` |
| **disabled** | false | false |

#### ボタンのインタラクションCSS

```css
/* ホバー/フォーカス時 */
._button:hover, ._button:focus {
  text-decoration: none;
  outline-color: var(--color-outline);
}

/* プライマリ ホバー時 */
._colorPrimary:hover {
  background-color: var(--color-primary-dark);
  border-color: var(--color-primary-dark);
}

/* 無効時 */
._button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
```

### 3-4. リンク詳細

| リンクテキスト | href | 位置 | スタイル |
|--------------|------|------|---------|
| （ロゴ画像） | `/` | ヘッダー左 | — |
| パスワードを忘れた場合 | `/recovery` | フォーム下、ログインボタン直後 | `rgb(0, 155, 155)` ティール |
| TOKIUM ID でログイン | `/auth-redirect` | 区切り線の下 | ボタン内包 |
| 新規登録はこちら | `/registration` | フォーム最下部 | `rgb(0, 155, 155)` ティール |

---

## 4. スタイル・デザインシステム

### 4-1. タイポグラフィ

| 要素 | フォント | サイズ | 太さ | 色 |
|------|---------|--------|------|-----|
| body | Avenir, Roboto, "Helvetica Neue", ... "Hiragino Sans", "BIZ UDPGothic", YuGothic, メイリオ, sans-serif | 16px | 400 | `rgb(52, 74, 64)` |
| h1 | 同上 | 32px | 700 | `rgb(52, 74, 64)` |
| label | 同上 | 16px | 700 | `rgb(84, 94, 100)` |
| ボタン | 同上 | 16px | 700 | `rgb(255, 255, 255)` |
| リンク | 同上 | 16px | 400 | `rgb(0, 155, 155)` |

### 4-2. カラーパレット

| 色 | RGB | 用途 |
|----|-----|------|
| ティール（プライマリ） | `rgb(0, 155, 155)` / `#009B9B` | ボタン背景、リンク文字 |
| ダークグリーン（テキスト） | `rgb(52, 74, 64)` / `#344A40` | 本文、見出し |
| グレー（ラベル） | `rgb(84, 94, 100)` / `#545E64` | ラベルテキスト |
| ライトグレー（ボーダー） | `rgb(213, 213, 211)` / `#D5D5D3` | inputボーダー |
| 背景グレー | `rgb(241, 241, 241)` / `#F1F1F1` | 左エリア背景 |
| 白 | `rgb(255, 255, 255)` | フォームパネル背景、ボタン文字 |
| 影（inset） | `rgba(52, 58, 64, 0.1)` | input内側影 |

### 4-3. 区切り線

- ログインボタン/パスワードリセットリンクとTOKIUM IDボタンの間に `<hr>` （水平区切り線）
- クラス: `_divider_6rirh_1 _horizontal_6rirh_6 _marginNone_6rirh_20`

---

## 5. インタラクション・状態遷移

### 5-1. フォーカス時のスタイル変化

| 項目 | 通常時 | フォーカス時 |
|------|--------|------------|
| input border | `1px solid rgb(213, 213, 211)` | 変化なし（CSSルールでは `outline-color: var(--color-outline)` が定義されているが、getComputedStyleでは差分なし） |
| input boxShadow | `rgba(52,58,64,0.1) 0px 1px 4px inset` | 変化なし |
| button | — | `outline-color: var(--color-outline)` + `text-decoration: none` |

> **注**: ブラウザ自動補完が入っている場合、email inputの背景が `rgb(232, 240, 254)` （青みがかった色）に変わる

### 5-2. バリデーション

| 項目 | 状態 |
|------|------|
| HTML5 required | **未設定**（email, passwordとも） |
| HTML5 pattern | **未設定** |
| HTML5 minLength/maxLength | **未設定** |
| ブラウザネイティブバリデーション | `type="email"` によるメール形式チェックのみ |
| React側バリデーション | 推定あり（サーバーサイドでエラーメッセージを返す仕組み） |

### 5-3. エラー表示

- **初期状態**: エラー表示要素なし
- **エラーコンテナ**: `[role="alert"]`, `[class*="error"]`, `[class*="toast"]` 等の要素は初期状態では存在しない
- **トースト通知**: react-hot-toast が読み込まれている（gooberのキーフレーム確認済み）が、初期状態ではコンテナ未生成
- **推定**: ログイン失敗時にreact-hot-toastでエラートースト表示される可能性が高い

### 5-4. タブ順序

```
1. <a> ロゴ (tabIndex: 0)
2. <input#email> メールアドレス (tabIndex: 0)
3. <input#password> パスワード (tabIndex: 0)
4. <button> ログイン (tabIndex: 0)
5. <a> パスワードを忘れた場合 (tabIndex: 0)
6. <button> TOKIUM ID でログイン (tabIndex: 0)
7. <a> 新規登録はこちら (tabIndex: 0)
```

---

## 6. アクセシビリティ評価

### 良好な点
- 全フォーム要素に `<label>` + `for` 属性が設定済み
- セマンティックHTML使用（`<header>`, `<main>`, `<form>`, `<h1>`）
- `role="banner"` が header に暗黙的に適用
- ボタンに明確なテキストあり
- `lang="ja"` 設定済み

### 改善の余地
- `data-testid` 属性なし（テスト自動化ではセマンティックロケーターで代替可能）
- `aria-required` 未設定（`required` 属性自体も未設定）
- `aria-invalid` 未設定（エラー時の状態通知が不明）
- `aria-describedby` 未設定（パスワードのplaceholderヒントをaria-describedbyで紐づけるのが理想）
- TOKIUM IDボタンが `<a>` > `<button>` のネスト構造（アクセシビリティ上は冗長）

---

## 7. 既存テストとのギャップ分析

### 現在のテスト（5件、全PASS）
| TC-ID | カテゴリ | 内容 |
|-------|---------|------|
| TH-L01 | 表示 | 主要要素の表示確認 |
| TH-L02 | 遷移 | パスワードリセットへの遷移 |
| TH-L03 | 遷移 | 新規登録への遷移 |
| TH-L04 | 遷移 | TOKIUM IDログインへの遷移 |
| TH-L05 | 認証 | 正常ログイン |

### 未カバー領域（追加テスト候補）

| # | カテゴリ | テスト内容 | 優先度 |
|---|---------|-----------|--------|
| 1 | **異常系: 認証失敗** | 誤ったパスワードでログイン → エラーメッセージ表示確認 | 高 |
| 2 | **異常系: 空入力** | メール/パスワード未入力でログインボタン押下 → エラー表示確認 | 高 |
| 3 | **異常系: メール形式不正** | `type="email"` のブラウザバリデーション動作確認 | 中 |
| 4 | **異常系: 存在しないユーザー** | 未登録メールアドレスでログイン → エラーメッセージ確認 | 中 |
| 5 | **UI: レイアウト** | 左右2カラムレイアウトの表示確認（ロゴ左、フォーム右） | 低 |
| 6 | **UI: 区切り線** | ログインボタンとTOKIUM IDボタンの間のdivider表示確認 | 低 |
| 7 | **UI: プレースホルダー** | パスワード欄の「8文字以上のパスワードを入力」表示確認 | 低 |
| 8 | **UI: autocomplete** | email欄のautocomplete="email"動作確認 | 低 |
| 9 | **状態: フォーカス** | Tab操作でのフォーカス移動順序確認 | 低 |
| 10 | **状態: トースト** | ログイン失敗時のreact-hot-toastの表示・自動消去確認 | 高 |
| 11 | **遷移: ロゴ** | TOKIUMロゴクリックで `/` に遷移確認 | 低 |
| 12 | **セキュリティ: パスワードマスク** | パスワード入力がマスクされていること | 低 |

---

## 8. Playwrightロケーター推奨一覧（更新版）

| 要素 | 推奨ロケーター | 安定性 |
|------|--------------|--------|
| メールアドレス入力 | `page.get_by_label("メールアドレス")` | ★★★ |
| パスワード入力 | `page.get_by_label("パスワード")` | ★★★ |
| ログインボタン | `page.get_by_role("button", name="ログイン", exact=True)` | ★★★ |
| パスワードリセットリンク | `page.get_by_role("link", name="パスワードを忘れた場合")` | ★★★ |
| TOKIUM IDボタン | `page.get_by_role("button", name="TOKIUM ID でログイン")` | ★★★ |
| 新規登録リンク | `page.get_by_role("link", name="新規登録はこちら")` | ★★★ |
| ロゴリンク | `page.get_by_role("link").filter(has=page.get_by_role("img", name="TOKIUM 請求書発行"))` | ★★☆ |
| 区切り線 | `page.locator("hr")` | ★★☆ |
| エラートースト（推定） | `page.locator('[class*="go"], [role="status"]')` | ★☆☆（要実機確認） |
