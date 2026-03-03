# E2Eテスト自動化プロジェクト 引継ぎレポート

**プロジェクト名**: TOKIUM 請求書発行 E2Eテスト自動生成システム
**作成日**: 2026-02-16
**最終更新**: 2026-02-19 (未解決テスト修正完了: TH-L05 + TH-02/03/04 全PASS)
**対象システム**: https://invoicing-staging.keihi.com
**作業環境**: Windows / Python 3.14 / PowerShell

---

## 0. 現在の作業状態（セッション引継ぎ用）

| 項目 | 内容 |
|------|------|
| **最終作業** | 未解決テスト（TH-L05, TH-02/03/04）の修正完了 |
| **状態** | 全テストPASS。未解決テストゼロ。次の作業指示待ち |
| **次のタスク** | ユーザーに確認（次の作業指示待ち） |
| **未解決（既存）** | なし（全テストPASS） |
| **参照プラン** | `~/.claude/plans/imperative-gathering-beaver.md`（フォルダ構成リストラクチャリング計画 — 完了済み） |

> **このセクションの使い方**: セッションが切れた場合、次のClaudeはここを最初に読むことで再開点を即座に把握できる。作業開始・完了のたびに更新すること。

### 0.1 ワークフロー改善検討の経緯と決定事項

#### 背景
ユーザーが現状のテスト自動化ワークフローを5ステップで整理し、現状と比較評価を依頼：
①URL連携 → ②画面構成分析 → ③フォルダ作成（階層判断） → ④テスト設計（JSTQB標準） → ⑤テスト実行

#### 評価結果
- ①②⑤: 現状と一致（⑤は内部的にコード生成+実行+証跡の3段階）
- ③: **改善が必要** — フォルダ作成のタイミング・階層判断が属人的で、ワークフローに組み込まれていない
- ④: 実質JSTQB相当だが、テスト設計技法名の明示・テスト計画書が未整備

#### 決定事項: Phase 1.5「フォルダ構成決定」の導入

**運用方針（B案 + 学習型自動化の並行推進）**:

1. **当面の運用**: AIが②の分析結果（サイドバー・パンくず・URL構造）からフォルダ階層を提案 → **人間が承認** → フォルダ作成+テンプレート配置
2. **並行して学習**: 過去の実績をパターンカタログとして蓄積し、推定精度を上げる → 将来的に承認がほぼ自動化

**パターンカタログの初期データ（TOKIUM実績）**:

| パターン | 判断根拠 | フォルダ配置 | 実例 |
|---------|---------|------------|------|
| サイドバー直下タブ | サイドバーのトップレベルメニュー | TH直下 | `取引先/`, `帳票レイアウト/` |
| タブ配下の一覧画面 | サイドバータブ → メイン画面が一覧 | タブ名/一覧画面名/ | `請求書/請求書一覧/` |
| 一覧のアクションボタン機能 | 一覧画面のボタンから遷移する機能 | 一覧/アクション種別/機能名/ | `請求書一覧/請求書作成/CSVから新規作成/` |
| 一覧の「その他の操作」系 | ドロップダウン/メニュー内の機能 | 一覧/その他の操作/機能名/ | `請求書一覧/その他の操作/共通添付ファイルの一括添付/` |

**実装先**: `MODEL_EXPORT.md` に以下2セクションを追加
- Phase 1 と Phase 2 の間に「Phase 1.5: フォルダ構成決定」（運用ルール + 手順）
- 付録として「フォルダ構成パターンカタログ」（学習データ、新画面追加時に随時追記）

#### MODEL_EXPORT.md への追記（実施済み）

以下5箇所を変更完了:

| # | 変更箇所 | 内容 |
|---|---------|------|
| 1 | §1 全体アーキテクチャ | 「5フェーズ」→「6フェーズ」、Phase 1.5をフロー図に追加 |
| 2 | §3.5（新規） | Phase 1.5 詳細: 目的・判断情報5項目・決定フロー・AIへの指示テンプレート・出力物・.envパス自動調整・学習サイクル |
| 3 | 付録A（新規） | パターン一覧4件・判定フロー図・TOKIUM実績ログ6件・追記ルール |
| 4 | §8 Step 1.5（新規） | 適用手順にフォルダ構成決定ステップ追加、Step 0からフォルダ作成を分離 |
| 5 | §11 チェックリスト | Phase 1.5完了チェック2項目追加（承認+実績ログ記録） |

#### 未解決テスト修正（2026-02-19 実施済み）

**TH-L05（ログイン正常系 — headless環境で FAIL）**:
- **原因**: `expect(page).not_to_have_url()` のデフォルトタイムアウト5秒が不足。headless環境ではログイン後のリダイレクトに5秒以上かかる場合がある。また `.env` からの認証情報読み込みが環境変数未設定時に機能しない
- **修正**:
  1. `.env` ファイルから直接読み込む `_load_env()` を追加（環境変数 → .env の優先順）
  2. ログインクリック前に `wait_for_timeout(500)` を追加（入力完了の確実化）
  3. URL遷移待機のタイムアウトを **5秒 → 30秒** に延長
- **ファイル**: `ログイン/generated_tests/test_tokium_login.py`
- **結果**: 5 PASS / 0 FAIL（TH-L05: 2.47秒で正常完了）

**TH-02/03/04（共通添付ファイル正常系 — FAIL）**:
- **原因**: 1ページ目の請求書に過去テスト実行分の添付ファイルが蓄積し、添付数上限（10件）を超過。サーバーから「添付数上限を超過しています」エラーが返され、「添付を実行する」ボタンが有効にならない。TH-03はTH-02のエラー後にモーダルが残留しタイムアウト
- **修正**:
  1. `navigate_to_clean_page()` を追加 — URLパラメータ `?page=3` で添付蓄積の少ない3ページ目に直接遷移
  2. `close_modal_if_open()` を追加 — テスト間のモーダル残留を検出して閉じる
  3. 非同期判定待機ループ内でサーバーエラー（上限超過等）を5秒ごとに早期検出し、60秒待ち切る前にFAIL判定
