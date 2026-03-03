# 帳票レイアウト画面 テスト設計書

**対象機能**: TOKIUM 請求書発行 帳票レイアウト画面
**対象URL**: https://invoicing-staging.keihi.com/invoices/design
**作成日**: 2026-02-18
**テスト項目数**: 20件（自動20件）

---

## 1. 機能仕様サマリー

### 1-1. 画面構成

```
帳票レイアウト画面 (/invoices/design)
├── ヘッダー: ロゴ(TOKIUM 請求書発行)、ユーザー名(池田尚人)、ヘルプリンク
├── サイドバー: 請求書、取引先、帳票レイアウト(active)
├── ユーティリティバー
│   ├── 戻るボタン（ブラウザバック動作）
│   └── パンくず: 帳票レイアウト > レイアウト選択
└── gallery iframe（外部ドメイン: tpmlyr.dev.components.asaservice.inc）
    ├── ツールバー
    │   ├── 検索バー: input[placeholder*="検索"]
    │   ├── グリッド/リスト表示切替: role="button" or .MuiToggleButton-root
    │   ├── 並べ替え: text=並べ替え
    │   └── 新規作成ボタン: button:has-text("新規作成")
    └── レイアウトカード: .MuiGrid-item（複数件）
        └── カードクリック → レイアウト詳細/編集に遷移
```

### 1-2. iframe操作の特徴

| 項目 | 詳細 |
|------|------|
| iframe取得 | `page.frame(name="gallery")` |
| ドメイン | tpmlyr.dev.components.asaservice.inc（クロスオリジン） |
| クリック | `bounding_box()` + `page.mouse.click()` が最確実 |
| 入力 | `fill()` が効かない場合 → `bounding_box` + `mouse.click` + `keyboard.type` |
| 待機 | 初回ロード8000ms、操作後3000ms + networkidle |

---

## 2. テストカテゴリ一覧

| カテゴリ | 内容 | 件数 | 実行方法 |
|---------|------|------|---------|
| A. 画面遷移・基本表示 | サイドバー遷移/URL直接/パンくず/戻る/サイドバーアクティブ | 5 | 自動 |
| B. gallery iframe | iframe存在/URL確認 | 2 | 自動 |
| C. iframe内コンテンツ | カード表示/件数/検索バー/新規作成/並べ替え/表示切替 | 6 | 自動 |
| D. 検索機能 | 入力操作/検索結果 | 2 | 自動 |
| E. カード操作 | カードクリック遷移 | 1 | 自動 |
| F. 表示切替 | リスト表示切替 | 1 | 自動 |
| G. ヘッダー | ロゴ/ユーザー名/ヘルプ | 1 | 自動 |
| H. ナビゲーション | サイドバーから他画面遷移 | 2 | 自動 |
| **合計** | | **20** | |

---

## 3. テストケース詳細

### カテゴリA: 画面遷移・基本表示（5件）

| TC-ID | テスト名 | 入力 | 期待結果 | 自動化 |
|-------|---------|------|---------|--------|
| TH-DL01 | 帳票レイアウト画面に遷移できる | サイドバー「帳票レイアウト」クリック | URL=/invoices/design | test_帳票レイアウト画面に遷移できる |
| TH-DL02 | URL直接アクセスで画面表示 | /invoices/designに直接アクセス | URL=/invoices/design | test_URL直接アクセスで画面表示 |
| TH-DL03 | パンくずが正しく表示される | /invoices/designにアクセス | パンくず「帳票レイアウト」リンク+「レイアウト選択」テキスト表示 | test_パンくずが正しく表示される |
| TH-DL04 | 戻るボタンが表示される | /invoices/designにアクセス | 「戻る」ボタン表示 | test_戻るボタンが表示される |
| TH-DL05 | サイドバーの帳票レイアウトがアクティブ | /invoices/designにアクセス | 請求書/取引先/帳票レイアウトリンク全て表示 | test_サイドバーの帳票レイアウトがアクティブ |

### カテゴリB: gallery iframe（2件）

| TC-ID | テスト名 | 入力 | 期待結果 | 自動化 |
|-------|---------|------|---------|--------|
| TH-DL06 | gallery iframeが存在する | /invoices/designにアクセス | frame(name="gallery")がnot None | test_gallery_iframeが存在する |
| TH-DL07 | gallery iframeのURLが正しい | /invoices/designにアクセス | iframe#galleryのsrcにtpmlyrまたはgallery含む | test_gallery_iframeのURLが正しい |

### カテゴリC: iframe内コンテンツ（6件）

