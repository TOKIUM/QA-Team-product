# E2Eテスト自動化 汎用モデル ― 他システム適用ガイド

**作成日**: 2026-02-17
**ベースプロジェクト**: TOKIUM 請求書発行「共通添付ファイルの一括添付」機能
**実績**: 全自動テスト全PASS / 80手動テスト設計済み / テストID別動画証跡管理（TOKIUM実装例）

---

## 0. このドキュメントの目的

本プロジェクトで確立した **「AIでテスト設計→テストコード生成→Playwrightで高速実行→テストID別動画証跡管理」** のワークフローを、**他の任意のWebシステム**に適用するための手順・テンプレート・知見を整理する。

### テンプレート実体ファイル

本ドキュメント内のテンプレートは `templates/` フォルダに実体ファイルとして配置済み。新システム適用時はコピーして使用する。

| ファイル | 用途 | 対応セクション |
|---------|------|-------------|
| `templates/CLAUDE_TEMPLATE.md` | セッション管理（CLAUDE.md） | §1.5 |
| `templates/conftest_template.py` | 方式A: pytest共通fixture | §1.6 |
| `templates/config_template.py` | 方式A: 設定ファイル | §1.6 |
| `templates/pytest.ini` | 方式A: pytest設定 | §1.6 |
| `templates/test_template_standalone.py` | 方式B: 独立スクリプト形式 | §5-2 |
| `templates/.env.example` | 環境変数サンプル | §8 Step 0 |

> 詳細は `templates/README.md` を参照。

> **重要**: `templates/conftest_template.py` は基本版（動画録画なし）。実際のプロジェクトでは動画録画（`record_video_dir`）、遅延コピー（`_pending_video_copies`）、テストIDマッピング（`TH_ID_MAP` + `_set_th_id` fixture）を追加する。詳細は §1.7「方式A/B 共通: 動画録画アーキテクチャ」を参照。

---

## 1. 全体アーキテクチャ（6フェーズ）

```
Phase 1:   画面分析        ← AI（Claude）がブラウザで対象画面を操作・DOM解析
    ↓
Phase 1.5: フォルダ構成決定 ← AIが分析結果からフォルダ階層を提案 → 人間が承認
    ↓
Phase 2:   テスト設計      ← AI が TEST_DESIGN.md / FULL_TEST_CHECKLIST.md を生成
    ↓
Phase 3:   コード生成      ← AI が Playwright テストコード(.py)を生成
    ↓
Phase 4:   テスト実行      ← Playwright が高速実行（AIなし・秒単位）
    ↓
Phase 5:   証跡管理        ← テストIDフォルダに動画(.webm)を自動整理、チェックリストと紐付け
```

### なぜこの方式か？

| 方式 | 速度 | コスト | 再現性 |
|------|------|--------|--------|
| 毎回AIがブラウザ操作 | 遅い（30秒/テスト） | 高い（毎回API呼出） | 低い |
| **AI生成→Playwright実行** | **速い（1.5秒/テスト）** | **低い（生成時のみ）** | **高い** |

---

## 1.5. CLAUDE.md テンプレート（必須）

新システムのプロジェクトルートに必ず配置する。セッション間のコンテキスト引き継ぎと、クラッシュ防止のためのルールを含む。

```markdown
# {システム名} E2Eテストプロジェクト

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
- 動画証跡（.webm）やスクリーンショット（.png）は指示がない限り読み込まない。

## プロジェクト概要
{システム名}のE2Eテスト自動化。Playwright + Python (pytest) を使用。

- **対象URL**: `{BASE_URL}`
- **認証**: 環境変数 `TEST_EMAIL` / `TEST_PASSWORD`

## フォルダ構成
（プロジェクト作成後に記載）

## 画面構造（要約）
（フェーズ1完了後に記載）

## 技術的制約・知見
（作業中に判明した事項を都度追記）

## 注意事項
（ロケーターの注意点、重複ラベル等を都度追記）
```

---

## 1.6. テストコード方式の使い分け

本プロジェクトでは2つのテストコード方式を併用している。新システムでも用途に応じて使い分けること。

### 方式A: pytest + conftest.py 形式

```python
# conftest.py の logged_in_page fixture を使用
def test_一覧ページの表示確認(logged_in_page: Page):
    page = logged_in_page
    page.goto(f"{BASE_URL}/invoices")
    expect(page.get_by_role("heading", name="請求書")).to_be_visible()
```

**適用場面**:
- 画面の表示確認・要素存在確認（一覧画面17テスト、詳細画面15テスト）
- 検索・フィルタ・ナビゲーションなどの基本操作テスト
- テスト間の独立性が高い（各テストが1操作で完結する）

**メリット**: `pytest -v` で一括実行可能、テスト結果がpytest標準で表示される
**デメリット**: conftest.pyの追加実装が必要（テストIDマッピング、遅延動画コピー等。詳細は§1.7参照）

### 方式B: 独立スクリプト形式（`python test_xxx.py` で実行）

```python
# sync_playwright() を直接使用、storage_state + 動画録画でテストID別証跡管理
def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # ...
        result = test_tc_01(page)
```

**適用場面**:
- 複数ステップのウィザード操作（共通添付ファイル一括添付：55テスト）
- テストID別の動画証跡が必要な場合
- 認証状態をstorage_stateで保存・再利用する場合
- 非同期処理の待機が複雑な場合
- テスト間で状態を引き継ぐ必要がある場合（同一ブラウザセッション）

**メリット**: テストIDフォルダ管理、ログ/JSON出力、動画録画自動保存、storage_stateで認証分離
**デメリット**: pytest統合されない、独自の実行管理が必要

### 使い分け判断フロー

```
テストの目的は？
  ├─ 画面の表示確認・基本操作 → 方式A（pytest + conftest.py）
  ├─ 複数ステップの業務フロー → 方式B（独立スクリプト）
  └─ 迷ったら？
       ├─ 2フェーズ認証（storage_state）が必要 → 方式B
       ├─ テスト間で状態引き継ぎが必要 → 方式B
       └─ 上記不要 → 方式A（conftest.pyで動画録画・テストID管理対応済み）
```

