# PDF取り込み画面 テストチェックリスト

**対象機能**: TOKIUM 請求書発行 PDF取り込み画面（請求書作成の分岐の1つ）
**対象URL**:
  - ファイル分割: https://invoicing-staging.keihi.com/invoices/pdf-organizer/separation
  - ファイルリネーム: https://invoicing-staging.keihi.com/invoices/pdf-organizer/rename
**作成日**: 2026-02-18
**最終更新**: 2026-02-18
**テスト項目数**: 27件（自動27件）

### テスト結果サマリー

| カテゴリ | 内容 | 件数 | PASS | FAIL | 未実施 | 実行方法 |
|---------|------|------|------|------|--------|---------|
| A. 分割モード基本表示 | URL直接/リダイレクト/見出し/パンくず/モード切替リンク | 5 | 5 | 0 | 0 | 自動 |
| B. リネームモード基本表示 | URL直接/見出し/パンくず/モード切替リンク | 4 | 4 | 0 | 0 | 自動 |
| C. モード切替 | 分割→リネーム/リネーム→分割 | 2 | 2 | 0 | 0 | 自動 |
| D. パンくず遷移 | 請求書リンク/PDFを取り込むリンク | 2 | 2 | 0 | 0 | 自動 |
| E. ヘッダー・サイドバー | ヘッダー要素/サイドバーリンク/ナビゲーション | 3 | 3 | 0 | 0 | 自動 |
| F. iframe存在確認 | 分割モード/リネームモード/src確認 | 3 | 3 | 0 | 0 | 自動 |
| G. iframe内（分割） | ステッパー/案内テキスト/キャンセル/次へ(disabled) | 4 | 4 | 0 | 0 | 自動 |
| H. iframe内（リネーム） | ステッパー/案内テキスト/キャンセル/次へ(disabled) | 4 | 4 | 0 | 0 | 自動 |
| **合計** | | **27** | **27** | **0** | **0** | |

---

## A. 分割モード基本表示（自動・5件）

| TC-ID | 画面 | 確認すること | 確認対象 | 詳細1 | 詳細2 | テスト実行手順 | 期待値 | 結果 | 実行日 | エビデンス |
|-------|------|------------|---------|-------|-------|--------------|--------|------|--------|-----------|
| TH-PO01 | /separation | ファイル分割モードにURL直接アクセスできる | URL遷移 | /separation直接goto | URL確認 | /separationにアクセス→URL確認 | URL=/invoices/pdf-organizer/separation | PASS | 2026-02-18 | ログ |
| TH-PO02 | /pdf-organizer | pdf-organizerリダイレクト | リダイレクト | /pdf-organizerにgoto | /separationにリダイレクト確認 | /pdf-organizerにアクセス→URL確認 | URL=/invoices/pdf-organizer/separation | PASS | 2026-02-18 | ログ |
| TH-PO03 | /separation | ファイル分割モードの見出しが表示される | 見出し | heading name=「PDFを分割して取り込む」 | visible確認 | /separationにアクセス→見出し確認 | 「PDFを分割して取り込む」表示 | PASS | 2026-02-18 | ログ |
| TH-PO04 | /separation | ファイル分割モードのパンくずが正しい | パンくず | #main-content nav内「請求書」「PDFを取り込む」リンク | 「ファイル分割」テキスト(span) | /separationにアクセス→パンくず要素確認 | リンク2件+テキスト表示 | PASS | 2026-02-18 | ログ |
| TH-PO05 | /separation | ファイル分割モードのモード切替リンクが表示される | モード切替リンク | link name=「ファイルリネームに切り替える」 | visible確認 | /separationにアクセス→リンク確認 | 「ファイルリネームに切り替える」表示 | PASS | 2026-02-18 | ログ |

## B. リネームモード基本表示（自動・4件）

