# WDL (WEBダウンロードサイト) プロダクト情報

## 基本情報

| 項目 | 内容 |
|------|------|
| 正式名称 | TOKIUM Webダウンロード |
| 略称 | WDL |
| 環境URL | `https://invoicing-wdl-staging.keihi.com` (staging) |
| 認証方式 | メール + パスワード（WDL独自ログイン。TOKIUM ID認証とは別） |
| 用途 | 請求書のWeb受領・閲覧・ダウンロード（受信者側ビューア） |
| 調査日 | 2026-03-06 |

---

## 画面構成（2画面）

### 1. 帳票（`/invoices`）

ログイン後のトップページ。テーブル一覧 + 検索フォーム（アコーディオン）。

#### テーブル列（9列）
| 列名 | 型 | 備考 |
|------|-----|------|
| 受信日 | 日付 | |
| ダウンロード済み | アイコン | チェックマーク表示 |
| 送付元 | テキスト | |
| 添付 | 数値 | 添付ファイル数 |
| 請求書番号 | テキスト | |
| 合計金額 | 金額 | 円表示 |
| 支払期日 | 日付 | |
| ファイル名 | テキスト | PDF名 |
| メモ | テキスト | |

#### 検索フォーム（12フィールド）
| フィールド名 | input name | 型 |
|-------------|-----------|-----|
| 受信ポスト | invoicePostId | select |
| 請求書番号 | documentNumber | text |
| 未ダウンロード | notDownloaded | checkbox |
| 合計金額（最小） | totalAmountMin | text |
| 合計金額（最大） | totalAmountMax | text |
| 請求日FROM | billedAtFrom | date |
| 請求日TO | billedAtTo | date |
| 支払期日FROM | dueAtFrom | date |
| 支払期日TO | dueAtTo | date |
| 受信日FROM | receivedAtFrom | date |
| 受信日TO | receivedAtTo | date |
| メモ | memo | text |

#### ボタン
- 検索条件（アコーディオン開閉）
- 検索条件を追加
- この条件で検索
- リセット

#### ページネーション
- 表示件数: 10件（変更可能）
- 調査時データ: 4112件

---

### 2. 受信ポスト（`/invoice-posts`）

送付元の管理画面。テーブル一覧 + 検索フォーム（アコーディオン）。

#### テーブル列（4列）
| 列名 | 型 | 備考 |
|------|-----|------|
| 送付元名 | テキスト | |
| 変更依頼 | アイコン | ダッシュ or 表示 |
| 未読 | 数値/チェック | 未読件数（青リンク） |
| 閲覧可能 | 数値 | 閲覧可能ユーザー数 |

#### 検索フォーム（3フィールド）
| フィールド名 | input name | 型 |
|-------------|-----------|-----|
| 送付元名 | senderName | text |
| 受信者メール | recipientEmail | text |
| 変更依頼あり | hasChangeRequest | checkbox |

#### ページネーション
- 表示件数: 10件（変更可能）
- 調査時データ: 347件

---

## テスト観点（WDL固有）

### 重点観点
- **検索機能**: 12フィールドの組み合わせ検索、日付範囲、金額範囲
- **ダウンロード**: ファイルダウンロード機能（帳票画面の主機能）
- **ページネーション**: 4112件の大量データでのページ送り・表示件数変更
- **認証**: WDL独自ログイン（TH本体とは別ドメイン・別認証）

### 対象外になりやすい観点
- 管理者画面（WDLには存在しない可能性）
- テナント切替（WDLは単一ドメイン）
- CRUD操作（WDLは閲覧・ダウンロード専用、データ作成は請求書発行側）

### TH本体（dev.keihi.com）との関連
- 請求書発行（invoicing-staging.keihi.com）で作成した請求書がWDL側で受信される
- TH-951等のセキュリティチケットで「対象環境: TH / WDL」と両環境テストが必要になるケースあり

---

## 調査データ

| ファイル | パス |
|---------|------|
| 構造JSON | `e2e-screen-test/screen_investigation/wdl_screen_structure.json` |
| スクリーンショット | `e2e-screen-test/screen_investigation/screenshots/wdl/` |
| 調査スクリプト | `e2e-screen-test/screen_investigation/investigate_wdl.py` |
| 画面構成一覧 | `Vault/10_Work/TOKIUM画面構成一覧.md` セクション6 |