---

## 1.7. 方式A/B 共通: 動画録画アーキテクチャ

現在の実装では方式A・方式Bともに**動画録画(.webm)**を証跡として使用している（スクリーンショットは使用していない）。

### 重要: 遅延コピーパターン（Delayed Video Copy）

Playwrightの動画ファイルはpage/contextが閉じるまで空ファイルのままである。そのため、テスト実行中は動画パスだけを記録し、セッション終了後に一括コピーする方式を採用している。

**方式A（conftest.py）での実装:**

```python
_pending_video_copies = []  # グローバルリスト

# pytest_runtest_makereportフック内: パスだけ記録
video_path = page.video.path()
dest_path = os.path.join(result_dir, f"{th_id}.webm")
_pending_video_copies.append((video_path, dest_path))

# pytest_sessionfinish内: 全動画を一括コピー
for src, dest in _pending_video_copies:
    if os.path.exists(src) and os.path.getsize(src) > 0:
        shutil.copy2(src, dest)
```

**方式B（main()関数）での実装:**

```python
pending_video_copies = []

# テストループ内のfinally: パスだけ記録
video_src = page.video.path()
pending_video_copies.append((str(video_src), dest_path))
page.close()

# context.close()後: 全動画を一括コピー
context.close()
for src, dest in pending_video_copies:
    shutil.copy2(src, dest)
```

### 方式A: テストID（TH-ID）マッピング

pytest方式では、テスト関数名からテストIDへのマッピングをfixtureで自動付与する:

```python
TH_ID_MAP = {
    "test_一覧ページの表示確認": "TH-IL01",
    "test_検索フォームの表示確認": "TH-IL03",
    # ...
}

@pytest.fixture(autouse=True)
def _set_th_id(request):
    """テスト関数名からTH-IDを自動付与"""
    base_name = request.node.name.split("[")[0]  # [chromium]等のパラメータを除去
    th_id = TH_ID_MAP.get(base_name)
    if th_id:
        request.node._th_id = th_id
```

### 方式B: storage_stateパターン（2フェーズ認証）

独立スクリプト方式では、ログインと動画録画を分離するためにstorage_stateを使用する:

```python
storage_state_path = os.path.join(RESULT_DIR, "_auth_state.json")

# Phase 1: ログイン + 認証状態保存（動画なし）
login_context = browser.new_context(
    viewport={"width": 1280, "height": 720},
    locale="ja-JP", timezone_id="Asia/Tokyo",
)
login_page = login_context.new_page()
login(login_page, email, password)
login_context.storage_state(path=storage_state_path)
login_context.close()

# Phase 2: 認証再利用 + 動画録画
context = browser.new_context(
    storage_state=storage_state_path,
    record_video_dir=VIDEOS_TMP_DIR,
    record_video_size={"width": 1280, "height": 720},
)
```

これにより、ログイン操作が動画に含まれず、テスト操作のみが録画される。

---

## 2. ディレクトリ構成テンプレート

```
プロジェクトルート/
├── {画面名}/                          ← 画面（サイドバーのタブ）ごとにフォルダ分け
│   ├── {機能名}/                      ← 機能単位でサブフォルダ
│   │   ├── TEST_DESIGN.md            ← テスト設計書（Phase 2 成果物）
│   │   ├── FULL_TEST_CHECKLIST.md    ← テスト結果一覧（Phase 2 + 5 成果物）
│   │   ├── UI_TEST_DESIGN.md         ← 手動UIテスト設計（オプション）
│   │   │
│   │   ├── test_{機能}_{カテゴリ}.py  ← テストコード（Phase 3 成果物）
│   │   ├── test_{機能}_{カテゴリ}.py  ← カテゴリ別に分割
│   │   ├── ...
│   │   │
│   │   ├── {テストデータフォルダ}/     ← テスト用ファイル
│   │   │   ├── create_{data}.py      ← テストデータ生成スクリプト
│   │   │   └── *.pdf, *.png, ...     ← 生成済みテストデータ
│   │   │
│   │   ├── test_results/              ← テスト結果（Phase 4 + 5 成果物）
│   │   │   ├── _logs/                ← ログ(.log)・JSON(.json)集約
│   │   │   ├── _videos_tmp/          ← 動画一時フォルダ（実行後に自動削除）
│   │   │   ├── _archive/             ← 旧ファイル退避
│   │   │   ├── TH-01/               ← テストIDごとの動画証跡（例: TH-01.webm）
│   │   │   ├── TH-02/               ← ※プレフィックスはプロジェクトに応じて変更
│   │   │   └── ...
│   │   │
│   │   ├── _auth_state.json          ← 方式B: storage_state一時ファイル（実行後削除）
│   │   │
│   │   └── migrate_test_results.py   ← 既存結果の移行用（初回のみ）
│   │
│   └── ログイン/
│       └── .env                       ← 認証情報（共有）
│
├── HANDOVER_REPORT.md                 ← プロジェクト全体管理
└── MEMORY.md                          ← AI用プロジェクトメモリ
```

---

## 3. Phase 1: 画面分析（AIが実施）

### 3-1. 入力
- 対象画面のURL
- ログイン情報

### 3-2. AIへの指示テンプレート

```
以下の画面を分析してください。

【対象URL】 https://example.com/target-page
【対象機能】 {機能名}（例: ファイルアップロードモーダル）
【ログイン情報】 .envファイル参照

分析してほしいこと:
1. 画面フロー（ステップ・遷移図）
2. DOM構造（主要要素のセレクタ、role属性、aria属性）
3. バリデーション仕様（フロント/サーバー、エラーメッセージ）
4. 制限値（ファイルサイズ、件数、文字数など）
5. ボタン状態変化（disabled/enabled条件）
6. 非同期処理の有無（ローディング、ポーリングなど）

結果を ANALYSIS_REPORT.md として出力してください。
```

### 3-3. 出力
- `ANALYSIS_REPORT.md`（画面のDOM構造・遷移・仕様が記録される）