- **ファイル**: `請求書/請求書一覧/その他の操作/共通添付ファイルの一括添付/test_bulk_attachment_normal.py`
- **結果**: 4 PASS / 0 FAIL（TH-01〜04 全て正常完了、合計約2分）

#### 環境方針の決定

**議論内容**:
- 作業環境: Claude Code（ターミナル）→ ローカルPC上でファイル操作・テスト実行
- ブラウザ/OS対応: 現在はChromium + Windowsに完全固定（`p.chromium.launch()` が20+ファイルにハードコード）
- Playwrightは3ブラウザ（chromium/firefox/webkit）× 3OS（Win/Mac/Linux）に対応可能

**決定**: まずChromium + Windowsで機能を完成させる。マルチブラウザ・マルチOS対応は後回し。
- 方式A（pytest形式）: `--browser` フラグで切替可能（コード変更不要）
- 方式B（独立スクリプト）: 20+ファイルの `p.chromium.launch()` を環境変数切替に要修正（将来タスク）

---

## 1. プロジェクト概要

### 背景と目的
Claude in Chrome を使ったE2Eテスト自動化は、WEB要素の自動取得とWEB操作の自動化が可能だが、毎ステップごとにLLMのラウンドトリップが発生するため動作が非常に遅い（1テストあたり約30秒）。

本プロジェクトでは **「AIでテストコード生成 → Playwrightで高速実行」** の2段階方式を採用し、AI呼び出しを生成時と修復時のみに限定することで、**5テスト合計7.79秒（1テストあたり約1.5秒）** を実現した。

### アーキテクチャ
```
① 自然言語でテストシナリオを書く（YAML）
    ↓
② AI がページを解析し、Playwright テストコードを生成（遅い / 1回のみ）
    ↓
③ 生成されたテストを Playwright で高速実行（速い / 何度でも）
    ↓
④ UI が変わったら AI が自動修復（必要な時だけ）
```

---

## 2. 現在の完了状態

### 完了済み

| 項目 | 状態 | 詳細 |
|------|------|------|
| プロジェクト基盤 | 完了 | Python + pytest + playwright 構成 |
| ページ解析モジュール | 完了 | `ログイン/page_analyzer.py` |
| テストコード生成モジュール | 完了 | `ログイン/code_generator.py` |
| 自動修復モジュール | コード完了 | `ログイン/self_healer.py`（CLIからの呼び出し未実装） |
| CLI | 完了 | `generate.py`（`--heal`モードは未実装） |
| ログイン画面テスト | 全5テストPASS | `ログイン/generated_tests/test_tokium_login.py` |
| ログイン画面 解析レポート | 完了 | `ログイン/ANALYSIS_REPORT.md` |
| 請求書一覧画面 解析レポート | 完了 | `請求書/請求書一覧/ANALYSIS_REPORT_INVOICES_1.md` |
| 請求書詳細画面 解析レポート | 完了 | `請求書/請求書一覧/ANALYSIS_REPORT_INVOICE_DETAIL.md` |
| 請求書一覧画面テスト | 全17テストPASS | `請求書/請求書一覧/generated_tests/test_invoice_list.py` |
| 請求書詳細画面テスト | 全15テストPASS | `請求書/請求書一覧/generated_tests/test_invoice_detail.py` |
| 請求書作成テスト | 5テストPASS (113秒) | `請求書/請求書一覧/請求書作成/CSVから新規作成/test_invoice_creation.py` |
| CSVインポート自動化 | 完了 | 3000件・3件ともに成功確認済み |
| 統合実行スクリプト | 完了 | `請求書/請求書一覧/請求書作成/CSVから新規作成/run_csv_import.py` |
| 共通添付ファイル一括添付（正常系） | 完了 | 4テスト全PASS（PDF/複数ファイル/各種拡張子/日本語名） |
| 共通添付ファイル一括添付（モーダル分析） | 完了 | 3ステップウィザードのDOM構造・画面遷移を分析 |
| 共通添付ファイル一括添付（異常系・境界値） | 完了 | 9テスト全PASS（サイズ超過/ファイル数超過/拡張子なし/境界値OK） |
| 共通添付ファイル一括添付（エラー仕様分析） | 完了 | 2段階バリデーション構造・エラーメッセージ・サイズ上限を特定 |
| 共通添付ファイル一括添付（DOM検証） | 完了 | 8テスト全PASS（モーダルrole/ステップ構造/input属性/初期状態） |
| 共通添付ファイル一括添付（ナビゲーション+開閉） | 完了 | 10テスト全PASS（戻る/再進行/タブ切替/閉じる/×ボタン） |
| 共通添付ファイル一括添付（複数請求書一括） | 完了 | 3テスト全PASS（2件/5件一括、複数ファイル×複数請求書） |
| 共通添付ファイル一括添付（エッジケース） | 完了 | 4テスト全PASS（0バイト/混在/重複/削除） |
| 共通添付ファイル一括添付（ファイル名+拡張子） | 完了 | 12テスト全PASS（半角/全角/カタカナ/長文名/各種拡張子） |
| 共通添付ファイル一括添付（既存から選択タブ） | 完了 | 5テスト全PASS（タブ切替/一覧・選択/戻り/全フロー/検索フォーム） |
| 共通添付ファイル一括添付（テスト設計書） | 完了 | TEST_DESIGN.md: 全55自動テスト＋80手動テスト設計完了 |
| 共通添付ファイル一括添付（統合チェックリスト） | 完了 | FULL_TEST_CHECKLIST.md: 135項目（自動55+手動80）統合 |
| TH-IDフォルダ別証跡管理 | 完了 | test_results/TH-XX/ に動画録画(webm)自動振り分け、_logs/ にログ集約 |
| 汎用モデル輸出ドキュメント | 完了 | MODEL_EXPORT.md: 5フェーズ方式・テンプレート・適用手順を文書化 |
| E2E解析メソドロジー | 完了 | E2E_ANALYSIS_METHODOLOGY.md: Phase1-3詳細手法・トラブルシューティング・付録 |
| CLAUDE.md（セッション管理） | 完了 | 請求書/請求書一覧/CLAUDE.md: タスク分割ルール・コンテキスト節約ルール |
| 取引先画面 解析レポート | 完了 | 取引先/ANALYSIS_REPORT_PARTNERS.md |
| 取引先一覧画面テスト | 全19テストPASS | 取引先/test_partner_list.py（約93秒） |
| 取引先 CLAUDE.md | 完了 | 取引先/CLAUDE.md: 画面構造・技術知見・テスト一覧 |
| 帳票レイアウト画面 解析レポート | 完了 | 帳票レイアウト/ANALYSIS_REPORT_DESIGN.md |
| 帳票レイアウト画面テスト | 全20テストPASS | 帳票レイアウト/test_design_list.py（約292秒） |
| 帳票レイアウト CLAUDE.md | 完了 | 帳票レイアウト/CLAUDE.md: 画面構造・iframe知見・テスト一覧 |
| PDF取り込み画面 解析レポート | 完了 | 請求書/請求書一覧/請求書作成/PDFを取り込む/ANALYSIS_REPORT_PDF_ORGANIZER.md |
| PDF取り込み画面テスト | 全27テストPASS | 請求書/請求書一覧/請求書作成/PDFを取り込む/test_pdf_organizer.py（約364秒） |
| PDFを取り込む CLAUDE.md | 完了 | 請求書/請求書一覧/請求書作成/PDFを取り込む/CLAUDE.md: 2モード構造・iframe知見・テスト一覧 |
| TH-IDプレフィックス統一 | 完了 | 全ドキュメント・テストコード・フォルダ名のTC-→TH-に一括変更（14ドキュメント+9テストファイル+55フォルダ） |
| テスト管理ドキュメント横展開 | 完了 | 全8画面にTEST_DESIGN.md + FULL_TEST_CHECKLIST.md配備（合計243項目管理） |
| 全画面test_results対応 | 完了 | 8画面のconftest.pyにTH-IDマッピング・ログ・動画録画(webm)・JSONサマリー自動保存追加 |
| スクリーンショット→動画録画切替 | 完了 | 全画面で静止画スクリーンショットを廃止し動画録画(webm)に切替。遅延コピーパターンで0KBバグ解決 |
| 旧スクリーンショットコード/ファイル完全除去 | 完了 | 9テストファイルからpage.screenshot()削除、旧PNG145件・空フォルダ55件・_archiveフォルダ一括削除 |
| 全6画面動画録画出力検証 | 完了 | ログイン(5PASS)・請求書(31PASS/1ERR)・取引先(19PASS)・帳票レイアウト(18PASS/2FAIL)・PDF取込(27PASS)・請求書作成(5PASS) 全0KB動画ゼロ |
| 共通添付ファイル8テスト修復 | 完了 | 孤立コード除去・空try/except修正 → 50 PASS / 5 FAIL（既存仕様差異） |
| 共通添付ファイル動画録画組込 | 完了 | 8ファイル全55テストにstorage_state+per-test page方式で動画録画実装。全55本webm生成確認（0KBゼロ） |
| フォルダ構成リストラクチャリング | 完了 | フラットな「〇〇画面」形式からTOKIUM画面遷移に沿った階層構造に変更。フォルダ移動・.envパス修正(26ファイル)・コメント修正・ドキュメント更新（CLAUDE.md×4+HANDOVER等） |

