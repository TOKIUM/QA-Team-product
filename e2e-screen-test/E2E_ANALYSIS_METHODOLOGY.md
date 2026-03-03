# WEBシステム E2E分析・テスト自動化 手法ガイド

**作成日**: 2026-02-17
**ベース**: TOKIUM 請求書発行システムでの E2Eテスト自動化実績から抽出
**目的**: 任意のWEBシステムに対して、画面分析 → テストコード生成 → テスト実行を効率的に行うための汎用手法

---

## 全体フロー

```
Phase 1: 画面分析
  ├─ 1-1. ページ構成の把握（アクセシビリティツリー + スクリーンショット）
  ├─ 1-2. インタラクティブ要素の棚卸し
  ├─ 1-3. UIフレームワークの特定と対応方針の策定
  └─ 1-4. 分析レポートの作成

Phase 2: テスト設計
  ├─ 2-1. 操作フロー（ユーザージャーニー）の洗い出し
  ├─ 2-2. テストケースの設計（正常系 → 異常系 → 境界値）
  └─ 2-3. テストデータの準備

Phase 3: テスト実装・実行
  ├─ 3-1. テスト基盤の構築（conftest.py / 共通ヘルパー）
  ├─ 3-2. テストコードの生成（AI活用 or 手動）
  ├─ 3-3. 実行・デバッグ・安定化
  └─ 3-4. 結果の記録とレポート更新
```

---

## Phase 1: 画面分析

### 1-1. ページ構成の把握

#### 手順

**① アクセシビリティツリーの取得**

ブラウザのアクセシビリティAPIを利用し、ページのセマンティック構造を取得する。
フレームワークやCSSに依存しない安定した情報源。

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://対象システムのURL")
    page.wait_for_load_state("networkidle")

    # アクセシビリティツリー取得
    snapshot = page.accessibility.snapshot()
    print(snapshot)
```

**② ゾーニング（画面領域の区分）**

画面をエリアごとに分解し、各エリアの役割を整理する。

```
典型的なゾーン構成:
┌─────────────────────────────────────────┐
│ [banner] ヘッダー                         │
│   ロゴ | ユーザー名 | ヘルプ | 設定        │
├──────────┬──────────────────────────────┤
│ [nav]    │ [main] メインコンテンツ         │
│ サイドバー │                              │
│          │  見出し + アクションボタン群      │
│ ・メニュー1│                              │
│ ・メニュー2│  検索/フィルタ                 │
│ ・メニュー3│                              │
│          │  データテーブル / フォーム        │
│          │                              │
│          │  ページネーション / フッター      │
└──────────┴──────────────────────────────┘
```

**③ スクリーンショットの取得**

各分析段階でスクリーンショットを残す。問題発生時の原因特定に不可欠。

```python
page.screenshot(path="analysis_step1_initial.png", full_page=True)
```

#### アウトプット例

```markdown
## ページ構成概要