### 3-4. 知見（TOKIUM固有→汎用化）

| TOKIUM固有の知見 | 汎用化したルール |
|-----------------|----------------|
| `exact=True` 必須（部分一致問題） | **ボタン特定は `exact=True` をデフォルトにする** |
| ネスト要素（`<a>`内の`<button>`） | **クリック対象は最外周の操作可能要素を特定** |
| iframe内ボタン | **`bounding_box()` + `page.mouse.click()` が最も確実** |
| 確認ダイアログ | **ウィザード形式は各ステップのボタンクリックを明示的に待機** |
| React検索フォーム | **`nativeInputValueSetter` + `form.requestSubmit()` 必須** |

---

## 3.5. Phase 1.5: フォルダ構成決定（AI提案 → 人間承認）

### 3.5-1. 目的

Phase 1 の画面分析結果から、テストコード・設計書を配置する**フォルダ階層**を決定する。

フォルダ構成は対象システムの画面遷移構造を反映すべきだが、URL構造だけでは正確に判断できない場合が多い。そのため **AIが提案→人間が承認** のフローで決定する。

### 3.5-2. 判断に使う情報（Phase 1 の分析結果から）

| 情報ソース | 確認ポイント | 例 |
|-----------|------------|-----|
| サイドバー | トップレベルメニュー項目 | 請求書、取引先、帳票レイアウト |
| パンくず | 画面の階層位置 | 請求書 > PDFを取り込む > ファイル分割 |
| URL構造 | パスの階層 | `/invoices/pdf-organizer/separation` |
| 画面上のアクションボタン | どの画面から遷移するか | 「請求書作成」ボタン → 請求書作成画面 |
| ドロップダウン/メニュー | 「その他の操作」等のサブ機能 | その他の操作 > 共通添付ファイル一括添付 |

### 3.5-3. フォルダ決定フロー

```
Phase 1 完了（ANALYSIS_REPORT.md 作成済み）
    ↓
Step 1: AIが上記5つの情報ソースを確認
    ↓
Step 2: AIがパターンカタログ（付録A）を参照して階層を推定
    ↓
Step 3: AIがフォルダ階層をツリー図で提案
    ↓
Step 4: 人間が承認 or 修正指示
    ↓
Step 5: フォルダ作成 + テンプレート配置（CLAUDE.md, conftest.py 等）
```

### 3.5-4. AIへの指示テンプレート

```
ANALYSIS_REPORT.md の分析結果に基づいて、テストファイルのフォルダ配置を提案してください。

【判断基準】
- サイドバーのメニュー構造
- パンくずの階層
- URL構造
- 画面遷移（どのボタン/リンクから到達するか）
- MODEL_EXPORT.md 付録Aのパターンカタログ

【出力形式】
以下のツリー図で提案してください:

```
プロジェクトルート/
├── {提案フォルダ}/
│   └── {提案サブフォルダ}/
│       ├── CLAUDE.md
│       ├── conftest.py
│       ├── pytest.ini
│       └── test_results/
```

【判断根拠】
パターンカタログのどのパターンに該当するか、またはどのような根拠で判断したかを説明してください。
```

### 3.5-5. 出力物

| ファイル | 内容 | 配置タイミング |
|---------|------|-------------|
| フォルダ一式 | 承認された階層構造のディレクトリ | 承認直後 |
| `CLAUDE.md` | テンプレートからコピー（§1.5参照） | フォルダ作成と同時 |
| `conftest.py` | テンプレートからコピー、.envパスを調整 | フォルダ作成と同時 |
| `pytest.ini` | テンプレートからコピー | フォルダ作成と同時 |
| `test_results/` | テスト結果フォルダ（空） | フォルダ作成と同時 |

### 3.5-6. .envパスの自動調整

フォルダの深さに応じて、conftest.py 内の .env 参照パスを調整する:

```python
# 例: TH/請求書/請求書一覧/ からログイン/.env を参照（深さ2）
env_path = Path(__file__).resolve().parent.parent.parent / "ログイン" / ".env"

# 例: TH/請求書/請求書一覧/請求書作成/PDFを取り込む/ から参照（深さ4）
env_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "ログイン" / ".env"
```

**ルール**: `TH/` からの階層の深さ = `.parent` の個数（+1 for ファイル自身）

### 3.5-7. 学習・改善サイクル

フォルダ構成の決定実績は**付録A: フォルダ構成パターンカタログ**に蓄積する。新しい画面を追加するたびに:

1. 使用したパターン or 新規パターンをカタログに追記
2. 判断根拠を記録
3. 将来的にAIの提案精度が上がり、人間の承認がほぼ自動化されることを目指す

---

## 4. Phase 2: テスト設計（AIが生成）

### 4-1. AIへの指示テンプレート

```
ANALYSIS_REPORT.md の分析結果に基づいて、テスト設計を行ってください。

【出力ファイル】
1. TEST_DESIGN.md — テスト設計書
2. FULL_TEST_CHECKLIST.md — テストチェックリスト

【テストカテゴリの分類ルール】
以下のカテゴリで網羅的にテストケースを設計してください:

A. 正常系: 基本フロー（ハッピーパス）
B. 異常系: フロントバリデーション
C. 異常系: サーバーバリデーション
D. 境界値: 上限ギリギリの値
E. 入力バリエーション: 文字種（半角/全角/記号/日本語）
F. 拡張子・形式バリエーション
G. 複数データ一括操作
H. ナビゲーション: 画面遷移・戻る操作
I. モーダル/ダイアログ: 開閉操作
J. DOM/エレメント: 属性・状態検証
K. エッジケース: 0件/空/重複/削除
L. 機能固有のカテゴリ（あれば）
M. UI/UX: 目視確認項目（手動テスト）

【TC-ID命名規則】
- 正常系: TC-01, TC-02, ...
- 異常系: TC-E01, TC-E02, ...
- ファイル名: TC-F01, ...
- 拡張子: TC-X01, ...
- 複数: TC-M01, ...
- ナビ: TC-N01, ...
- モーダル閉: TC-C01, ...
- DOM: TC-D01, ...
- エッジ: TC-V01, ...
- 既存タブ: TC-T01, ...
- UI手動: UI-01, UI-02, ...

【FULL_TEST_CHECKLIST.md の書式】

先頭にサマリーテーブル（カテゴリ×PASS/FAIL/未実施）を記載し、
各カテゴリのテーブルには以下の列を含めること:

| TC-ID | 画面 | 確認すること | 確認対象 | 詳細1 | 詳細2 | テスト実行手順 | 期待値 | 結果 | 実行日 | エビデンス |
```