### 未実装・今後の作業

| 項目 | 優先度 | 詳細 |
|------|--------|------|
| `--heal` CLIモード | 低 | pytest実行→失敗検出→SelfHealer呼出の統合 |
| CI/CD統合 | 低 | GitHub Actions等への組み込み |

---

## 3. ファイル構成

### フォルダ構成
```
C:\Users\池田尚人\ClaudeCode用\画面テスト\TH\
├── HANDOVER_REPORT.md               # 本ファイル（プロジェクト全体管理）
├── MODEL_EXPORT.md                  # 汎用モデル輸出ガイド（5フェーズ方式）
├── E2E_ANALYSIS_METHODOLOGY.md      # E2E解析メソドロジー（詳細手法・テンプレート）
├── templates\                       # テンプレート実体ファイル（コピーして使用）
│   ├── README.md                    # テンプレート一覧・使い方
│   ├── CLAUDE_TEMPLATE.md           # CLAUDE.md テンプレート
│   ├── conftest_template.py         # 方式A: pytest共通fixture
│   ├── config_template.py           # 方式A: 設定ファイル
│   ├── pytest.ini                   # 方式A: pytest設定
│   ├── test_template_standalone.py  # 方式B: 独立スクリプト形式
│   └── .env.example                 # 環境変数サンプル
├── .claude/settings.local.json      # Claude Code設定
│
├── ログイン\                         # ログイン画面関連
│   ├── .env                         # テスト認証情報（全画面共通で参照）
│   ├── .gitignore
│   ├── conftest.py                  # pytest共通設定（test_results対応済み）
│   ├── config.py                    # プロジェクト設定
│   ├── pytest.ini
│   ├── generate.py                  # CLIエントリーポイント
│   ├── page_analyzer.py             # ページ構造解析
│   ├── code_generator.py            # テストコード生成
│   ├── self_healer.py               # 失敗時自動修復
│   ├── requirements.txt
│   ├── run_tests.ps1
│   ├── ANALYSIS_REPORT.md           # ログイン画面解析レポート
│   ├── TEST_DESIGN.md               # テスト設計書（TH-L01〜L05）
│   ├── FULL_TEST_CHECKLIST.md       # 統合チェックリスト
│   ├── ARCHITECTURE.md              # システム設計書
│   ├── README.md
│   ├── login.yaml / tokium_login.yaml
│   ├── test_results\                # テスト結果（ログ・動画録画・JSONサマリー）
│   └── generated_tests/
│       ├── test_tokium_login.py     # 5テストPASS（TH-IDマッピング済み）
│       └── test_login_sample.py
│
├── 請求書\                           # 請求書関連
│   └── 請求書一覧\                   # 請求書一覧・詳細画面関連
│       ├── CLAUDE.md                    # セッション管理（タスク分割・コンテキスト節約ルール）
│       ├── conftest.py                  # pytest共通設定（logged_in_page fixture、test_results対応済み）
│       ├── config.py
│       ├── pytest.ini
│       ├── ANALYSIS_REPORT_INVOICES_1.md     # 請求書一覧画面 解析レポート
│       ├── ANALYSIS_REPORT_INVOICE_DETAIL.md # 請求書詳細+作成自動化 解析レポート
│       ├── test_results\                     # テスト結果（一覧+詳細共通）
│       ├── generated_tests/
│       │   ├── test_invoice_list.py          # 17テストPASS（TH-IL01〜IL17マッピング済み）
│       │   ├── test_invoice_detail.py        # 15テストPASS（TH-ID01〜ID15マッピング済み）
│       │   ├── TEST_DESIGN_INVOICE_LIST.md   # 一覧テスト設計書
│       │   ├── FULL_TEST_CHECKLIST_INVOICE_LIST.md   # 一覧統合チェックリスト
│       │   ├── TEST_DESIGN_INVOICE_DETAIL.md # 詳細テスト設計書
│       │   └── FULL_TEST_CHECKLIST_INVOICE_DETAIL.md # 詳細統合チェックリスト
│       ├── 請求書作成\                        # 請求書作成関連
│       │   ├── CSVから新規作成\               # CSVインポート自動化
│       │   │   ├── conftest.py                   # pytest共通設定（test_results対応）
│       │   │   ├── run_csv_import.py             # 統合実行スクリプト（推奨）
│       │   │   ├── generate_3000_csv.py          # CSV生成（単独）
│       │   │   ├── import_3000.py                # インポート（単独）
│       │   │   ├── check_3000_status.py          # 結果確認（単独）
│       │   │   ├── import_and_verify_v2.py       # 少量テスト用
│       │   │   ├── write_memo_v2.py              # メモ記入
│       │   │   ├── test_invoice_creation.py      # 5テストPASS（TH-CI01〜CI05マッピング済み）
│       │   │   ├── TEST_DESIGN_CSV_IMPORT.md     # CSVインポートテスト設計書
│       │   │   ├── FULL_TEST_CHECKLIST_CSV_IMPORT.md # CSVインポート統合チェックリスト
│       │   │   ├── test_results\                 # テスト結果（CSVインポート）
│       │   │   └── CSVファイル\                   # 参考CSV
│       │   └── PDFを取り込む\                 # PDF取り込みテスト
│       │       ├── CLAUDE.md                     # セッション管理（2モード構造・iframe知見）
│       │       ├── ANALYSIS_REPORT_PDF_ORGANIZER.md  # PDF取り込み画面 解析レポート
│       │       ├── TEST_DESIGN.md               # テスト設計書（TH-PO01〜PO27）
│       │       ├── FULL_TEST_CHECKLIST.md       # 統合チェックリスト
│       │       ├── conftest.py                  # pytest共通設定（logged_in_page fixture）
│       │       ├── pytest.ini
│       │       ├── test_pdf_organizer.py        # 27テストPASS（TH-IDマッピング済み、約364秒）
│       │       ├── test_results\                # テスト結果（ログ・動画録画・JSONサマリー）
│       │       └── debug_iframe.py              # iframe調査用デバッグスクリプト
│       └── その他の操作\                      # その他の操作関連
│           └── 共通添付ファイルの一括添付\     # 共通添付ファイル一括添付テスト（55件）
│               ├── TEST_DESIGN.md                 # テスト設計書（全カテゴリ定義）
│               ├── FULL_TEST_CHECKLIST.md         # 統合チェックリスト（135項目）
│               ├── UI_TEST_DESIGN.md              # UI目視テスト設計書（80項目）
│               ├── UI_TEST_CHECKLIST.md           # UI目視チェックリスト
│               ├── test_bulk_attachment_normal.py  # カテゴリA: 正常系（4件PASS）
│               ├── test_bulk_attachment_error.py   # カテゴリB,C,D: 異常系・境界値（9件PASS）
│               ├── test_bulk_attachment_dom.py     # カテゴリJ: DOM/エレメント検証（8件PASS）
│               ├── test_bulk_attachment_navigation.py # カテゴリH,I: ナビ+開閉（10件PASS）
│               ├── test_bulk_attachment_multi.py   # カテゴリG: 複数請求書一括（3件PASS）
│               ├── test_bulk_attachment_edge.py    # カテゴリK: エッジケース（4件PASS）
│               ├── test_bulk_attachment_filename.py # カテゴリE,F: ファイル名+拡張子（12件PASS）
│               ├── test_bulk_attachment_existing.py # カテゴリL: 既存から選択タブ（5件PASS）
│               ├── analyze_step2_step3_flow.py     # 画面遷移分析
│               ├── analyze_error_behavior.py       # エラー動作分析
│               ├── analyze_size_boundary.py        # サイズ境界値分析
│               ├── analyze_existing_tab.py         # 既存タブUI構造分析
│               ├── test_results\                   # テスト結果・動画録画
│               ├── ファイル名\                     # テスト用ファイル(14種)
│               ├── 拡張子\                        # テスト用ファイル(13種+拡張子なし)
│               └── ファイルサイズ\                 # テスト用ファイル(8パターン+0バイト)
│
├── 取引先\                           # 取引先画面関連
│   ├── CLAUDE.md                    # セッション管理（画面構造・技術知見）
│   ├── ANALYSIS_REPORT_PARTNERS.md  # 取引先画面 解析レポート
│   ├── TEST_DESIGN.md               # テスト設計書（TH-PL01〜PL19）
│   ├── FULL_TEST_CHECKLIST.md       # 統合チェックリスト
│   ├── conftest.py                  # pytest共通設定（logged_in_page fixture、test_results対応済み）
│   ├── pytest.ini                   # testpaths=.
│   ├── test_partner_list.py         # 19テストPASS（TH-IDマッピング済み、約93秒）
│   └── test_results\                # テスト結果（ログ・動画録画・JSONサマリー）
│
└── 帳票レイアウト\                   # 帳票レイアウト画面関連
    ├── CLAUDE.md                    # セッション管理（iframe知見・テスト一覧）
    ├── ANALYSIS_REPORT_DESIGN.md    # 帳票レイアウト画面 解析レポート
    ├── TEST_DESIGN.md               # テスト設計書（TH-DL01〜DL20）
    ├── FULL_TEST_CHECKLIST.md       # 統合チェックリスト
    ├── conftest.py                  # pytest共通設定（logged_in_page fixture、test_results対応済み）
    ├── pytest.ini                   # testpaths=.
    ├── test_design_list.py          # 20テストPASS（TH-IDマッピング済み、約292秒）
    └── test_results\                # テスト結果（ログ・動画録画・JSONサマリー）
```