| TC-ID | 画面 | 確認すること | 確認対象 | 詳細1 | 詳細2 | テスト実行手順 | 期待値 | 結果 | 実行日 | エビデンス |
|-------|------|------------|---------|-------|-------|--------------|--------|------|--------|-----------|
| TH-PO06 | /rename | ファイルリネームモードにURL直接アクセスできる | URL遷移 | /rename直接goto | URL確認 | /renameにアクセス→URL確認 | URL=/invoices/pdf-organizer/rename | PASS | 2026-02-18 | ログ |
| TH-PO07 | /rename | ファイルリネームモードの見出しが表示される | 見出し | heading name=「PDFをリネームして取り込む」 | visible確認 | /renameにアクセス→見出し確認 | 「PDFをリネームして取り込む」表示 | PASS | 2026-02-18 | ログ |
| TH-PO08 | /rename | ファイルリネームモードのパンくずが正しい | パンくず | #main-content nav内「請求書」「PDFを取り込む」リンク | 「ファイルリネーム」テキスト(span) | /renameにアクセス→パンくず要素確認 | リンク2件+テキスト表示 | PASS | 2026-02-18 | ログ |
| TH-PO09 | /rename | ファイルリネームモードのモード切替リンクが表示される | モード切替リンク | link name=「ファイル分割に切り替える」 | visible確認 | /renameにアクセス→リンク確認 | 「ファイル分割に切り替える」表示 | PASS | 2026-02-18 | ログ |

## C. モード切替（自動・2件）

| TC-ID | 画面 | 確認すること | 確認対象 | 詳細1 | 詳細2 | テスト実行手順 | 期待値 | 結果 | 実行日 | エビデンス |
|-------|------|------------|---------|-------|-------|--------------|--------|------|--------|-----------|
| TH-PO10 | /separation→/rename | 分割モードからリネームモードに切替できる | モード切替 | 「ファイルリネームに切り替える」クリック | URL+見出し変化確認 | /separationにアクセス→切替リンククリック→URL+見出し確認 | URL=/rename、見出し「PDFをリネームして取り込む」 | PASS | 2026-02-18 | ログ |
| TH-PO11 | /rename→/separation | リネームモードから分割モードに切替できる | モード切替 | 「ファイル分割に切り替える」クリック | URL+見出し変化確認 | /renameにアクセス→切替リンククリック→URL+見出し確認 | URL=/separation、見出し「PDFを分割して取り込む」 | PASS | 2026-02-18 | ログ |

## D. パンくず遷移（自動・2件）

| TC-ID | 画面 | 確認すること | 確認対象 | 詳細1 | 詳細2 | テスト実行手順 | 期待値 | 結果 | 実行日 | エビデンス |
|-------|------|------------|---------|-------|-------|--------------|--------|------|--------|-----------|
| TH-PO12 | /separation | パンくず請求書リンクで一覧画面に遷移 | パンくず遷移 | #main-content nav内「請求書」クリック | URL確認 | /separationにアクセス→パンくず「請求書」クリック→URL確認 | URL=/invoices | PASS | 2026-02-18 | ログ |
| TH-PO13 | /separation | パンくずPDFを取り込むリンクで遷移 | パンくず遷移 | #main-content nav内「PDFを取り込む」クリック | URL確認 | /separationにアクセス→パンくず「PDFを取り込む」クリック→URL確認 | URL=/invoices/pdf-organizer | PASS | 2026-02-18 | ログ |

## E. ヘッダー・サイドバー（自動・3件）

| TC-ID | 画面 | 確認すること | 確認対象 | 詳細1 | 詳細2 | テスト実行手順 | 期待値 | 結果 | 実行日 | エビデンス |
|-------|------|------------|---------|-------|-------|--------------|--------|------|--------|-----------|
| TH-PO14 | /separation | ヘッダーに主要要素が表示される | ヘッダー | ロゴ(TOKIUM 請求書発行)、ユーザー名(池田尚人.first) | ヘルプリンク(TOKIUM 請求書発行 - ヘルプセンター) | /separationにアクセス→各要素visible確認 | ロゴ+ユーザー名+ヘルプ表示 | PASS | 2026-02-18 | ログ |
| TH-PO15 | /separation | サイドバーにナビゲーションリンクが表示される | サイドバー | 請求書(exact=True).first、取引先.first、帳票レイアウト.first | 3リンクvisible確認 | /separationにアクセス→各リンクvisible確認 | 3リンク全て表示 | PASS | 2026-02-18 | ログ |
| TH-PO16 | /separation | サイドバーから請求書画面に遷移できる | ナビゲーション | 「請求書」(exact=True).firstクリック | URL確認 | /separationにアクセス→「請求書」クリック→URL確認 | URL=/invoices | PASS | 2026-02-18 | ログ |

## F. iframe存在確認（自動・3件）