### 4-2. TC-ID命名規則（推奨）

> **注意**: 以下はTC-を汎用デフォルトプレフィックスとした命名規則テンプレートである。
> 実際のプロジェクトではプロジェクト固有のプレフィックスに置き換える。
> 例: TOKIUMプロジェクトでは `TH-` プレフィックスを使用（TH = TOKIUM Hakkousho）。
> プレフィックスの決定は Phase 1.5 のフォルダ構成決定時に行う。

```
{プレフィックス}-{連番}

プレフィックス例:
  TC     : 正常系メイン
  TC-E   : 異常系/エラー
  TC-F   : ファイル名系
  TC-X   : 拡張子/形式系
  TC-M   : 複数/一括系
  TC-N   : ナビゲーション系
  TC-C   : モーダル閉じる系
  TC-D   : DOM/属性検証系
  TC-V   : バリデーション追加系
  TC-T   : タブ/切替系
  UI     : 手動UI確認
```

### 4-3. 出力物

| ファイル | 内容 | 用途 |
|---------|------|------|
| `TEST_DESIGN.md` | 機能仕様+テストカテゴリ+全テストケース詳細 | テスト設計の根拠 |
| `FULL_TEST_CHECKLIST.md` | サマリー+全テスト一覧（結果列付き） | テスト実行管理・証跡台帳 |
| `UI_TEST_DESIGN.md` | 手動UI確認チェックリスト | デザインQA |

---

## 5. Phase 3: テストコード生成（AIが生成）

### 5-1. テストコード分割方針

```
1ファイル = 1テストカテゴリ（3〜12テスト程度）
```

| ファイル名パターン | 例 | テスト数目安 |
|-------------------|-----|------------|
| `test_{機能}_normal.py` | test_bulk_attachment_normal.py | 3〜5 |
| `test_{機能}_error.py` | test_bulk_attachment_error.py | 5〜10 |
| `test_{機能}_dom.py` | test_bulk_attachment_dom.py | 5〜10 |
| `test_{機能}_navigation.py` | test_bulk_attachment_navigation.py | 5〜10 |
| `test_{機能}_edge.py` | test_bulk_attachment_edge.py | 3〜5 |

### 5-2. テストコード必須テンプレート