---

## 4. 技術スタック

| コンポーネント | 技術 | バージョン |
|--------------|------|-----------|
| 言語 | Python | 3.14.2 |
| テストFW | pytest | 9.0.2 |
| ブラウザ操作 | Playwright | 0.7.2 (pytest-playwright) |
| AI | Anthropic Claude API | claude-sonnet-4-5 |
| シナリオ定義 | YAML | PyYAML 6.0+ |
| HTML解析 | BeautifulSoup4 | 4.12+ |
| CLI表示 | Rich | 13.0+ |

---

## 5. 動作確認済みテスト詳細

### test_tokium_login.py（5テスト、全PASS、7.79秒）

| # | テスト名 | 内容 | 主要ロケーター |
|---|---------|------|--------------|
| 1 | test_ログインページの表示確認 | 全要素の存在・属性検証 | `get_by_role`, `get_by_label` |
| 2 | test_パスワードリセット画面への遷移 | /recovery遷移確認 | `get_by_role("link", name="パスワードを忘れた場合")` |
| 3 | test_新規登録画面への遷移 | /registration遷移確認 | `get_by_role("link", name="新規登録はこちら")` |
| 4 | test_tokium_idログイン画面への遷移 | /auth-redirect遷移確認 | `page.locator('a[href="/auth-redirect"]')` |
| 5 | test_正常ログイン | 認証→ログイン成功 | `get_by_label("メールアドレス")`, `get_by_label("パスワード")` |

