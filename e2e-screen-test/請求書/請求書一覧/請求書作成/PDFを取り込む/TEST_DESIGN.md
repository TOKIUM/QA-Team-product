# PDF取り込み画面 テスト設計書

**対象機能**: TOKIUM 請求書発行 PDF取り込み画面（請求書作成の分岐の1つ）
**対象URL**:
  - ファイル分割: https://invoicing-staging.keihi.com/invoices/pdf-organizer/separation
  - ファイルリネーム: https://invoicing-staging.keihi.com/invoices/pdf-organizer/rename
**作成日**: 2026-02-18
**テスト項目数**: 27件（自動27件）

---

## 1. 機能仕様サマリー

### 1-1. 請求書作成における位置づけ

```
請求書作成
├── CSVインポート（/invoices/import）
└── PDF取り込み（/invoices/pdf-organizer/）  ← 本画面
    ├── ファイル分割（/separation）… 3ステップ
    └── ファイルリネーム（/rename）… 2ステップ

※ /invoices/pdf-organizer は /separation にリダイレクト
```

### 1-2. 画面構成

```
PDF取り込み画面
├── ヘッダー: ロゴ(TOKIUM 請求書発行)、ユーザー名(池田尚人)、ヘルプリンク
├── サイドバー: 請求書、取引先、帳票レイアウト
├── パンくず: 請求書 > PDFを取り込む > ファイル分割 / ファイルリネーム
├── 見出し
│   ├── 分割モード: 「PDFを分割して取り込む」
│   └── リネームモード: 「PDFをリネームして取り込む」
├── モード切替リンク
│   ├── 分割→リネーム: 「ファイルリネームに切り替える」
│   └── リネーム→分割: 「ファイル分割に切り替える」
└── organizer iframe（外部ドメイン: tpmlyr.dev.components.asaservice.inc）
    ├── ステッパー
    │   ├── 分割モード: ファイルアップロード → ファイルの分割 → プレビュー（3ステップ）
    │   └── リネームモード: ファイルアップロード → ファイル名の変換（2ステップ）
    ├── 案内テキスト: 「アップロードするファイルを選択し…」
    └── ボタン: キャンセル / 次へ（初期状態disabled）
```

### 1-3. iframe操作の特徴

| 項目 | 詳細 |
|------|------|
| iframe取得 | `page.frame(name="organizer")` |
| ⚠️ 禁止パターン | `page.frame(url=lambda url: "organizer" in url)` はNG（メインURL にもマッチ） |
| フォールバック | `page.frame(url=lambda url: "tpmlyr.dev.components.asaservice.inc" in url)` |
| ドメイン | tpmlyr.dev.components.asaservice.inc（クロスオリジン） |
| 待機 | 初回ロード8000ms、操作後3000ms + networkidle |

---

## 2. テストカテゴリ一覧

| カテゴリ | 内容 | 件数 | 実行方法 |
|---------|------|------|---------|
| A. 分割モード基本表示 | URL直接/リダイレクト/見出し/パンくず/モード切替リンク | 5 | 自動 |
| B. リネームモード基本表示 | URL直接/見出し/パンくず/モード切替リンク | 4 | 自動 |
| C. モード切替 | 分割→リネーム/リネーム→分割 | 2 | 自動 |
| D. パンくず遷移 | 請求書リンク/PDFを取り込むリンク | 2 | 自動 |
| E. ヘッダー・サイドバー | ヘッダー/サイドバー/ナビゲーション | 3 | 自動 |
| F. iframe存在確認 | 分割モード/リネームモード/src確認 | 3 | 自動 |
| G. iframe内（分割） | ステッパー/案内テキスト/キャンセル/次へ(disabled) | 4 | 自動 |
| H. iframe内（リネーム） | ステッパー/案内テキスト/キャンセル/次へ(disabled) | 4 | 自動 |
| **合計** | | **27** | |

---

## 3. テストケース詳細

### カテゴリA: 分割モード基本表示（5件）