```python
"""
{機能名} - {カテゴリ名}テスト

テスト内容:
  TC-XX: {テスト概要}
  TC-XX: {テスト概要}
  ...

前提条件:
  - ログイン情報は {相対パス}/.env に設定済み
  - テスト用ファイルは {フォルダ名}/ に配置済み
"""

import os
import sys
import json
import shutil
from datetime import datetime
from playwright.sync_api import sync_playwright, expect

# ===== パス設定 =====
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "https://example.com"  # ← 対象システムのURLに変更
RESULT_DIR = os.path.join(SCRIPT_DIR, "test_results")

# ===== ログ設定 =====
os.makedirs(RESULT_DIR, exist_ok=True)
LOGS_DIR = os.path.join(RESULT_DIR, "_logs")
os.makedirs(LOGS_DIR, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOGS_DIR, f"test_{カテゴリ}_{timestamp}.log")
log_fh = None


def get_th_result_dir(th_id: str) -> str:
    """テストIDごとの証跡（動画）保存フォルダを作成して返す
    ※ 関数名・引数名はプロジェクトプレフィックスに合わせてリネーム可（例: get_tc_result_dir）
    """
    d = os.path.join(RESULT_DIR, th_id)
    os.makedirs(d, exist_ok=True)
    return d


def log(msg: str):
    """コンソール + ファイルに出力"""
    global log_fh
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    if log_fh:
        log_fh.write(line + "\n")
        log_fh.flush()
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.encode("ascii", "replace").decode())


def load_env() -> dict:
    """ログイン情報を .env からロード"""
    env_path = os.path.normpath(
        os.path.join(SCRIPT_DIR, "..", "..", "..", "ログイン", ".env")
    )
    vals = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    vals[k.strip()] = v.strip()
    return vals


def login(page, email: str, password: str):
    """共通ログイン処理"""
    log("ログイン開始...")
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")
    # ← ここは対象システムに合わせて書き換え
    page.get_by_role("button", name="ログイン", exact=True).wait_for(state="visible")
    page.get_by_label("メールアドレス").fill(email)
    page.get_by_label("パスワード").fill(password)
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="ログイン", exact=True).click()
    try:
        page.wait_for_url("**/dashboard**", timeout=60000)
    except Exception:
        for _ in range(30):
            if "/login" not in page.url:
                break
            page.wait_for_timeout(1000)
    page.wait_for_load_state("networkidle")
    log(f"ログイン完了: {page.url}")
    if "/login" in page.url:
        raise RuntimeError(f"ログイン失敗: URL={page.url}")


# ===== テスト関数テンプレート =====
def test_tc_xx(page):
    """TC-XX: テスト概要"""
    tc_id = "TC-XX"
    log(f"\n{'='*60}")
    log(f"{tc_id}: テスト概要")
    log(f"{'='*60}")

    try:
        # --- テスト操作 ---
        # ※ 動画録画が有効な場合、操作は自動的に録画される
        # ※ 特定ステップの静止画が必要な場合のみ page.screenshot() を追加

        # --- 検証 ---
        # assert / expect で期待値チェック

        log(f"結果: PASS")
        return {"success": True}

    except Exception as e:
        log(f"結果: FAIL ({e})")
        return {"success": False, "error": str(e)}


# ===== メイン =====
def main():
    global log_fh
    log_fh = open(LOG_FILE, "w", encoding="utf-8")

    env = load_env()
    email = env.get("TEST_EMAIL")
    password = env.get("TEST_PASSWORD")

    if not email or not password:
        log("ERROR: TEST_EMAIL / TEST_PASSWORD が .env に設定されていません")
        log_fh.close()
        return

    log(f"テスト開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # テストケース定義: (テストID, テスト名, 関数)
    tests = [
        ("TC-XX", "テスト概要", test_tc_xx),
    ]

    results = []
    pending_video_copies = []
    storage_state_path = os.path.join(RESULT_DIR, "_auth_state.json")
    VIDEOS_TMP_DIR = os.path.join(RESULT_DIR, "_videos_tmp")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # === Phase 1: ログイン + 認証状態保存（動画なし） ===
        login_context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
        )
        login_context.set_default_timeout(30000)
        login_page = login_context.new_page()
        login(login_page, email, password)
        login_context.storage_state(path=storage_state_path)
        login_context.close()
        log("認証状態を保存しました")

        # === Phase 2: 動画録画付きコンテキストでテスト実行 ===
        os.makedirs(VIDEOS_TMP_DIR, exist_ok=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
            storage_state=storage_state_path,
            record_video_dir=VIDEOS_TMP_DIR,
            record_video_size={"width": 1280, "height": 720},
        )
        context.set_default_timeout(30000)

        for tc_id, tc_name, tc_func in tests:
            page = context.new_page()
            log(f"\n{'#'*60}")
            log(f"# {tc_id}: {tc_name}")
            log(f"{'#'*60}")

            try:
                page.goto(f"{BASE_URL}/target-page")
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(2000)

                result = tc_func(page)
                result["tc_id"] = tc_id
                result["tc_name"] = tc_name
                results.append(result)

                status = "PASS" if result["success"] else "FAIL"
                log(f"\n結果: {status}")

            except Exception as e:
                log(f"\n結果: FAIL (例外: {e})")
                results.append({
                    "tc_id": tc_id, "tc_name": tc_name,
                    "success": False, "error": str(e),
                })

            finally:
                # 動画パスを記録（遅延コピー用）
                try:
                    video = page.video
                    if video:
                        video_src = video.path()
                        if video_src:
                            dest_dir = get_th_result_dir(tc_id)
                            dest_path = os.path.join(dest_dir, f"{tc_id}.webm")
                            pending_video_copies.append((str(video_src), dest_path))
                except Exception:
                    pass
                page.close()

        context.close()

        # === Phase 3: 遅延コピー（動画確定後にコピー） ===
        for src, dest in pending_video_copies:
            try:
                if os.path.exists(src) and os.path.getsize(src) > 0:
                    shutil.copy2(src, dest)
                    log(f"  🎬 動画保存: {dest}")
            except Exception as e:
                log(f"  🎬 動画保存失敗: {e}")

        # クリーンアップ
        if os.path.exists(VIDEOS_TMP_DIR):
            try: shutil.rmtree(VIDEOS_TMP_DIR)
            except: pass
        if os.path.exists(storage_state_path):
            try: os.remove(storage_state_path)
            except: pass

        browser.close()

    # サマリー
    pass_count = sum(1 for r in results if r["success"])
    fail_count = len(results) - pass_count
    log(f"\n合計: {len(results)}件 | PASS: {pass_count}件 | FAIL: {fail_count}件")

    # JSON結果出力
    json_path = os.path.join(LOGS_DIR, f"test_{カテゴリ}_{timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    log_fh.close()
    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()
```

### 5-3. 証跡ファイル命名規則

#### 動画録画（推奨方式）

```
{テストID}/{テストID}.webm

例:
  TH-01/TH-01.webm        ← テストTH-01の操作動画
  TH-E02/TH-E02.webm      ← テストTH-E02の操作動画
```

> 動画はPlaywrightの `record_video_dir` で自動録画される。1テスト=1動画ファイル。

#### スクリーンショット（必要な場合のみ）

```
{テストID}/{テストID}_{操作ステップ}.png

例:
  TH-01/th-01_step1.png        ← Step1 のスクリーンショット
  TH-01/th-01_error.png        ← エラー発生時（例外キャッチ）
```

> スクリーンショットは動画録画と併用可能。特定の画面状態を静止画で残したい場合に使用する。

### 5-4. ロケーター優先順位

```
1. get_by_role()         ← 最優先（アクセシビリティベース）
2. get_by_label()        ← フォーム要素
3. get_by_placeholder()  ← 入力フィールド
4. get_by_text()         ← テキストで特定
5. locator(CSS)          ← 最終手段
```

**重要**: `exact=True` をデフォルトで付与（部分一致による誤クリック防止）

---

## 6. Phase 4: テスト実行

### 6-1. 実行コマンド

```powershell
# 単体実行
python test_{機能}_{カテゴリ}.py

# 全カテゴリ一括実行（PowerShell）
$files = Get-ChildItem -Filter "test_*.py" | Sort-Object Name
foreach ($f in $files) {
    Write-Host "=== $($f.Name) ===" -ForegroundColor Cyan
    python $f.FullName
    Write-Host ""
}
```

### 6-2. 出力先

```
test_results/
  _logs/
    test_normal_20260217_220720.log    ← 実行ログ
    test_normal_20260217_220720.json   ← JSON結果
  _videos_tmp/                         ← 動画一時フォルダ（実行後に自動削除）
  TH-01/
    TH-01.webm                         ← テスト操作動画（証跡）
  TH-02/
    TH-02.webm
  ...
```

### 6-3. 並列実行の注意

- 同一アカウントで複数ブラウザが同時操作すると**セッション競合**が発生する
- **同一テストファイル内は直列実行**（1ブラウザで順次実行）
- **異なるテストファイルは並列実行可能**（ただし同一アカウントを使う場合は注意）

---

## 7. Phase 5: 証跡管理（テストIDフォルダ構造）

### 7-1. フォルダ構造の自動生成