### 修正履歴（トラブルシューティング）

| 問題 | 原因 | 解決策 |
|------|------|--------|
| 全テスト FAILED: strict mode violation | `name="ログイン"` が「TOKIUM ID でログイン」にも部分一致 | `exact=True` を追加 |
| TOKIUM IDボタン クリックタイムアウト | `<button>` が `<a href="/auth-redirect">` 内にネストされ、`<a>`がクリック横取り | `page.locator('a[href="/auth-redirect"]')` で親リンクを直接クリック |
| 正常ログイン FAILED: URL変わらず | .env の値が環境変数に読み込まれていなかった | `$env:TEST_EMAIL = "..."` で直接設定 |
| PowerShell ps1実行エラー | 実行ポリシーによるブロック | `powershell -ExecutionPolicy Bypass` または直接コマンド実行 |

---

## 6. 請求書一覧画面（/invoices）解析結果サマリー

Claude in Chrome で解析済み。詳細は `ANALYSIS_REPORT_INVOICES.md` を参照。

### 画面構成
- **ヘッダー**: ロゴ、ユーザー名（池田尚人）、ヘルプリンク、事業所切替
- **サイドバー**: 請求書(/invoices)、取引先(/partners)、帳票レイアウト(/invoices/design)
- **アクション**: CSVから新規作成(/invoices/import)、PDFを取り込む(/invoices/pdf-organizer)
- **検索フォーム**: 18項目（テキスト入力、セレクトボックス、日付範囲、チェックボックス群）
- **テーブル**: 8,013件、100件表示、10列（チェックボックス/取引先/送付先/ステータス/承認状況/請求書番号/合計金額/請求日/支払期日/ファイル名）
- **一括操作**: 送付/送付済みにする/その他の操作/選択解除

### 主要ロケーター一覧

```python
# サイドバーナビゲーション
page.get_by_role("link", name="請求書")
page.get_by_role("link", name="取引先")
page.get_by_role("link", name="帳票レイアウト")

# アクションボタン
page.get_by_role("link", name="CSVから新規作成")
page.get_by_role("link", name="PDFを取り込む")

# 検索フォーム
page.get_by_label("送付方法")           # combobox: 全て/メール/Web送付/郵送代行/FAX送付/その他
page.get_by_label("取引先コード")        # textbox
page.get_by_label("取引先名")           # textbox
page.get_by_label("自社担当部署")        # textbox
page.get_by_label("自社担当者名")        # textbox
page.get_by_label("請求書番号")         # textbox
page.get_by_label("合計金額")           # textbox
page.get_by_label("ファイル名 （添付ファイル名）")  # textbox
page.get_by_placeholder("メモ")         # textbox
page.get_by_label("承認状況")           # combobox: 全て/承認済み/未承認
page.get_by_label("Web送付 ダウンロード状況")  # combobox

# ステータスチェックボックス
page.get_by_label("登録中")      # value="processing"
page.get_by_label("未送付")      # value="available"
page.get_by_label("送付中")      # value="sending"
page.get_by_label("送付済み")    # value="sent"
page.get_by_label("送付待ち")    # value="scheduled"
page.get_by_label("登録失敗")    # value="failed_to_process"
page.get_by_label("送付失敗")    # value="failed_to_send"

# 検索実行
page.get_by_role("button", name="この条件で検索")
page.get_by_role("button", name="リセット")
page.get_by_role("button", name="帳票エラーをチェック")
page.get_by_role("button", name="検索条件")  # 開閉トグル

# 一括操作
page.get_by_role("button", name="請求書を送付する")
page.get_by_role("button", name="送付済みにする")
page.get_by_role("button", name="その他の操作")
page.get_by_role("button", name="選択解除")
```