| エリア | 役割 | 主要要素 |
|--------|------|---------|
| ヘッダー(banner) | 全体ナビ | ロゴ、ユーザー名、ヘルプリンク |
| サイドバー(nav) | 画面遷移 | メニューリンク群 |
| メインコンテンツ(main) | 業務操作 | 見出し、検索、テーブル、ボタン |
| フッター | ページ操作 | ページネーション、一括操作 |
```

---

### 1-2. インタラクティブ要素の棚卸し

#### 要素抽出スクリプト（汎用テンプレート）

```python
def extract_interactive_elements(page):
    """ページ上のインタラクティブ要素を一括抽出"""
    return page.evaluate("""() => {
        const selectors = [
            'a[href]', 'button', 'input', 'select', 'textarea',
            '[role="button"]', '[role="link"]', '[role="tab"]',
            '[role="menuitem"]', '[role="checkbox"]', '[role="radio"]',
            '[onclick]', '[tabindex]'
        ];

        const seen = new Set();
        const elements = [];

        for (const sel of selectors) {
            document.querySelectorAll(sel).forEach(el => {
                const key = el.tagName + '_' + (el.id || el.name || el.textContent?.trim().substring(0, 30));
                if (seen.has(key)) return;
                seen.add(key);

                const rect = el.getBoundingClientRect();
                if (rect.width === 0 && rect.height === 0) return;  // 非表示要素を除外

                // ラベルの取得
                let label = '';
                if (el.id) {
                    const labelEl = document.querySelector(`label[for="${el.id}"]`);
                    label = labelEl ? labelEl.textContent.trim() : '';
                }
                if (!label) {
                    const parentLabel = el.closest('label');
                    label = parentLabel ? parentLabel.textContent.trim() : '';
                }

                elements.push({
                    tag: el.tagName.toLowerCase(),
                    type: el.type || '',
                    role: el.getAttribute('role') || '',
                    name: el.name || '',
                    id: el.id || '',
                    text: el.innerText?.trim().substring(0, 80) || '',
                    label: label.substring(0, 80),
                    placeholder: el.placeholder || '',
                    disabled: el.disabled || false,
                    required: el.required || false,
                    ariaLabel: el.getAttribute('aria-label') || '',
                    testId: el.getAttribute('data-testid') || '',
                    href: el.href || '',
                    classes: (el.className || '').substring(0, 100),
                    rect: { x: Math.round(rect.x), y: Math.round(rect.y),
                            w: Math.round(rect.width), h: Math.round(rect.height) }
                });
            });
        }
        return elements.slice(0, 200);  // 上限200件
    }""")
```

#### ロケーター推奨の判定ロジック

抽出した各要素に対して、最も安定したPlaywrightロケーターを判定する。

```
ロケーター優先順位:
 1. get_by_role()       ← ARIA role + accessible name（最も安定）
 2. get_by_label()      ← <label for=...> によるフォーム紐付け
 3. get_by_placeholder() ← placeholder テキスト
 4. get_by_text()       ← テキスト内容マッチ（exact=True推奨）
 5. get_by_test_id()    ← data-testid 属性（あれば安定）
 6. locator(CSS)        ← CSSセレクタ（最終手段・壊れやすい）
```

**判定フローチャート:**

```
要素にrole属性 or 暗黙roleあり？
  ├─ Yes → テキストラベル or aria-labelあり？
  │          ├─ Yes → get_by_role("role名", name="ラベル")  ★推奨
  │          └─ No  → 近くにlabelあり？ → get_by_label("ラベル名")
  └─ No → <label for="..."> が紐付いている？
           ├─ Yes → get_by_label("ラベル名")
           └─ No  → placeholder あり？
                     ├─ Yes → get_by_placeholder("...")
                     └─ No  → data-testid あり？
                               ├─ Yes → get_by_test_id("...")
                               └─ No  → locator("CSSセレクタ")  ⚠壊れやすい
```

#### アウトプット例（要素一覧表）

```markdown
| # | 要素 | ロケーター | 推奨API | 安定度 |
|---|------|-----------|---------|--------|
| 1 | メールアドレス入力 | label="メールアドレス" | get_by_label("メールアドレス") | ★★★ |
| 2 | ログインボタン | button name="ログイン" | get_by_role("button", name="ログイン", exact=True) | ★★★ |
| 3 | 検索ボタン | button name="この条件で検索" | get_by_role("button", name="この条件で検索") | ★★★ |
| 4 | テーブル行 | table tbody tr | locator("table tbody tr").nth(N) | ★☆☆ |
```

---

### 1-3. UIフレームワークの特定と対応方針

#### フレームワーク検出スクリプト

```python
def detect_ui_framework(page):
    """ページで使用されているUIフレームワークを検出"""
    return page.evaluate("""() => {
        const frameworks = [];

        // React
        if (document.querySelector('[data-reactroot]') ||
            document.querySelector('[data-reactid]') ||
            document.querySelector('div#__next') ||
            document.querySelector('div#root')?.__reactFiber) {
            frameworks.push('React');
        }

        // Material-UI (MUI)
        if (document.querySelector('.MuiBox-root') ||
            document.querySelector('[class*="Mui"]')) {
            frameworks.push('Material-UI');
        }

        // Headless UI
        if (document.querySelector('[id*="headlessui"]') ||
            document.querySelector('[data-headlessui-state]')) {
            frameworks.push('Headless UI');
        }

        // Ant Design
        if (document.querySelector('.ant-btn') ||
            document.querySelector('[class*="ant-"]')) {
            frameworks.push('Ant Design');
        }

        // Bootstrap
        if (document.querySelector('.btn') &&
            document.querySelector('.container')) {
            frameworks.push('Bootstrap');
        }

        // Tailwind CSS (推定)
        const hasTailwind = document.querySelector('[class*="flex "]') &&
                           document.querySelector('[class*="px-"]');
        if (hasTailwind) frameworks.push('Tailwind CSS（推定）');

        // Next.js
        if (document.querySelector('div#__next') ||
            document.querySelector('script#__NEXT_DATA__')) {
            frameworks.push('Next.js');
        }

        // Vue
        if (document.querySelector('[data-v-]') ||
            document.querySelector('div#app')?.__vue__) {
            frameworks.push('Vue.js');
        }

        return frameworks;
    }""")