テストコード内の `get_th_result_dir(th_id)` が自動的にフォルダを作成する。

```python
def get_th_result_dir(th_id: str) -> str:
    """テストIDごとの証跡（動画）保存フォルダを作成して返す
    ※ 関数名はプロジェクトプレフィックスに合わせて変更
    """
    d = os.path.join(RESULT_DIR, th_id)
    os.makedirs(d, exist_ok=True)
    return d
```

### 7-2. FULL_TEST_CHECKLIST.md との紐付け

チェックリストの「エビデンス」列に相対リンクを設定:

```markdown
| TH-01 | ... | PASS | 2026-02-17 | [動画](test_results/TH-01/TH-01.webm) |
| TH-02 | ... | PASS | 2026-02-17 | [動画](test_results/TH-02/TH-02.webm) |
```

### 7-3. 既存結果の移行（migrate_test_results.py テンプレート）

新規プロジェクトでは不要。既に結果がフラットに存在する場合のみ使用:

```python
TC_FILE_MAPPING = {
    "TC-01": ["tc01_step1.png", "tc01_step2.png", ...],
    "TC-02": ["tc02_step1.png", "tc02_step2.png", ...],
}
```

---

## 8. 他システムへの適用手順（ステップバイステップ）

### Step 0: 環境準備（10分）

```powershell
# 1. Python + Playwright インストール
pip install playwright
playwright install chromium

# 2. .env 作成（ログイン情報）※ フォルダ作成は Step 1.5 で実施
# TEST_EMAIL=your-email@example.com
# TEST_PASSWORD=your-password
```

### Step 1: 画面分析（AIに依頼 / 15〜30分）

```
AIへの指示:
「{URL} の {機能名} 画面を分析して、ANALYSIS_REPORT.md を作成してください」
```

**AIが行うこと**:
- ブラウザで対象画面にアクセス
- DOM構造を解析（セレクタ、role、aria属性）
- 画面遷移を記録（ステップ、ボタン、状態変化）
- バリデーション仕様を特定（エラー条件、メッセージ）
- 制限値を実測（サイズ、件数、文字数）

### Step 1.5: フォルダ構成決定（AI提案→人間承認 / 5〜10分）

```
AIへの指示:
「ANALYSIS_REPORT.md のサイドバー・パンくず・URL構造を元に、
 MODEL_EXPORT.md §3.5 と付録Aのパターンカタログに従って、
 テストファイルのフォルダ配置をツリー図で提案してください」
```

**AIが行うこと**:
- 分析結果からサイドバー構造・パンくず階層・URL構造を確認
- 付録Aのパターンカタログを参照して最適なパターンを選択
- フォルダ階層をツリー図で提案
- **人間が承認**したら、フォルダ作成 + テンプレート配置（CLAUDE.md, conftest.py, pytest.ini, test_results/）
- 付録Aの実績ログに1行追記

### Step 2: テスト設計（AIに依頼 / 30〜60分）

```
AIへの指示:
「ANALYSIS_REPORT.md に基づいて、TEST_DESIGN.md と FULL_TEST_CHECKLIST.md を作成してください。
 カテゴリ分類・TC-ID命名はMODEL_EXPORT.md のセクション4に従ってください」
```

**AIが行うこと**:
- テストカテゴリ分類（A〜M）
- TC-ID採番
- テストケース詳細設計（手順・期待値）
- チェックリスト生成（結果列・エビデンス列付き）

### Step 3: テストコード生成（AIに依頼 / 1〜3時間）

```
AIへの指示:
「TEST_DESIGN.md のテストケースを、Playwrightテストコードとして実装してください。
 テンプレートは MODEL_EXPORT.md のセクション5-2 に従ってください。
 以下の点を守ること:
 - 動画録画を有効にし、遅延コピーでテストIDフォルダに保存（§1.7, §5-2参照）
 - 方式Bの場合はstorage_stateパターンを使用
 - ログは _logs/ フォルダに出力
 - ロケーターは get_by_role > get_by_label 優先、exact=True デフォルト
 - カテゴリ別にファイル分割」
```

**AIが行うこと**:
- テンプレートをベースにテストコード生成
- ブラウザで実際に動作確認
- エラーが出たらセレクタ・待機時間を修正
- テストデータ生成スクリプトも必要に応じて作成

### Step 4: テスト実行・修正（反復 / 1〜2時間）

```powershell
# 1ファイルずつ実行して動作確認
python test_{機能}_normal.py

# FAILがあれば修正 → 再実行を繰り返す
```

### Step 5: チェックリスト更新（5分）

```
AIへの指示:
「全テスト実行結果に基づいて、FULL_TEST_CHECKLIST.md の結果列を更新してください。
 PASS は '結果=PASS, 実行日=今日, エビデンス=[証跡](test_results/TC-XX/)'
 FAIL は '結果=FAIL' と備考を記載」
```

---

## 9. 成功のための知見・Tips

### 9-1. Windows環境の落とし穴