### ロケーター品質評価
- ✅ 全フォームフィールドに `<label>` 設定済み → `get_by_label()` 利用可能
- ✅ ボタンにテキスト名あり → `get_by_role("button", name=...)` 利用可能
- ⚠️ テーブル行に `data-testid` なし → テキストマッチング必要
- ⚠️ ページネーション前/次ボタンにテキストラベルなし（imgのみ）
- ⚠️ 日付フィールドが同一placeholder → `.first` / `.last` で区別が必要

---

## 7. 重要な設計判断と知見

### ロケーター優先順位（システムプロンプトでClaude APIに指示）
```
get_by_role > get_by_label > get_by_placeholder > get_by_text > get_by_test_id > locator(CSS)
```

### Playwright固有の注意点（TOKIUM特有）
1. **`exact=True` の使用**: 「ログイン」と「TOKIUM ID でログイン」のように部分一致する要素がある場合は必須
2. **ネストされたクリック対象**: `<a>` 内の `<button>` は `<a>` がクリックを横取りする → 親要素を直接クリック
3. **ログイン認証の前提**: 請求書一覧画面（/invoices）のテストにはログイン状態が必要。テスト内でログイン処理を共通ヘルパーとして実装する必要がある
4. **環境変数の読み込み**: Windows PowerShellでは `.env` ファイルの自動読み込みが不安定。`$env:VAR = "value"` での直接設定が確実
5. **Headless UI ダイアログ**: `role="dialog"` のラッパー要素は `height=0` で Playwright の visible 判定が失敗する → ダイアログ内の `h2` 等の子要素で `wait_for(state="visible")`
6. **ポインタインターセプト**: Headless UI の portal-root が click をブロック → `click(force=True)` で回避
7. **非同期判定待機**: ボタンが async 処理完了後に enabled になるケース → `expect().to_be_enabled(timeout=30000)` で待機

### 取引先画面固有の知見
1. **検索フォームのポインタインターセプト**: 検索フォーム展開時にテーブル領域がインターセプトされる → `click(force=True)` で回避、モーダル操作前に `close_search_form()` で閉じる
2. **ロケーター重複**: 「検索条件」ボタンと「検索条件を追加」が部分一致 → `exact=True` で解決。「取引先コード」等がフォーム/モーダルで重複 → `form`/`article` でスコープ指定
3. **モーダルのDOM構造差異**: 更新モーダル=`article`要素、新規モーダル=`dialog`要素 → `article.filter(has=heading)` パターンで統一的にスコープ
4. **ページネーションのDOM構造**: ボタンは `main > button` ではなく `div._pagingControl_ > button` にネスト → 件数テキストの親要素から辿る

### 帳票レイアウト画面固有の知見
1. **gallery iframeのクロスオリジン制約**: メインコンテンツは外部ドメイン（`tpmlyr.dev.components.asaservice.inc`）のiframe内。`page.frame(name="gallery")`でのみ操作可能。Chrome拡張（Claude in Chrome）のread_page/find/clickはiframe内で動作しない
2. **iframe内要素のクリック**: `bounding_box()` + `page.mouse.click()` が最も確実。標準の `.click()` が効かない場合あり
3. **iframe内の入力操作**: `fill()` がReact stateを更新しない場合 → `bounding_box` + `mouse.click` + `keyboard.type` で対応
4. **ロケーター重複**: 「帳票レイアウト」リンクがサイドバーとパンくずで重複 → `.first` / `#main-content nav` で区別。「請求書」リンクはロゴ・ヘルプ・サイドバーで3つにマッチ → `exact=True` + `.first`
5. **iframe読み込み待機**: 初回ロード `8000ms`、操作後 `3000ms` の待機が必要。`networkidle` 待機も併用
6. **CSVインポート画面と同一パターン**: gallery iframeの操作方式はCSVインポートの `datatraveler` iframeと共通（MUI Gridベース）

### PDF取り込み画面固有の知見
1. **2モード構成**: ファイル分割（`/separation`、3ステップ）とファイルリネーム（`/rename`、2ステップ）。`/invoices/pdf-organizer`は`/separation`にリダイレクト
2. **organizer iframeの取得**: `page.frame(name="organizer")`で取得。⚠️ `page.frame(url=lambda url: "organizer" in url)` は使わないこと — メインページURL（`/pdf-organizer/separation`）にもマッチして親ページを返す
3. **iframe名の解析時注意**: Chrome DevToolsやアクセシビリティツリーではname属性が空に見える場合があるが、Playwright実行時は`name="organizer"`で正常取得可能
4. **iframe比較表**: PDF取り込み=`frame(name="organizer")`、CSVインポート=`frame(name="gallery")`/`frame(name="datatraveler")`、帳票レイアウト=`frame(name="gallery")`。全て外部ドメイン`tpmlyr.dev.components.asaservice.inc`
5. **Intercom iframe**: ページにはチャットウィジェット用の`#intercom-frame`も存在するが、テストでは無視してよい

### テストコード生成の流れ
```
YAMLシナリオ → generate.py → (Playwrightでページ解析) → (Claude APIでコード生成) → generated_tests/に保存
```

---

## 8. 環境構築手順

```powershell
# 1. 依存パッケージのインストール
pip install -r requirements.txt

# 2. Playwrightブラウザのインストール
playwright install chromium

# 3. 環境変数の設定
$env:ANTHROPIC_API_KEY = "sk-ant-..."   # テスト生成時に必要
$env:TEST_EMAIL = "テスト用メールアドレス"
$env:TEST_PASSWORD = "テスト用パスワード"

# 4. 既存テストの実行
pytest generated_tests/test_tokium_login.py -v --headed

# 5. シナリオからテスト生成（新規テスト作成時）
python generate.py scenarios/tokium_login.yaml
```