```

#### フレームワーク別の対応方針

| フレームワーク | 主な課題 | 対応方針 |
|--------------|---------|---------|
| **Headless UI** | `role="dialog"` の height=0 問題 | 子要素（h2等）で `wait_for(state="visible")` |
| **Headless UI** | portal-root によるポインタインターセプト | `click(force=True)` で回避 |
| **Material-UI** | ポップオーバーが `body` 直下に生成 | `page.locator('.MuiDialog-root')` でスコープ指定 |
| **React** | `fill()` + `pressEnter()` で検索が発火しない | `nativeInputValueSetter` + `form.requestSubmit()` |
| **Next.js** | ページ遷移が SPA 内遷移 | `page.wait_for_url()` or `expect().to_have_url()` |
| **iframe埋め込み** | Playwright click が iframe 境界で失敗 | `bounding_box()` + `page.mouse.click(x, y)` |

---

### 1-4. 分析レポートの作成

#### レポートテンプレート

```markdown
# ページ解析レポート: [システム名] - [画面名]

**URL**: https://...
**解析日**: YYYY-MM-DD
**UIフレームワーク**: [検出結果]

---

## 1. ページ構成概要
（ゾーニング図 + 各エリアの役割表）

## 2. エリア別 要素一覧
### 2-1. ヘッダー
（要素テーブル: 要素名 / ロケーター / 推奨API）
### 2-2. サイドバー
### 2-3. メインコンテンツ
...

## 3. ロケーター品質評価
✅ 良好な点:
⚠️ 注意が必要な点:

## 4. テスト可能な操作シナリオ
### A. 検索・フィルタリング
### B. テーブル操作
### C. フォーム入力
### D. モーダル/ダイアログ操作
...

## 5. 技術的な知見・リスク
| 課題 | 影響度 | 対応方針 |
```

---

## Phase 2: テスト設計

### 2-1. 操作フローの洗い出し

#### フロー記録の手順

1. **手動操作の観察**: 対象画面を手動で操作しながら、各操作ステップを記録
2. **スクリーンショット**: 各操作の前後でスクリーンショットを取得
3. **タイミング計測**: 各操作にかかる時間を記録（UIラグ vs バックグラウンド処理の判別）
4. **分岐の特定**: 成功/失敗/条件分岐を洗い出す

#### フロー記録テンプレート

```markdown
## 操作フロー: [フロー名]

### 前提条件
- ログイン済み状態
- 〇〇画面を表示している

### ステップ

| # | 操作 | 対象要素 | 期待結果 | 所要時間 |
|---|------|---------|---------|---------|
| 1 | ボタンクリック | get_by_role("button", name="...") | モーダルが開く | ~1秒 |
| 2 | ファイル選択 | locator('input[type="file"]') | ファイル名が表示 | ~2秒 |
| 3 | 確認ボタンクリック | get_by_role("button", name="確認") | 確認画面に遷移 | ~1秒 |
| 4 | 非同期処理待ち | — | ボタンがenabledに | ~2-30秒 |
| 5 | 実行ボタンクリック | get_by_role("button", name="実行") | 処理完了画面 | ~8秒 |