| 問題 | 原因 | 対策 |
|------|------|------|
| `.env` 読み込み失敗 | Windows改行コード | `$env:VAR = "value"` で直接設定 |
| cp932エンコードエラー | 絵文字→コンソール出力 | `try/except UnicodeEncodeError` + ASCII fallback |
| パス区切り文字 | `\` vs `/` | `os.path.join()` を必ず使用 |
| ファイル名の文字化け | 日本語ファイル名 | `encoding="utf-8"` 明示 |

### 9-2. Playwright テクニック

| テクニック | 用途 | コード |
|-----------|------|--------|
| ネットワーク待機 | ページ遷移後の安定化 | `page.wait_for_load_state("networkidle")` |
| 固定待機 | UI描画完了待ち | `page.wait_for_timeout(2000)` |
| ボタンenable待機 | 非同期判定完了待ち | `expect(btn).to_be_enabled(timeout=30000)` |
| iframe操作 | フレーム内要素 | `bounding_box()` + `page.mouse.click()` |
| React入力 | 制御されたinput | `nativeInputValueSetter` + `dispatchEvent` |
| ファイルアップロード | input[type=file] | `input.set_input_files([path1, path2])` |
| セレクタ | 複数候補回避 | `get_by_role("button", name="ログイン", exact=True)` |

### 9-3. テスト設計のポイント

1. **正常系を先に全PASS** → 異常系・境界値の順に拡充
2. **1テスト = 1検証** を原則とする（FAILの原因特定が容易）
3. **テスト間の独立性** を保つ（毎テスト冒頭でページリロード）
4. **動画録画を有効にする**（テスト操作全体が自動録画され、FAIL時の原因分析に有用）
5. **動画は自動保存されるため、個別のスクリーンショットは原則不要**（特定ステップの静止画が必要な場合のみ追加）

### 9-4. AI指示のコツ

1. **ANALYSIS_REPORT.md を必ず先に作る** → テストコードの精度が上がる
2. **1カテゴリずつ生成・実行** → 大量生成は修正が困難
3. **既存のPASSコードを参考に** → 「normal.py と同じパターンで error.py を作って」
4. **セレクタ問題は動画やスクリーンショットを見せる** → AIが正しいセレクタを推定できる

### 9-5. 動画録画の知見

| 知見 | 詳細 |
|------|------|
| 遅延コピー必須 | Playwrightの動画はpage/context閉鎖後にファイル確定。`save_as()` をteardown内で呼ぶとハングする |
| storage_state分離 | 方式Bではログインと録画を別コンテキストで実行。ログイン操作が動画に含まれない |
| `_videos_tmp` | 一時保存先。テスト完了後にテストIDフォルダへコピーし、一時フォルダは削除する |
| ファイルサイズ | 1テスト(10-30秒)で約200KB-1.7MB。スクリーンショットと比較して情報量が多い |

### 9-6. テストデータ蓄積への対策

テストを繰り返し実行すると、テストデータ（例: 添付ファイル）が蓄積し、後続のテストに影響する場合がある（例: 「添付数上限を超過しています」エラー）。

**対策: URL直接指定で蓄積の少ないページへ遷移**

```python
def navigate_to_clean_page(page, page_num: int = 3):
    """添付ファイルの蓄積が少ない後方ページに遷移する"""
    page.goto(f"{BASE_URL}/invoices?page={page_num}")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)
```

> ページネーションボタンのクリックよりURL直接指定（`?page=N`）が確実。ボタンのセレクタはUIに依存するため不安定になりやすい。

### 9-7. モーダルのクリーンアップ

テスト間でモーダルが残留すると後続テストが失敗する。3段階のフォールバック戦略で確実に閉じる:

```python
def close_modal_if_open(page):
    """モーダルが開いている場合に確実に閉じる（テスト間クリーンアップ用）"""
    try:
        dialog = page.locator('[role="dialog"]')
        if dialog.count() > 0 and dialog.first.is_visible():
            # 1. 「閉じる」ボタン
            close_btn = page.get_by_role("button", name="閉じる")
            if close_btn.count() > 0 and close_btn.first.is_visible():
                close_btn.first.click(force=True)
                page.wait_for_timeout(1000)
                return
            # 2. ×ボタン（ダイアログ内の最初のボタン）
            x_btn = page.locator('[role="dialog"] button').first
            if x_btn.count() > 0:
                x_btn.click(force=True)
                page.wait_for_timeout(1000)
                return
            # 3. Escapeキー
            page.keyboard.press("Escape")
            page.wait_for_timeout(1000)
    except Exception:
        pass
```

### 9-8. サーバーエラーの早期検出（ポーリング＋エラーチェック）

非同期処理の完了待ちでは、単純なタイムアウト待機ではなく、エラー状態も並行チェックする:

```python
for attempt in range(12):  # 最大60秒（5秒 × 12回）
    try:
        expect(exec_btn).to_be_enabled(timeout=5000)
        break
    except Exception:
        # エラーメッセージが出ていないか確認
        error_check = page.evaluate("""() => {
            const d = document.querySelector('[role="dialog"]');
            if (!d) return { hasError: false };
            const text = d.innerText;
            return {
                hasError: text.includes('上限を超過') || text.includes('エラーがあります'),
                errorText: text.substring(0, 500)
            };
        }""")
        if error_check.get("hasError"):
            result["error"] = "サーバーエラー検出"
            return result