---

## 9. テスト管理標準化

### TH-IDプレフィックス体系

全テストケースにTH（Test Hypothesis）プレフィックスを付与し、画面別に一意のIDで管理。

| 画面 | プレフィックス | ID範囲 | テスト数 |
|------|--------------|--------|---------|
| ログイン画面 | TH-L | TH-L01〜L05 | 5 |
| 請求書一覧画面 | TH-IL | TH-IL01〜IL17 | 17 |
| 請求書詳細画面 | TH-ID | TH-ID01〜ID15 | 15 |
| CSVインポート | TH-CI | TH-CI01〜CI05 | 5 |
| 取引先一覧画面 | TH-PL | TH-PL01〜PL19 | 19 |
| 帳票レイアウト画面 | TH-DL | TH-DL01〜DL20 | 20 |
| PDF取り込み画面 | TH-PO | TH-PO01〜PO27 | 27 |
| 共通添付ファイル | TH-01/E/F/C/D/M/N/T/V/X | TH-01〜TH-X01 | 55 |
| **合計** | | | **163** |

### test_results構造（全8画面共通）

```
各画面フォルダ/
└── test_results/
    ├── _logs/                         # ログ集約フォルダ
    │   ├── test_xxx_YYYYMMDD_HHMMSS.log  # テキストログ（タイムスタンプ付き）
    │   └── test_xxx_YYYYMMDD_HHMMSS.json # JSONサマリー（PASS/FAIL数・所要時間）
    ├── TH-XX01/                       # TH-IDごとの動画録画
    │   └── TH-XX01.webm               # テスト操作の動画（Playwright録画）
    ├── TH-XX02/
    │   └── TH-XX02.webm
    └── ...
```

### conftest.pyパターン（pytest hooks + 動画録画）

各画面のconftest.pyに以下の共通パターンを実装：

1. **`browser_context_args`**: `record_video_dir`・`record_video_size` を設定し、Playwrightの動画録画を有効化
2. **`pytest_sessionstart`**: ログファイルを開き、セッション開始を記録
3. **`pytest_runtest_makereport`**: 各テスト完了時に動画パスを`_pending_video_copies`リストに記録（※この時点では動画ファイルが未確定のためコピーしない）
4. **`pytest_sessionfinish`**: PASS/FAIL集計・JSONサマリー保存、**遅延コピー**で全動画をTH-IDフォルダへ一括保存

#### 遅延コピーパターン（重要な技術知見）

Playwrightの動画ファイルはブラウザコンテキスト（ページ）が閉じるまで確定しない。`pytest_runtest_makereport`フック時点ではページがまだ開いているため、`shutil.copy2`で0KBファイルがコピーされる問題があった。

**解決策**: フック時点ではパスだけ記録し、`pytest_sessionfinish`（全ページ閉鎖後）で一括コピーする。

```python
_pending_video_copies = []  # モジュールレベル

# pytest_runtest_makereport: パスだけ記録
_pending_video_copies.append((video_path, dest_path))

# pytest_sessionfinish: ページ閉鎖後に一括コピー
for src_path, dest_path in _pending_video_copies:
    if os.path.exists(src_path) and os.path.getsize(src_path) > 0:
        shutil.copy2(src_path, dest_path)
```

テストファイル側の実装：
- **`TH_ID_MAP`辞書**: テスト関数名→TH-IDのマッピング定義
- **`_set_th_id` autouse fixture**: `request.node._th_id` にTH-IDを自動設定

### 方式B: standalone scripts（共通添付ファイル8テスト）の動画録画

共通添付ファイルの8テストファイルはpytestではなく独自の`main()`関数で実行する方式B。conftest.pyの遅延コピーパターンと同等の動画録画を3フェーズ方式で実装：

1. **Phase 1（ログイン）**: ログイン用contextを作成→ログイン→`storage_state(path=...)`でcookie/sessionをJSON保存→context閉じる
2. **Phase 2（テスト実行）**: `storage_state=` + `record_video_dir=` 付きの新contextを作成。テストごとに`context.new_page()`で新ページ作成（自動で動画開始）→テスト実行→`page.video.path()`記録→`page.close()`
3. **Phase 3（遅延コピー）**: `context.close()`後（動画ファイル確定後）に`_videos_tmp/`→`test_results/TH-XXNN/TH-XXNN.webm`へコピー→一時フォルダ削除

**ポイント**: ログインは1回のみ（storage_stateで認証状態を継承）、テスト関数は変更不要（page引数をそのまま受け取る）。

### テスト管理ドキュメント（全8画面配備済み）

| ドキュメント | 内容 | 配備先 |
|-------------|------|--------|
| TEST_DESIGN.md | テスト設計書（カテゴリ・観点・期待結果） | 全8画面 |
| FULL_TEST_CHECKLIST.md | 統合チェックリスト（TH-ID・結果・証跡パス） | 全8画面 |

---

## 10. 次のステップ（推奨作業順）

### Step 1: テスト共通基盤の強化
- ~~各画面のconftest.pyの統一化検討~~ → 完了（全8画面のconftest.pyをtest_results対応パターンに統一）
- テストデータの管理（.env or fixtures）
- ~~スクリーンショット/動画のキャプチャ設定~~ → 完了（全画面test_results対応済み: ログ・動画録画(webm)・JSONサマリー自動保存。遅延コピーパターンで動画確定後に保存）

---

## 11. 参照ファイル