### 注意事項
- Step 4: 非同期処理のため `expect().to_be_enabled(timeout=30000)` で待機
- Step 5: force=True 必須（ポインタインターセプト回避）
```

---

### 2-2. テストケースの設計

#### 設計順序

```
1. 正常系（Happy Path）: 最も基本的な成功パターン
   └─ まず動くテストを1本作り、基盤の安定性を確認

2. バリエーション: 正常系の入力パターンを変える
   └─ ファイル種類、入力値、選択数など

3. 異常系（Error Path）: エラーが期待される操作
   └─ 上限超過、未入力、不正値など

4. 境界値: 上限ギリギリの値
   └─ ファイルサイズ上限、文字数上限、件数上限など

5. 操作系: ユーザーの戻る・キャンセル操作
   └─ 途中離脱、戻るボタン、×ボタンなど
```

#### テストケーステンプレート

```markdown
| TC-ID | カテゴリ | テスト名 | 入力データ | 期待結果 | 優先度 |
|-------|---------|---------|-----------|---------|--------|
| TC-01 | 正常系 | 基本操作 | 有効なデータ | 成功メッセージ | 高 |
| TC-02 | 正常系 | 複数データ | 3件同時 | 成功メッセージ(3件) | 高 |
| TC-03 | 異常系 | 上限超過 | 制限超えデータ | エラーメッセージ | 中 |
| TC-04 | 境界値 | ギリギリ成功 | 上限値ちょうど | 成功メッセージ | 中 |
| TC-05 | 操作系 | 途中キャンセル | — | 元の画面に戻る | 低 |
```

---

### 2-3. テストデータの準備

#### ファイル生成スクリプトのテンプレート

テスト用ファイルを自動生成するスクリプトを作っておくと、環境再構築が容易。

```python
"""テストファイル生成スクリプト（汎用テンプレート）"""
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "test_files")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_pdf(filepath: str, size_bytes: int = 1024):
    """指定サイズのPDFを生成"""
    header = b"%PDF-1.4\n"
    trailer = b"\n%%EOF"
    padding = b"0" * max(0, size_bytes - len(header) - len(trailer))
    with open(filepath, "wb") as f:
        f.write(header + padding + trailer)