| TC-ID | テスト名 | 入力 | 期待結果 | 自動化 |
|-------|---------|------|---------|--------|
| TH-PO01 | ファイル分割モードにURL直接アクセスできる | /separation直接アクセス | URL=/separation | test_ファイル分割モードにURL直接アクセスできる |
| TH-PO02 | pdf_organizerリダイレクト | /pdf-organizerにアクセス | /separationにリダイレクト | test_pdf_organizerリダイレクト |
| TH-PO03 | ファイル分割モードの見出し | /separationにアクセス | 「PDFを分割して取り込む」表示 | test_ファイル分割モードの見出し |
| TH-PO04 | ファイル分割モードのパンくず | /separationにアクセス | 「請求書」「PDFを取り込む」リンク+「ファイル分割」テキスト | test_ファイル分割モードのパンくず |
| TH-PO05 | ファイル分割モードのモード切替リンク | /separationにアクセス | 「ファイルリネームに切り替える」リンク表示 | test_ファイル分割モードのモード切替リンク |

### カテゴリB: リネームモード基本表示（4件）

| TC-ID | テスト名 | 入力 | 期待結果 | 自動化 |
|-------|---------|------|---------|--------|
| TH-PO06 | ファイルリネームモードにURL直接アクセスできる | /rename直接アクセス | URL=/rename | test_ファイルリネームモードにURL直接アクセスできる |
| TH-PO07 | ファイルリネームモードの見出し | /renameにアクセス | 「PDFをリネームして取り込む」表示 | test_ファイルリネームモードの見出し |
| TH-PO08 | ファイルリネームモードのパンくず | /renameにアクセス | 「請求書」「PDFを取り込む」リンク+「ファイルリネーム」テキスト | test_ファイルリネームモードのパンくず |
| TH-PO09 | ファイルリネームモードのモード切替リンク | /renameにアクセス | 「ファイル分割に切り替える」リンク表示 | test_ファイルリネームモードのモード切替リンク |

### カテゴリC: モード切替（2件）

| TC-ID | テスト名 | 入力 | 期待結果 | 自動化 |
|-------|---------|------|---------|--------|
| TH-PO10 | 分割モードからリネームモードに切替できる | 切替リンククリック | URL=/rename、見出し「PDFをリネームして取り込む」 | test_分割モードからリネームモードに切替できる |
| TH-PO11 | リネームモードから分割モードに切替できる | 切替リンククリック | URL=/separation、見出し「PDFを分割して取り込む」 | test_リネームモードから分割モードに切替できる |

### カテゴリD: パンくず遷移（2件）

| TC-ID | テスト名 | 入力 | 期待結果 | 自動化 |
|-------|---------|------|---------|--------|
| TH-PO12 | パンくず請求書リンクで一覧画面に遷移 | パンくず「請求書」クリック | URL=/invoices | test_パンくず請求書リンクで一覧画面に遷移 |
| TH-PO13 | パンくずPDFを取り込むリンクで遷移 | パンくず「PDFを取り込む」クリック | URL=/invoices/pdf-organizer | test_パンくずPDFを取り込むリンクで遷移 |

### カテゴリE: ヘッダー・サイドバー（3件）

| TC-ID | テスト名 | 入力 | 期待結果 | 自動化 |
|-------|---------|------|---------|--------|
| TH-PO14 | ヘッダーが表示される | /separationにアクセス | ロゴ+ユーザー名(池田尚人)+ヘルプリンク表示 | test_ヘッダーが表示される |
| TH-PO15 | サイドバーが表示される | /separationにアクセス | 請求書/取引先/帳票レイアウト 3リンク表示 | test_サイドバーが表示される |
| TH-PO16 | サイドバーから請求書画面に遷移できる | 「請求書」クリック | URL=/invoices | test_サイドバーから請求書画面に遷移できる |

### カテゴリF: iframe存在確認（3件）

| TC-ID | テスト名 | 入力 | 期待結果 | 自動化 |
|-------|---------|------|---------|--------|
| TH-PO17 | organizer iframeが存在する（分割モード） | /separationにアクセス | iframe#organizer attached + frameオブジェクト取得 | test_organizer_iframeが存在する_分割モード |
| TH-PO18 | organizer iframeが存在する（リネームモード） | /renameにアクセス | iframe#organizer attached + frameオブジェクト取得 | test_organizer_iframeが存在する_リネームモード |
| TH-PO19 | organizer iframeのsrcが正しい | /separationにアクセス | srcにtpmlyr+organizer含む | test_organizer_iframeのsrcが正しい |

### カテゴリG: iframe内・分割モード（4件）

