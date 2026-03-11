# WDL (WEBダウンロードサイト) プロダクト情報

## 基本情報

| 項目 | 内容 |
|------|------|
| 正式名称 | TOKIUM Webダウンロード |
| 略称 | WDL |
| 環境URL | `https://invoicing-wdl-staging.keihi.com` (staging) |
| 認証方式 | メール + パスワード（WDL独自ログイン。TOKIUM ID認証とは別） |
| 用途 | 請求書のWeb受領・閲覧・ダウンロード（受信者側ビューア） |
| 調査日 | 2026-03-11（受信ポスト詳細ページ追加） |

---

## 画面構成（3画面 + ドロワー）

### 1. 帳票（`/invoices`）

ログイン後のトップページ。テーブル一覧 + 検索フォーム（アコーディオン）。行クリックで帳票詳細ドロワーが開く。

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

### 受信ポスト詳細（`/invoice-posts/{UUID}`）

受信ポスト一覧の行クリックで遷移する独立ページ。帳票詳細（ドロワー）とは異なり、URLが変わる。

| 要素 | 内容 |
|------|------|
| パンくず | 「≪ 戻る | 受信ポスト > 詳細情報」 |
| H1 | 受信ポスト |
| 送付元 | 送付元名（H2） |
| 閲覧メールアドレス | (N/30) ユーザー名 + メールアドレスの一覧。最大30件 |
| 操作ボタン | 「+ 閲覧メールアドレスを追加/削除する」（メールアドレスの追加・削除） |
| 戻るボタン | 「≪ 戻る」で受信ポスト一覧に戻る |

※ 「閲覧権限変更依頼」は一覧の変更依頼列に表示されるステータス。受信ポスト詳細での操作は「閲覧メールアドレスを追加/削除する」ボタンから行う。変更依頼はTH側の取引先管理で承認/却下される。

### 帳票詳細ドロワー（行クリックで表示）

帳票一覧の行クリックで右サイドに開くドロワーパネル（600px幅）。URL変化なし（`/invoices`のまま）。

| セクション | 内容 |
|-----------|------|
| ヘッダー | 「帳票詳細」+ 送付元名 + 請求書番号 + ×閉じるボタン |
| 帳票ファイル | ファイルサイズ + **「ダウンロード」ボタン** + DL済みステータス・日時 |
| 帳票項目 | 請求書番号 / 送付元 / 合計金額 / 発行日 / 請求日 / 支払期日 / ファイル名（dt/dd形式） |
| 関連添付ファイル | ファイル一覧 + 各ファイルに**「保存」ボタン** |
| 基本情報 | 管理ID(UUID) / 受信日 |
| メモ | textarea（編集可）+ **「メモを保存する」ボタン** |

---

### 3. プロフィール（`/profile`）

右上ユーザー名クリック → ドロップダウン「プロフィール」で遷移。

| 要素 | 内容 |
|------|------|
| メールアドレス | 表示のみ（編集不可） |
| 氏名 | テキスト入力欄（編集可） |
| 送信ボタン | 「氏名を変更」 |
| パスワード変更 | 案内文のみ（「ログアウトして『パスワードを忘れた場合』へ」） |

※ ヘッダードロップダウンメニュー: プロフィール / ログアウト

---

## テスト観点（WDL固有）

### 重点観点
- **検索機能**: 12フィールドの組み合わせ検索、日付範囲、金額範囲
- **ダウンロード**: ファイルダウンロード機能（帳票画面の主機能）
- **ページネーション**: 4112件の大量データでのページ送り・表示件数変更
- **認証**: WDL独自ログイン（TH本体とは別ドメイン・別認証）

### 対象外になりやすい観点
- 管理者画面（WDLには存在しない）
- テナント切替（WDLは単一ドメイン）
- CRUD操作（WDLは閲覧・ダウンロード専用、データ作成は請求書発行側）

### WDLの画面制約（テスト設計時の注意）
- WDLは**3画面+ドロワー**（帳票一覧 + 受信ポスト一覧 + プロフィール + 帳票詳細ドロワー）
- 帳票詳細は**右サイドドロワー**（URL変化なし）。行クリックで開き、×で閉じる
- プロフィールは右上ユーザー名ドロップダウンからアクセス（サイドバーにはリンクなし）
- 閲覧権限変更依頼は受信ポスト画面から操作
- SPA構成: ログイン後URLが`/login`のまま変わらない → wait_for_url不可

### TH本体（dev.keihi.com）との関連
- 請求書発行（invoicing-staging.keihi.com）で作成した請求書がWDL側で受信される
- TH-951/954等のセキュリティチケットで「対象環境: TH / WDL」と両環境テストが必要になるケースあり

---

## 調査データ

| ファイル | パス |
|---------|------|
| 構造JSON | `e2e-screen-test/screen_investigation/wdl_screen_structure.json` |
| スクリーンショット | `e2e-screen-test/screen_investigation/screenshots/wdl/` |
| 調査スクリプト | `e2e-screen-test/screen_investigation/investigate_wdl.py` |
| プロフィール調査 | `e2e-screen-test/screen_investigation/investigate_wdl_profile.py` |
| 帳票詳細調査 | `e2e-screen-test/screen_investigation/investigate_wdl_detail.py` |
| 帳票詳細構造JSON | `e2e-screen-test/screen_investigation/wdl_detail_panel_structure.json` |
| スクリーンショット(設定) | `e2e-screen-test/screen_investigation/screenshots/wdl_settings/` |
| スクリーンショット(詳細) | `e2e-screen-test/screen_investigation/screenshots/wdl_detail/` |
| 受信ポスト詳細調査 | `e2e-screen-test/screen_investigation/investigate_wdl_invoice_post_detail.py` |
| 受信ポスト詳細JSON | `e2e-screen-test/screen_investigation/wdl_invoice_post_detail_investigation.json` |
| スクリーンショット(受信ポスト詳細) | `e2e-screen-test/screen_investigation/screenshots/wdl_invoice_post_detail/` |
| 画面構成一覧 | `Vault/10_Work/TOKIUM画面構成一覧.md` セクション6 |