| TC-ID | 画面 | 確認すること | 確認対象 | 詳細1 | 詳細2 | テスト実行手順 | 期待値 | 結果 | 実行日 | エビデンス |
|-------|------|------------|---------|-------|-------|--------------|--------|------|--------|-----------|
| TH-PO17 | /separation | organizer iframeが存在する（分割モード） | iframe | iframe#organizer attached確認 | frame(url含"organizer") not None | /separationにアクセス→iframe attached+frameオブジェクト取得確認 | iframe存在+frame取得成功 | PASS | 2026-02-18 | ログ |
| TH-PO18 | /rename | organizer iframeが存在する（リネームモード） | iframe | iframe#organizer attached確認 | frame(url含"organizer") not None | /renameにアクセス→iframe attached+frameオブジェクト取得確認 | iframe存在+frame取得成功 | PASS | 2026-02-18 | ログ |
| TH-PO19 | /separation | organizer iframeのsrcが正しい | iframe src | iframe#organizerのsrc属性取得 | src含"tpmlyr"かつ"organizer" | /separationにアクセス→src属性確認 | srcにtpmlyr+organizer含む | PASS | 2026-02-18 | ログ |

## G. iframe内・分割モード（自動・4件）

| TC-ID | 画面 | 確認すること | 確認対象 | 詳細1 | 詳細2 | テスト実行手順 | 期待値 | 結果 | 実行日 | エビデンス |
|-------|------|------------|---------|-------|-------|--------------|--------|------|--------|-----------|
| TH-PO20 | iframe内(分割) | ステッパーに3ステップが表示される | ステッパー | 「ファイルアップロード」「ファイルの分割」「プレビュー」 | 各.first visible確認 | /separation→iframe取得→各ステップテキスト確認 | 3ステップ全て表示 | PASS | 2026-02-18 | ログ |
| TH-PO21 | iframe内(分割) | 案内テキストが表示される | 案内テキスト | text=「アップロードするファイルを選択し」 | .first visible確認 | /separation→iframe取得→テキスト確認 | 案内テキスト表示 | PASS | 2026-02-18 | ログ |
| TH-PO22 | iframe内(分割) | キャンセルボタンが表示される | キャンセルボタン | button:has-text("キャンセル") | フォールバック: role="button" name="キャンセル" | /separation→iframe取得→ボタン確認 | キャンセルボタン表示 | PASS | 2026-02-18 | ログ |
| TH-PO23 | iframe内(分割) | 次へボタンが表示されdisabledである | 次へボタン | button:has-text("次へ") visible確認 | disabled確認（ファイル未選択） | /separation→iframe取得→ボタンvisible+disabled確認 | 「次へ」表示かつdisabled | PASS | 2026-02-18 | ログ |

## H. iframe内・リネームモード（自動・4件）

| TC-ID | 画面 | 確認すること | 確認対象 | 詳細1 | 詳細2 | テスト実行手順 | 期待値 | 結果 | 実行日 | エビデンス |
|-------|------|------------|---------|-------|-------|--------------|--------|------|--------|-----------|
| TH-PO24 | iframe内(リネーム) | ステッパーに2ステップが表示される | ステッパー | 「ファイルアップロード」「ファイル名の変換」 | 各.first visible確認 | /rename→iframe取得→各ステップテキスト確認 | 2ステップ全て表示 | PASS | 2026-02-18 | ログ |
| TH-PO25 | iframe内(リネーム) | 案内テキストが表示される | 案内テキスト | text=「アップロードするファイルを選択し」 | .first visible確認 | /rename→iframe取得→テキスト確認 | 案内テキスト表示 | PASS | 2026-02-18 | ログ |
| TH-PO26 | iframe内(リネーム) | キャンセルボタンが表示される | キャンセルボタン | button:has-text("キャンセル") | フォールバック: role="button" name="キャンセル" | /rename→iframe取得→ボタン確認 | キャンセルボタン表示 | PASS | 2026-02-18 | ログ |
| TH-PO27 | iframe内(リネーム) | 次へボタンが表示されdisabledである | 次へボタン | button:has-text("次へ") visible確認 | disabled確認（ファイル未選択） | /rename→iframe取得→ボタンvisible+disabled確認 | 「次へ」表示かつdisabled | PASS | 2026-02-18 | ログ |