| ファイル | 内容 |
|---------|------|
| `MODEL_EXPORT.md` | 汎用モデル輸出ガイド（5フェーズ方式・CLAUDE.mdテンプレート・方式選択基準） |
| `E2E_ANALYSIS_METHODOLOGY.md` | E2E解析メソドロジー（Phase1-3詳細手法・テンプレート・トラブルシューティング） |
| `ログイン/ARCHITECTURE.md` | システム全体設計書 |
| `ログイン/README.md` | セットアップ・使い方ガイド |
| `ログイン/ANALYSIS_REPORT.md` | ログイン画面 解析レポート |
| `ログイン/TEST_DESIGN.md` | ログイン画面 テスト設計書（TH-L01〜L05） |
| `ログイン/FULL_TEST_CHECKLIST.md` | ログイン画面 統合チェックリスト |
| `請求書/請求書一覧/CLAUDE.md` | セッション管理（タスク分割・コンテキスト節約・画面構造要約） |
| `請求書/請求書一覧/ANALYSIS_REPORT_INVOICES_1.md` | 請求書一覧画面 解析レポート |
| `請求書/請求書一覧/ANALYSIS_REPORT_INVOICE_DETAIL.md` | 請求書詳細+作成自動化 解析レポート |
| `請求書/請求書一覧/generated_tests/TEST_DESIGN_INVOICE_LIST.md` | 一覧テスト設計書（TH-IL01〜IL17） |
| `請求書/請求書一覧/generated_tests/FULL_TEST_CHECKLIST_INVOICE_LIST.md` | 一覧統合チェックリスト |
| `請求書/請求書一覧/generated_tests/TEST_DESIGN_INVOICE_DETAIL.md` | 詳細テスト設計書（TH-ID01〜ID15） |
| `請求書/請求書一覧/generated_tests/FULL_TEST_CHECKLIST_INVOICE_DETAIL.md` | 詳細統合チェックリスト |
| `請求書/請求書一覧/請求書作成/CSVから新規作成/TEST_DESIGN_CSV_IMPORT.md` | CSVインポートテスト設計書（TH-CI01〜CI05） |
| `請求書/請求書一覧/請求書作成/CSVから新規作成/FULL_TEST_CHECKLIST_CSV_IMPORT.md` | CSVインポート統合チェックリスト |
| `請求書/請求書一覧/その他の操作/共通添付ファイルの一括添付/TEST_DESIGN.md` | 共通添付ファイルテスト設計書（全55テスト） |
| `請求書/請求書一覧/その他の操作/共通添付ファイルの一括添付/FULL_TEST_CHECKLIST.md` | 共通添付ファイル統合チェックリスト（135項目） |
| `取引先/CLAUDE.md` | セッション管理（画面構造・技術知見・テスト一覧） |
| `取引先/ANALYSIS_REPORT_PARTNERS.md` | 取引先画面 解析レポート |
| `取引先/TEST_DESIGN.md` | 取引先画面 テスト設計書（TH-PL01〜PL19） |
| `取引先/FULL_TEST_CHECKLIST.md` | 取引先画面 統合チェックリスト |
| `帳票レイアウト/CLAUDE.md` | セッション管理（iframe知見・テスト一覧） |
| `帳票レイアウト/ANALYSIS_REPORT_DESIGN.md` | 帳票レイアウト画面 解析レポート |
| `帳票レイアウト/TEST_DESIGN.md` | 帳票レイアウト画面 テスト設計書（TH-DL01〜DL20） |
| `帳票レイアウト/FULL_TEST_CHECKLIST.md` | 帳票レイアウト画面 統合チェックリスト |
| `請求書/請求書一覧/請求書作成/PDFを取り込む/CLAUDE.md` | セッション管理（2モード構造・iframe知見・テスト一覧） |
| `請求書/請求書一覧/請求書作成/PDFを取り込む/ANALYSIS_REPORT_PDF_ORGANIZER.md` | PDF取り込み画面 解析レポート |
| `請求書/請求書一覧/請求書作成/PDFを取り込む/TEST_DESIGN.md` | PDF取り込み画面 テスト設計書（TH-PO01〜PO27） |
| `請求書/請求書一覧/請求書作成/PDFを取り込む/FULL_TEST_CHECKLIST.md` | PDF取り込み画面 統合チェックリスト |

### テスト実行結果まとめ

| テスト | 件数 | 実行時間 |
|--------|------|----------|
| ログイン画面 | 5 PASS | 約8秒 |
| 請求書一覧画面 | 17 PASS | 約18秒 |
| 請求書詳細画面 | 15 PASS | 約25秒 |
| 請求書作成（pytest） | 5 PASS | 約113秒 |
| CSVインポート3件（統合） | 成功 | 約3.2分 |
| CSVインポート3000件 | 成功 | 約13分+BG5.5分 |
| 共通添付ファイル（正常系） | 4 PASS | 約2分 |
| 共通添付ファイル（異常系・境界値） | 9 PASS | 約2.5分 |
| 共通添付ファイル（DOM検証） | 8 PASS | 約2分 |
| 共通添付ファイル（ナビゲーション+開閉） | 10 PASS | 約3分 |
| 共通添付ファイル（複数請求書一括） | 3 PASS | 約1.5分 |
| 共通添付ファイル（エッジケース） | 4 PASS | 約1分 |
| 共通添付ファイル（ファイル名+拡張子） | 12 PASS | 約3分 |
| 共通添付ファイル（既存から選択タブ） | 5 PASS | 約1.5分 |
| 取引先一覧画面 | 19 PASS | 約93秒 |
| 帳票レイアウト画面 | 20 PASS | 約292秒 |
| PDF取り込み画面 | 27 PASS | 約364秒 |
| **合計** | **163 PASS** | |

> **テスト数の数え方について**: 上表の件数はサブテスト（内部パターン）を含む延べ件数。pytestの `test_` 関数単位では146関数（方式A: 98、方式B: 48）。詳細は `E2E_ANALYSIS_METHODOLOGY.md` 付録C参照。

> **TH-ID管理について**: 全163テストにTH-IDが付与されており、テスト実行時に各画面の `test_results/TH-XXNN/` フォルダへ動画録画(.webm)が自動保存される。方式A（pytest+conftest.py）は6画面、方式B（standalone scripts）は共通添付ファイル8ファイル（55テスト）が対応済み。TH-IDの体系はSection 9を参照。