def create_text_file(filepath: str, content: str = "test"):
    """テキストファイルを生成"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

# サイズバリエーション
create_pdf(os.path.join(OUTPUT_DIR, "small.pdf"), 1024)           # 1KB
create_pdf(os.path.join(OUTPUT_DIR, "medium.pdf"), 5 * 1024**2)   # 5MB
create_pdf(os.path.join(OUTPUT_DIR, "large.pdf"), 9.9 * 1024**2)  # 9.9MB（上限以内）
create_pdf(os.path.join(OUTPUT_DIR, "over.pdf"), 10.1 * 1024**2)  # 10.1MB（上限超過）

# ファイル名バリエーション
create_pdf(os.path.join(OUTPUT_DIR, "日本語ファイル.pdf"))
create_pdf(os.path.join(OUTPUT_DIR, "special !@#$.pdf"))
create_pdf(os.path.join(OUTPUT_DIR, "a" * 200 + ".pdf"))  # 長いファイル名
```

---

## Phase 3: テスト実装・実行

### 3-1. テスト基盤の構築

#### conftest.py テンプレート

```python
"""pytest共通設定（汎用テンプレート）"""
import os
import re
import pytest
from playwright.sync_api import Page, expect

# 環境変数から設定を読み込み（.env or CI/CD環境変数）
BASE_URL = os.environ.get("BASE_URL", "https://対象システムURL")
TEST_EMAIL = os.environ.get("TEST_EMAIL", "test@example.com")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD", "password")


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """ブラウザコンテキスト設定（セッション全体で共有）"""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "locale": "ja-JP",           # 日本語UIの場合
        "timezone_id": "Asia/Tokyo",  # タイムゾーン
    }


@pytest.fixture
def logged_in_page(page: Page) -> Page:
    """ログイン済みページを返すフィクスチャ"""
    page.goto(f"{BASE_URL}/login")

    # ログインフォームが表示されるまで待機
    page.get_by_role("button", name="ログイン", exact=True).wait_for(state="visible")

    # 認証情報を入力
    page.get_by_label("メールアドレス").fill(TEST_EMAIL)
    page.get_by_label("パスワード").fill(TEST_PASSWORD)
    page.wait_for_timeout(500)  # フォームバリデーション待ち

    # ログインボタンクリック
    page.get_by_role("button", name="ログイン", exact=True).click()

    # ログイン後のURL遷移を待機（ポーリングではなく expect で待つ）
    expect(page).to_have_url(re.compile(r"/dashboard|/home|/invoices"), timeout=30000)

    return page
```

#### 共通ヘルパー関数テンプレート

```python
"""共通ヘルパー関数（汎用テンプレート）"""
import os
from datetime import datetime


def load_env(env_path: str) -> dict:
    """
    .envファイルを読み込む。
    Windows PowerShellでは os.environ 経由が不安定な場合があるため、
    直接ファイルから読み込む方式を併用する。
    """
    vals = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    vals[k.strip()] = v.strip()
    return vals


def login(page, base_url: str, email: str, password: str):
    """共通ログイン処理"""
    page.goto(f"{base_url}/login")
    page.get_by_role("button", name="ログイン", exact=True).wait_for(state="visible")
    page.get_by_label("メールアドレス").fill(email)
    page.get_by_label("パスワード").fill(password)
    page.wait_for_timeout(500)
    page.get_by_role("button", name="ログイン", exact=True).click()
    for _ in range(30):
        if "/login" not in page.url:
            break
        page.wait_for_timeout(1000)


def wait_for_button_enabled(page, button_name: str, timeout: int = 30000):
    """
    非同期処理完了を待つ（ボタンがenabledになるまで）。
    Headless UIなどで非同期判定処理がある場合に使用。
    """
    from playwright.sync_api import expect
    btn = page.get_by_role("button", name=button_name).first
    expect(btn).to_be_enabled(timeout=timeout)
    return btn


def safe_click(page_or_locator, force: bool = True):
    """
    安全なクリック。
    Headless UI の portal-root などによるポインタインターセプトを
    force=True で回避する。
    """
    page_or_locator.click(force=force)


def take_screenshot(page, result_dir: str, name: str):
    """タイムスタンプ付きスクリーンショット"""
    os.makedirs(result_dir, exist_ok=True)
    path = os.path.join(result_dir, f"{name}.png")
    page.screenshot(path=path)
    return path
```

---

### 3-2. テストコードの生成（AI活用）

#### AIプロンプト設計

テストコード生成をClaude等のAIに依頼する場合、以下の情報をプロンプトに含める。

```
【システムプロンプト】
- ロケーター優先順位ルール
- コード規約（pytest関数ベース、日本語コメント等）
- ハードコードされた wait の禁止（auto-wait機構を使用）
- 出力フォーマット（```python ... ``` ブロック）

【ユーザープロンプト】
- テストシナリオ（YAML/日本語のステップ記述）
- ページスナップショット（アクセシビリティツリー + 要素一覧）
- 対象URL（base_url）
- 特記事項（iframe対応、React対応、確認ダイアログ対応 等）
```

#### AIへの指示テンプレート

```
あなたはPlaywrightのE2Eテストコードを生成するエキスパートです。

## ルール
1. ロケーターの優先順位を守ること:
   get_by_role > get_by_label > get_by_placeholder > get_by_text > get_by_test_id > locator(CSS)
2. get_by_text() を使う場合は exact=True を推奨
3. time.sleep() は使わない。Playwrightの auto-wait を活用
4. 非同期処理の完了待ちには expect().to_be_enabled(timeout=...) を使用
5. ポインタインターセプトの可能性がある場合は click(force=True)

## ページ情報
[ここにアクセシビリティツリーと要素一覧を貼る]

## テストシナリオ
[ここにテスト手順を記述]

## 出力
pytest関数ベースのPlaywrightテストコードを ```python ブロックで出力してください。
```

---

### 3-3. 実行・デバッグ・安定化

#### よくある問題と対処法（トラブルシューティング集）

| # | 症状 | 原因 | 対処法 |
|---|------|------|--------|
| 1 | `strict mode violation` | ロケーターが複数要素にマッチ | `exact=True` を追加、または `.first` / `.nth(N)` で絞り込み |
| 2 | `element is not visible` | 要素はDOMにあるが非表示 | 親要素やコンテナの visibility を確認。Headless UIの場合は子要素で待機 |
| 3 | `element intercepted` | 他の要素がクリックを遮っている | `click(force=True)` で回避。原因はオーバーレイ/portal-root |
| 4 | `timeout waiting for` | 非同期処理が未完了 | timeout値を延長。`expect().to_be_enabled(timeout=30000)` |
| 5 | `page.fill() が反映されない` | React/Vueの仮想DOM更新が走らない | `nativeInputValueSetter` + `dispatchEvent('input')` で直接セット |
| 6 | `iframe内の要素をクリックできない` | Playwrightのクリック先がiframe境界で止まる | `bounding_box()` + `page.mouse.click(x, y)` |
| 7 | `dialog/modalが検出できない` | dialog要素の height=0 | 内部のテキスト要素（h2等）で `wait_for(state="visible")` |
| 8 | `ログイン状態が維持されない` | Cookie/セッション切れ | conftest.py で毎テスト前にログインするか、session scope で共有 |
| 9 | `テスト間の干渉（前のテストの影響）` | 同じデータを使い回し | テストごとに異なるデータを使用 or setup/teardown でリセット |
| 10 | `.env ファイルが読み込めない` | Windows PowerShellの環境変数問題 | ファイルから直接読み込む `load_env()` 関数を使用 |

#### React/Vue フォームの入力対策

```python
def fill_react_input(page, selector: str, value: str):
    """React管理下のinputに値をセットする"""
    page.evaluate(f"""(value) => {{
        const el = document.querySelector('{selector}');
        const nativeSetter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value'
        ).set;
        nativeSetter.call(el, value);
        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
    }}""", value)
```

#### iframe内要素のクリック対策

```python
def click_in_iframe(page, iframe_locator, element_selector: str):
    """iframe内の要素をページ座標でクリック"""
    frame = iframe_locator.content_frame
    element = frame.query_selector(element_selector)
    box = element.bounding_box()
    page.mouse.click(
        box['x'] + box['width'] / 2,
        box['y'] + box['height'] / 2
    )
```

---

### 3-4. 結果の記録とレポート更新

#### テスト結果ログの設計

```python
class TestLogger:
    """テスト結果をログファイル + JSONに記録"""

    def __init__(self, result_dir: str):
        self.result_dir = result_dir
        os.makedirs(result_dir, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_path = os.path.join(result_dir, f"test_{self.timestamp}.log")
        self.results = []
        self._fh = open(self.log_path, "w", encoding="utf-8")

    def log(self, msg: str):
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        self._fh.write(line + "\n")
        self._fh.flush()
        print(line)

    def record(self, tc_id: str, name: str, success: bool, **kwargs):
        self.results.append({
            "tc_id": tc_id, "name": name, "success": success, **kwargs
        })

    def save_json(self):
        import json
        json_path = os.path.join(self.result_dir, f"test_{self.timestamp}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

    def summary(self):
        passed = sum(1 for r in self.results if r["success"])
        failed = len(self.results) - passed
        self.log(f"\n合計: {len(self.results)}件 | PASS: {passed}件 | FAIL: {failed}件")

    def close(self):
        self._fh.close()
```

---

## 付録A: モーダル/ダイアログ分析スクリプト（汎用版）

複数のUIフレームワークに対応した、モーダル内の要素を自動抽出するスクリプト。

```python
def analyze_dialog(page, max_depth: int = 5):
    """
    現在開いているダイアログ/モーダルの構造を分析する。
    対応: 標準ARIA, Material-UI, Headless UI, Ant Design
    """
    return page.evaluate("""(maxDepth) => {
        // ダイアログコンテナの検出（複数フレームワーク対応）
        const selectors = [
            '[role="dialog"]',
            '[role="alertdialog"]',
            '.MuiDialog-root',
            '.MuiModal-root',
            '[id*="headlessui-dialog"]',
            '.ant-modal-wrap',
            '.modal.show',
        ];

        let container = null;
        for (const sel of selectors) {
            container = document.querySelector(sel);
            if (container) break;
        }
        if (!container) return { found: false };

        // ボタン一覧
        const buttons = [];
        container.querySelectorAll('button').forEach(b => {
            const r = b.getBoundingClientRect();
            if (r.width > 0 && r.height > 0) {
                buttons.push({
                    text: b.innerText.trim(),
                    disabled: b.disabled,
                    ariaLabel: b.getAttribute('aria-label') || '',
                    rect: { x: Math.round(r.x), y: Math.round(r.y),
                            w: Math.round(r.width), h: Math.round(r.height) }
                });
            }
        });

        // フォーム要素
        const inputs = [];
        container.querySelectorAll('input, select, textarea').forEach(el => {
            inputs.push({
                tag: el.tagName.toLowerCase(),
                type: el.type || '',
                name: el.name || '',
                placeholder: el.placeholder || '',
                disabled: el.disabled,
                required: el.required,
                accept: el.accept || '',
                multiple: el.multiple || false,
                value: el.value?.substring(0, 100) || '',
            });
        });

        // テーブル
        const tables = [];
        container.querySelectorAll('table').forEach(t => {
            const headers = Array.from(t.querySelectorAll('th'))
                .map(th => th.innerText.trim());
            const rows = [];
            t.querySelectorAll('tbody tr').forEach(tr => {
                const cells = Array.from(tr.querySelectorAll('td'))
                    .map(td => td.innerText.trim().substring(0, 100));
                rows.push(cells);
            });
            tables.push({ headers, rows });
        });

        // DOMツリー
        function tree(el, depth) {
            if (depth > maxDepth) return '';
            const tag = el.tagName.toLowerCase();
            const role = el.getAttribute('role') ? ` role="${el.getAttribute('role')}"` : '';
            const cls = el.className ? ` class="${String(el.className).substring(0, 60)}"` : '';
            const text = el.childNodes.length === 1 && el.childNodes[0].nodeType === 3
                ? ` "${(el.textContent || '').trim().substring(0, 60)}"` : '';
            let result = '  '.repeat(depth) + `<${tag}${role}${cls}>${text}\n`;
            for (const child of el.children) {
                result += tree(child, depth + 1);
            }
            return result;
        }

        return {
            found: true,
            title: container.querySelector('h1, h2, h3')?.textContent?.trim() || '',
            text: container.innerText.substring(0, 2000),
            buttons,
            inputs,
            tables,
            domTree: tree(container, 0).substring(0, 5000),
        };
    }""", max_depth)
```

---

## 付録B: チェックリスト

### 新しいシステムの分析を始めるときのチェックリスト

```
□ Phase 1: 画面分析
  □ 対象URLにアクセスし、ログイン可能か確認
  □ アクセシビリティツリーを取得
  □ スクリーンショットを撮影（初期状態）
  □ ゾーニング（ヘッダー/サイドバー/メイン/フッター）を記録
  □ インタラクティブ要素を棚卸し（上限200件）
  □ 各要素の推奨ロケーターを決定
  □ UIフレームワークを検出
  □ モーダル/ダイアログがあれば構造を分析
  □ ロケーター品質を評価（✅ / ⚠️）
  □ 分析レポートを作成

□ Phase 2: テスト設計
  □ 操作フロー（ユーザージャーニー）を洗い出し
  □ 各フローのステップをタイミング付きで記録
  □ 正常系テストケースを設計
  □ 異常系・境界値テストケースを設計
  □ テストデータを準備（生成スクリプト含む）

□ Phase 3: テスト実装
  □ conftest.py を作成（ログイン・コンテキスト設定）
  □ 共通ヘルパー関数を作成
  □ 正常系テスト1本を作成して基盤を安定させる
  □ 残りのテストケースを実装
  □ 全テストPASSを確認
  □ 結果をレポートに反映
```

---

## 付録C: 実績データ（TOKIUM）

本ガイドの元となった実績:

### C.1 テストスイート一覧

| # | 対象画面 | テストファイル | テスト数 | 方式 | 主な技術課題 |
|---|---------|-------------|---------|------|------------|
| 1 | ログイン画面 | (別リポジトリ) | 5 PASS | A | exact=True、ネスト要素 |
| 2 | 請求書一覧画面 | test_invoice_list.py | 17 PASS | A | 検索フォーム、テーブル操作、チェックボックス |
| 3 | 請求書詳細画面 | test_invoice_detail.py | 15 PASS | A | iframe、確認ダイアログ、ページ送り |
| 4 | 請求書作成（CSV） | test_invoice_creation.py | 5 PASS | B | CSVインポート、クロスオリジンiframe、BG処理待ち |
| 5 | 一括添付・正常系 | test_bulk_attachment_normal.py | 4 PASS | B | Headless UIモーダル、非同期判定 |
| 6 | 一括添付・異常系 | test_bulk_attachment_error.py | 3 PASS | B | ファイルサイズ上限、件数上限、境界値 |
| 7 | 一括添付・DOM構造 | test_bulk_attachment_dom.py | 8 PASS | B | ステップウィザード構造、role属性検証 |
| 8 | 一括添付・エッジケース | test_bulk_attachment_edge.py | 4 PASS | B | 0バイトファイル、重複ファイル名、混在アップロード |
| 9 | 一括添付・ファイル名 | test_bulk_attachment_filename.py | 1 PASS | B | 全角/半角カナ、長大ファイル名(200文字超)、各種拡張子 |
| 10 | 一括添付・複数請求書 | test_bulk_attachment_multi.py | 3 PASS | B | 複数請求書選択、一括添付フロー |
| 11 | 一括添付・ナビゲーション | test_bulk_attachment_navigation.py | 10 PASS | B | ステップ間遷移、戻る操作、モーダル開閉 |
| 12 | 一括添付・既存ファイル | test_bulk_attachment_existing.py | 5 PASS | B | タブ切替、既存ファイル選択、検索フィルタ |

**合計: 80テスト関数（方式A: 32、方式B: 48）**

> 方式A = pytest + conftest.py（logged_in_page共有）、方式B = 独立スクリプト（TC-ID別エビデンス管理）

### C.2 テスト分類別の内訳

| カテゴリ | テスト数 | 説明 |
|---------|---------|------|
| 画面表示・基本操作 | 32 | 一覧17 + 詳細15（方式A） |
| CSVインポートフロー | 5 | レイアウト選択→アップロード→マッピング→確認→メモ |
| 一括添付・正常系 | 4 | 単一/複数ファイル、各種形式、日本語ファイル名 |
| 一括添付・異常系/境界値 | 3 | サイズ超過、件数超過、合計サイズ超過 |
| 一括添付・DOM/UI構造 | 8 | role属性、ステップ構造、input属性、状態遷移 |
| 一括添付・エッジケース | 4 | 0バイト、混在、重複名、削除操作 |
| 一括添付・ファイル名/拡張子 | 1 | 半角/全角/カナ/長大名/各種拡張子（内部で複数パターン） |
| 一括添付・複数請求書 | 3 | 2件/5件一括、複数ファイル×複数請求書 |
| 一括添付・ナビゲーション | 10 | 戻る、タブ切替、閉じる、インジケータ |
| 一括添付・既存ファイル選択 | 5 | タブ切替、チェックボックス選択、フルフロー |

### C.3 エビデンス管理

- **方式A**: pytestの標準出力（PASS/FAIL）で管理
- **方式B**: `test_results/TC-{ID}/` 配下にスクリーンショット + JSON/LOGファイル
  - 実績: 30以上のTC別フォルダ、60以上のログファイルペア
  - アーカイブ: `test_results/_archive/` に過去実行分を日付別保存