| TC-ID | テスト名 | 入力 | 期待結果 | 自動化 |
|-------|---------|------|---------|--------|
| TH-PO20 | 分割モードのステッパー表示 | iframe内確認 | 「ファイルアップロード」「ファイルの分割」「プレビュー」3ステップ表示 | test_分割モードのステッパー表示 |
| TH-PO21 | 分割モードの案内テキスト | iframe内確認 | 「アップロードするファイルを選択し」テキスト表示 | test_分割モードの案内テキスト |
| TH-PO22 | 分割モードのキャンセルボタン | iframe内確認 | 「キャンセル」ボタン表示 | test_分割モードのキャンセルボタン |
| TH-PO23 | 分割モードの次へボタン | iframe内確認 | 「次へ」ボタン表示かつdisabled（ファイル未選択） | test_分割モードの次へボタン |

### カテゴリH: iframe内・リネームモード（4件）

| TC-ID | テスト名 | 入力 | 期待結果 | 自動化 |
|-------|---------|------|---------|--------|
| TH-PO24 | リネームモードのステッパー表示 | iframe内確認 | 「ファイルアップロード」「ファイル名の変換」2ステップ表示 | test_リネームモードのステッパー表示 |
| TH-PO25 | リネームモードの案内テキスト | iframe内確認 | 「アップロードするファイルを選択し」テキスト表示 | test_リネームモードの案内テキスト |
| TH-PO26 | リネームモードのキャンセルボタン | iframe内確認 | 「キャンセル」ボタン表示 | test_リネームモードのキャンセルボタン |
| TH-PO27 | リネームモードの次へボタン | iframe内確認 | 「次へ」ボタン表示かつdisabled（ファイル未選択） | test_リネームモードの次へボタン |

---

## 4. テスト関数とTC-IDの対応

| TC-ID | テスト関数名 | ファイル |
|-------|------------|---------|
| TH-PO01 | test_ファイル分割モードにURL直接アクセスできる | test_pdf_organizer.py |
| TH-PO02 | test_pdf_organizerリダイレクト | test_pdf_organizer.py |
| TH-PO03 | test_ファイル分割モードの見出し | test_pdf_organizer.py |
| TH-PO04 | test_ファイル分割モードのパンくず | test_pdf_organizer.py |
| TH-PO05 | test_ファイル分割モードのモード切替リンク | test_pdf_organizer.py |
| TH-PO06 | test_ファイルリネームモードにURL直接アクセスできる | test_pdf_organizer.py |
| TH-PO07 | test_ファイルリネームモードの見出し | test_pdf_organizer.py |
| TH-PO08 | test_ファイルリネームモードのパンくず | test_pdf_organizer.py |
| TH-PO09 | test_ファイルリネームモードのモード切替リンク | test_pdf_organizer.py |
| TH-PO10 | test_分割モードからリネームモードに切替できる | test_pdf_organizer.py |
| TH-PO11 | test_リネームモードから分割モードに切替できる | test_pdf_organizer.py |
| TH-PO12 | test_パンくず請求書リンクで一覧画面に遷移 | test_pdf_organizer.py |
| TH-PO13 | test_パンくずPDFを取り込むリンクで遷移 | test_pdf_organizer.py |
| TH-PO14 | test_ヘッダーが表示される | test_pdf_organizer.py |
| TH-PO15 | test_サイドバーが表示される | test_pdf_organizer.py |
| TH-PO16 | test_サイドバーから請求書画面に遷移できる | test_pdf_organizer.py |
| TH-PO17 | test_organizer_iframeが存在する_分割モード | test_pdf_organizer.py |
| TH-PO18 | test_organizer_iframeが存在する_リネームモード | test_pdf_organizer.py |
| TH-PO19 | test_organizer_iframeのsrcが正しい | test_pdf_organizer.py |
| TH-PO20 | test_分割モードのステッパー表示 | test_pdf_organizer.py |
| TH-PO21 | test_分割モードの案内テキスト | test_pdf_organizer.py |
| TH-PO22 | test_分割モードのキャンセルボタン | test_pdf_organizer.py |
| TH-PO23 | test_分割モードの次へボタン | test_pdf_organizer.py |
| TH-PO24 | test_リネームモードのステッパー表示 | test_pdf_organizer.py |
| TH-PO25 | test_リネームモードの案内テキスト | test_pdf_organizer.py |
| TH-PO26 | test_リネームモードのキャンセルボタン | test_pdf_organizer.py |
| TH-PO27 | test_リネームモードの次へボタン | test_pdf_organizer.py |