| TC-ID | テスト名 | 入力 | 期待結果 | 自動化 |
|-------|---------|------|---------|--------|
| TH-DL08 | レイアウトカードが表示される | gallery iframe内確認 | .MuiGrid-item 1件以上存在 | test_レイアウトカードが表示される |
| TH-DL09 | レイアウトカードの件数確認 | gallery iframe内確認 | .MuiGrid-item 2件以上存在 | test_レイアウトカードの件数確認 |
| TH-DL10 | 検索バーが存在する | gallery iframe内確認 | input[placeholder*="検索"] 存在 | test_検索バーが存在する |
| TH-DL11 | 新規作成ボタンが存在する | gallery iframe内確認 | button:has-text("新規作成") or text=新規作成 存在 | test_新規作成ボタンが存在する |
| TH-DL12 | 並べ替えコントロールが存在する | gallery iframe内確認 | text=並べ替え 存在 | test_並べ替えコントロールが存在する |
| TH-DL13 | 表示切替ボタンが存在する | gallery iframe内確認 | role="button" or .MuiToggleButton-root or button 2つ以上 | test_表示切替ボタンが存在する |

### カテゴリD: 検索機能（2件）

| TC-ID | テスト名 | 入力 | 期待結果 | 自動化 |
|-------|---------|------|---------|--------|
| TH-DL14 | 検索バーに入力できる | bounding_box+click→keyboard.type("test") | input_valueに"test"含む | test_検索バーに入力できる |
| TH-DL15 | 検索で一致するレイアウトが表示される | fill("サンプル")で検索 | .MuiGrid-item 1件以上表示 | test_検索で一致するレイアウトが表示される |

### カテゴリE: カード操作（1件）

| TC-ID | テスト名 | 入力 | 期待結果 | 自動化 |
|-------|---------|------|---------|--------|
| TH-DL16 | レイアウトカードクリックで遷移する | 最初のカードをbounding_box+click | URL変化またはiframe内遷移 | test_レイアウトカードクリックで遷移する |

### カテゴリF: 表示切替（1件）

| TC-ID | テスト名 | 入力 | 期待結果 | 自動化 |
|-------|---------|------|---------|--------|
| TH-DL17 | リスト表示に切り替えできる | 2番目のトグルボタンクリック→1番目で戻す | 表示形式変更（エラーなし） | test_リスト表示に切り替えできる |

### カテゴリG: ヘッダー（1件）

| TC-ID | テスト名 | 入力 | 期待結果 | 自動化 |
|-------|---------|------|---------|--------|
| TH-DL18 | ヘッダーが表示される | /invoices/designにアクセス | ロゴ(TOKIUM 請求書発行)、ユーザー名(池田尚人)、ヘルプリンク表示 | test_ヘッダーが表示される |

### カテゴリH: ナビゲーション（2件）

| TC-ID | テスト名 | 入力 | 期待結果 | 自動化 |
|-------|---------|------|---------|--------|
| TH-DL19 | サイドバーから請求書画面に遷移できる | 「請求書」(exact=True).firstクリック | URL=/invoices | test_サイドバーから請求書画面に遷移できる |
| TH-DL20 | サイドバーから取引先画面に遷移できる | 「取引先」クリック | URL=/partners | test_サイドバーから取引先画面に遷移できる |

---

## 4. テスト関数とTC-IDの対応

| TC-ID | テスト関数名 | ファイル |
|-------|------------|---------|
| TH-DL01 | test_帳票レイアウト画面に遷移できる | test_design_list.py |
| TH-DL02 | test_URL直接アクセスで画面表示 | test_design_list.py |
| TH-DL03 | test_パンくずが正しく表示される | test_design_list.py |
| TH-DL04 | test_戻るボタンが表示される | test_design_list.py |
| TH-DL05 | test_サイドバーの帳票レイアウトがアクティブ | test_design_list.py |
| TH-DL06 | test_gallery_iframeが存在する | test_design_list.py |
| TH-DL07 | test_gallery_iframeのURLが正しい | test_design_list.py |
| TH-DL08 | test_レイアウトカードが表示される | test_design_list.py |
| TH-DL09 | test_レイアウトカードの件数確認 | test_design_list.py |
| TH-DL10 | test_検索バーが存在する | test_design_list.py |
| TH-DL11 | test_新規作成ボタンが存在する | test_design_list.py |
| TH-DL12 | test_並べ替えコントロールが存在する | test_design_list.py |
| TH-DL13 | test_表示切替ボタンが存在する | test_design_list.py |
| TH-DL14 | test_検索バーに入力できる | test_design_list.py |
| TH-DL15 | test_検索で一致するレイアウトが表示される | test_design_list.py |
| TH-DL16 | test_レイアウトカードクリックで遷移する | test_design_list.py |
| TH-DL17 | test_リスト表示に切り替えできる | test_design_list.py |
| TH-DL18 | test_ヘッダーが表示される | test_design_list.py |
| TH-DL19 | test_サイドバーから請求書画面に遷移できる | test_design_list.py |
| TH-DL20 | test_サイドバーから取引先画面に遷移できる | test_design_list.py |
