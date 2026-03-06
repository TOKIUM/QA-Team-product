# TOKIUM管理者画面 プロダクト情報

## 基本情報

| 項目 | 内容 |
|------|------|
| 正式名称 | TOKIUM管理者画面（システム設定） |
| 略称 | TH-admin |
| 環境URL | `https://{サブドメイン}.dev.keihi.com/admin/` (staging) |
| 認証方式 | TOKIUM ID + サブドメイン（管理者権限必要） |
| 用途 | テナント設定・ユーザー管理・会計出力設定・セキュリティ管理 |
| 調査日 | 2026-03-06 |

---

## 画面構成（テナント別19〜31画面）

ヘッダーの「システム設定」からアクセス。テナントにより利用可能画面が異なる。

### テナント別管理画面数

| テナント | admin画面数 | 備考 |
|---------|-----------|------|
| th-01（智片拓海TH連携） | 31 | フル機能（役職/部署/外貨/科目含む） |
| th-02（マルチテナント検証用1） | 24 | 役職/部署/外貨/科目なし |
| マルチテナント検証用2 | 19 | 役職/部署なし |
| tkti10 | 19 | 役職/部署なし |

### サイドバー（th-01: フル構成）

```
├── ユーザー・組織
│   ├── 従業員 (/members)
│   ├── 役職 (/posts)         ← th-02,th-04,tkti10になし
│   ├── 部署 (/groups)         ← th-02,th-04,tkti10になし
│   └── 参加者 (/companions)
├── 経費関連設定
│   ├── 支払口座 (/preferences/company_expense_accounts)
│   ├── 申請フォーム (/request_types)
│   ├── 申請フロー (/approval_flows)
│   ├── プロジェクト (/preferences/projects)
│   ├── 外貨 (/preferences/currencies)         ← th-02になし
│   ├── 科目 (/root_categories)                ← th-02になし
│   ├── 税区分 (/preferences/tax_categories)
│   ├── 自動入力科目 (/preferences/business_categories)
│   ├── 経費入力・レポート (/preferences/reports)
│   ├── 日当・手当 (/preferences/allowances)
│   ├── アラート (/preferences/alert_rules)
│   ├── IC乗車券オプション (/preferences/ic_card_option)
│   └── 付加情報 (/preferences/metadata)
├── 会計・出力
│   ├── 会計データ出力形式 (/preferences/export)
│   ├── 会計データ出力 (/preferences/analyses_config)
│   ├── 会計データ定期出力 (/accounting_data_scheduled_exports)
│   └── 仕訳フォーマット (/journal_entries)
├── その他設定
│   ├── 締め日 (/closing_dates)
│   ├── 電子帳簿保存法 (/e_doc_options)
│   ├── 一覧表示 (/preferences/list_options)
│   ├── 法人カード (/preferences/corporate_cards)
│   └── 汎用マスタ (/generic_fields/data_sets)
├── セキュリティ・ログ
│   ├── セキュリティ (/preferences/security/ip_restriction)
│   └── ログ (/activity_logs)
└── 契約・組織変更
    ├── 契約 (/payment)
    └── 組織変更の予約 (/kernels/organizations/reorganizations/changes)
```

---

## テスト観点（TH-admin固有）

### 重点観点
- **テナント依存**: テナントにより利用可能画面が異なる（19〜31画面）。テスト対象テナントの明記必須
- **マスタCRUD**: 従業員/部署/科目/税区分等のマスタデータ管理（追加/編集/削除）
- **マスタ削除の影響範囲**: マスタ削除→経費精算/インボイスの参照データ破損リスク（影響範囲チェックリスト5-1〜5-6）
- **承認フロー設計**: 申請フロー（条件分岐: 部署・金額・プロジェクト）の正しい動作
- **会計連携設定**: 会計データ出力形式・定期出力・仕訳フォーマットの設定
- **セキュリティ**: IP制限・アクセスログ
- **権限管理**: 管理者/一般ユーザーのアクセス制御
- **組織変更**: 組織変更の予約機能（部署異動・統廃合）

### 対象外になりやすい観点
- 一般ユーザー画面の動作（TH-expense/TH-invoice側の責務）
- 請求書発行機能（TH-invoicing側の責務）
- WDL側の動作（WDL側の責務）

### 他プロダクトとの関連
- **TH-expense**: 科目・税区分・申請フロー・プロジェクト等の設定が経費精算に直接影響
- **TH-invoice**: テナント設定でインボイス機能の有効/無効を制御。取引先マスタは別管理
- **全プロダクト共通**: 従業員マスタ・部署・権限設定が全プロダクトの基盤

---

## 調査データ

| ファイル | パス |
|---------|------|
| 構造JSON (th-01) | `e2e-screen-test/screen_investigation/screen_structure.json` |
| 構造JSON (th-02) | `e2e-screen-test/screen_investigation/th02_screen_structure.json` |
| 構造JSON (th-04) | `e2e-screen-test/screen_investigation/th04_screen_structure.json` |
| スクリーンショット (th-01) | `e2e-screen-test/screen_investigation/screenshots/` |
| スクリーンショット (th-02) | `e2e-screen-test/screen_investigation/screenshots/th02/` |
| スクリーンショット (th-04) | `e2e-screen-test/screen_investigation/screenshots/th04/` |
| 画面構成一覧 | `Vault/10_Work/TOKIUM画面構成一覧.md` セクション7 |