```

> 30秒待ってからFAILになるより、エラーを即座に検出できるため、テスト実行時間を大幅に短縮できる。

---

## 10. 品質メトリクス（参考値）

TOKIUMプロジェクトの実績（2026-02時点）:

| メトリクス | 値 |
|-----------|-----|
| テストスイート数 | 7（ログイン、請求書一覧、請求書詳細、取引先、帳票レイアウト、CSV作成、PDF取込）+ 共通添付8ファイル |
| 方式A自動テスト数 | ログイン5 + 請求書一覧17 + 請求書詳細15 + 取引先19 + 帳票レイアウト20 = 76件 |
| 方式B自動テスト数 | 共通添付ファイル55件（8ファイル） |
| 手動テスト設計数 | 80件 |
| 全テスト実行時間 | 約3分（並列実行） |
| 1テストあたり平均時間 | 約3秒 |
| テストカテゴリ数 | 12（自動）+ 10（手動）= 22 |
| テストIDフォルダ数 | 全テスト数 + _logs + _archive |
| PASS率 | 100%（全テストPASS） |
| 証跡形式 | .webm 動画録画（テストID別フォルダ管理） |

---

## 11. チェックリスト: 他システム適用時の確認事項

適用開始前に以下を確認:

- [ ] 対象システムのURLとログイン情報がある
- [ ] Python 3.10+ と Playwright がインストール済み
- [ ] 対象機能の画面遷移が把握できている（少なくとも概要）
- [ ] テスト用アカウントが用意されている（本番アカウント不可）
- [ ] テスト環境（staging）が利用可能

Phase 完了チェック:

- [ ] Phase 1: ANALYSIS_REPORT.md が作成された
- [ ] Phase 1.5: フォルダ構成が人間に承認され、テンプレートが配置された
- [ ] Phase 1.5: 付録Aの実績ログに記録された
- [ ] Phase 2: TEST_DESIGN.md + FULL_TEST_CHECKLIST.md が作成された
- [ ] Phase 3: テストコードが全ファイル生成された
- [ ] Phase 4: 全テスト実行して結果を確認した
- [ ] Phase 5: FULL_TEST_CHECKLIST.md の結果列が更新された
- [ ] Phase 5: test_results/ にテストIDフォルダ（動画証跡 .webm）が作成された

---

## 12. ファイル一覧（本モデルで生成されるもの）

### 12-1. 初期セットアップ時（templates/ からコピー）

| # | ファイル | テンプレート元 | 説明 |
|---|---------|-------------|------|
| 1 | `CLAUDE.md` | `templates/CLAUDE_TEMPLATE.md` | セッション管理・タスク分割ルール |
| 2 | `config.py` | `templates/config_template.py` | BASE_URL・認証情報・Playwright設定 |
| 3 | `conftest.py` | `templates/conftest_template.py` | 方式A: logged_in_page fixture |
| 4 | `pytest.ini` | `templates/pytest.ini` | 方式A: pytest設定 |
| 5 | `.env` | `templates/.env.example` | 環境変数（認証情報） |

### 12-2. Phase実行中に生成

| # | ファイル | 生成フェーズ | 説明 |
|---|---------|------------|------|
| 1 | `ANALYSIS_REPORT.md` | Phase 1 | 画面分析結果 |
| 2 | `TEST_DESIGN.md` | Phase 2 | テスト設計書 |
| 3 | `FULL_TEST_CHECKLIST.md` | Phase 2+5 | テスト結果台帳 |
| 4 | `UI_TEST_DESIGN.md` | Phase 2 | 手動UIテスト設計 |
| 5 | `test_{機能}_{カテゴリ}.py` × N | Phase 3 | テストコード（方式Bは `templates/test_template_standalone.py` ベース） |
| 6 | `create_{data}.py` × N | Phase 3 | テストデータ生成 |
| 7 | `test_results/_logs/*.log` | Phase 4 | 実行ログ |
| 8 | `test_results/_logs/*.json` | Phase 4 | JSON結果 |
| 9 | `test_results/{テストID}/{テストID}.webm` | Phase 4 | テストID別動画証跡 |
| 9b | `test_results/_auth_state.json` | Phase 4 | 方式B: storage_state一時ファイル（実行後削除） |
| 10 | `migrate_test_results.py` | 任意 | 既存結果移行用 |

---

## 付録A: フォルダ構成パターンカタログ

Phase 1.5 でAIがフォルダ階層を提案する際の判断根拠となるパターン集。新しい画面の追加実績があるたびに追記し、推定精度を向上させる。

### A-1. パターン一覧

| # | パターン名 | 判断根拠 | フォルダ配置 | TOKIUM実例 |
|---|-----------|---------|------------|-----------|
| 1 | サイドバー直下タブ | サイドバーのトップレベルメニュー項目 | `プロジェクトルート/{タブ名}/` | `取引先/`, `帳票レイアウト/` |
| 2 | タブ配下の一覧画面 | サイドバータブ → メイン画面が一覧形式 | `{タブ名}/{一覧画面名}/` | `請求書/請求書一覧/` |
| 3 | 一覧のアクションボタン機能 | 一覧画面のボタンから遷移する機能 | `{一覧}/アクション種別/{機能名}/` | `請求書一覧/請求書作成/CSVから新規作成/` |
| 4 | 一覧の「その他の操作」系 | ドロップダウン/メニュー内のサブ機能 | `{一覧}/その他の操作/{機能名}/` | `請求書一覧/その他の操作/共通添付ファイルの一括添付/` |

### A-2. パターン判定フロー

```
対象画面の情報を確認
  │
  ├─ サイドバーにトップレベルのタブとして存在する？
  │   ├─ YES → パターン1: サイドバー直下タブ
  │   │   └─ メイン画面が一覧形式？
  │   │       ├─ YES → パターン2: タブ配下の一覧画面（一覧名サブフォルダ追加）
  │   │       └─ NO  → パターン1のまま（タブ名直下に配置）
  │   └─ NO  → 別の画面から遷移して到達する
  │       └─ 到達元はどこ？
  │           ├─ 一覧画面のアクションボタン → パターン3: アクションボタン機能
  │           ├─ 一覧画面の「その他の操作」メニュー → パターン4: その他の操作系
  │           └─ 上記以外 → 新パターンとして記録
  └─ パターンが不明 → 人間に判断を委ねる（ツリー図で複数案を提示）
```

### A-3. 実績ログ（追記式）

新画面を追加するたびに以下の形式で記録する。これにより将来のAI提案の参考データが蓄積される。

| 日付 | 対象システム | 対象画面 | 適用パターン | 判断根拠 | 備考 |
|------|------------|---------|------------|---------|------|
| 2026-02-18 | TOKIUM | 取引先一覧 | パターン1 | サイドバー「取引先」直下 | — |
| 2026-02-18 | TOKIUM | 帳票レイアウト一覧 | パターン1 | サイドバー「帳票レイアウト」直下 | iframe画面 |
| 2026-02-18 | TOKIUM | 請求書一覧 | パターン2 | サイドバー「請求書」→ 一覧画面 | 一覧+詳細の両テストを格納 |
| 2026-02-18 | TOKIUM | CSVから新規作成 | パターン3 | 請求書一覧 →「請求書作成」ボタン → CSVインポート | — |
| 2026-02-18 | TOKIUM | PDFを取り込む | パターン3 | 請求書一覧 →「請求書作成」ボタン → PDFを取り込む | 2モード（分割/リネーム） |
| 2026-02-18 | TOKIUM | 共通添付ファイル一括添付 | パターン4 | 請求書一覧 →「その他の操作」→ 共通添付ファイル | モーダル形式のウィザード |

> **追記ルール**: 新画面追加時に1行追加する。「適用パターン」が既存にない場合は、A-1テーブルにも新パターンを追加する。
