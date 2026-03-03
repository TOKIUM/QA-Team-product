# TH ログイン方法の整理

**作成日**: 2026-03-03
**対象環境**: dev（`dev.keihi.com`）/ invoicing-staging（`invoicing-staging.keihi.com`）
**根拠**: 実機調査（2026-03-02〜03）+ TH-898仕様書

---

## 1. ログイン方法の全体像

THには**2つのシステム**と**5つのログイン方法**がある。

```
┌─────────────────────────────────────────────────────┐
│  TOKIUM 請求書発行 (invoicing-staging.keihi.com)     │
│                                                      │
│  ① invoicing直接ログイン（メール+PW）                  │
│  ② TOKIUM IDでログイン → dev.keihi.comへSSO           │
│                                                      │
└─────────────────────────────────────────────────────┘
              │ ②のリダイレクト先
              ▼
┌─────────────────────────────────────────────────────┐
│  TOKIUM ID (dev.keihi.com)                           │
│                                                      │
│  ③ TOKIUM ID直接ログイン（メール+PW）                  │
│  ④ Googleでログイン                                   │
│  ⑤ Microsoft 365でログイン                            │
│                                                      │
│  ＋ サブドメイン経由ログイン                             │
│    → [sd].dev.keihi.com（メール+PWのみ）               │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## 2. 各ログイン方法の詳細

### ① invoicing直接ログイン

| 項目 | 内容 |
|------|------|
| **入口** | `invoicing-staging.keihi.com/login` |
| **認証方式** | メールアドレス + パスワード |
| **ログイン先** | invoicing-staging.keihi.com/invoices（請求書一覧） |
| **サブドメイン** | 不要 |
| **特徴** | invoicing独自の認証。TOKIUM ID（dev.keihi.com）を経由しない |

### ② TOKIUM IDでログイン（invoicing経由）

| 項目 | 内容 |
|------|------|
| **入口** | invoicingログイン画面の「TOKIUM IDでログイン」ボタン |
| **認証方式** | SSO（invoicing → dev.keihi.com → SSOコールバック → invoicing） |
| **フロー** | 下記参照 |
| **ログイン先** | invoicing-staging.keihi.com/invoices（SSOコールバックで自動戻り） |
| **サブドメイン** | 不要（ただしサブドメイン必須アカウントは拒否される） |

```
invoicing/login → [TOKIUM IDでログイン]
  → invoicing/auth-redirect
  → dev.keihi.com/users/sign_in    ← ここでメール+PW入力
  → invoicing/auth/callback?token=...
  → invoicing/invoices              ← 最終着地点
```

### ③ TOKIUM ID直接ログイン

| 項目 | 内容 |
|------|------|
| **入口** | `dev.keihi.com/users/sign_in` |
| **認証方式** | メールアドレス + パスワード |
| **ログイン先** | dev.keihi.com/transactions（経費一覧） |
| **サブドメイン** | 不要 |
| **制限** | サブドメイン必須アカウントはエラーで拒否される（後述） |

### ④ Googleでログイン

| 項目 | 内容 |
|------|------|
| **入口** | TOKIUM IDログイン画面（dev.keihi.com/users/sign_in）の「Googleでログイン」ボタン |
| **認証方式** | Google OAuth2 |
| **form** | POST `dev.keihi.com/omniauth/google_oauth2` |
| **サブドメインログイン画面** | **利用不可**（ボタンなし） |

### ⑤ Microsoft 365でログイン

| 項目 | 内容 |
|------|------|
| **入口** | TOKIUM IDログイン画面（dev.keihi.com/users/sign_in）の「Microsoft 365でログイン」ボタン |
| **認証方式** | Microsoft Office365 OAuth |
| **form** | POST `dev.keihi.com/omniauth/microsoft_office365` |
| **サブドメインログイン画面** | **利用不可**（ボタンなし） |

---

## 3. サブドメインログインの仕組み

### サブドメインとは

テナント（事業所）ごとに割り当てられた識別子。サブドメインを使うと、テナント専用のログイン画面にアクセスできる。

| サブドメイン | テナント名 | URL |
|------------|----------|-----|
| th-01 | マルチテナント検証用1 | th-01.dev.keihi.com |
| th-02 | マルチテナント検証用2 | th-02.dev.keihi.com |

### サブドメインログインのフロー

```
dev.keihi.com/users/sign_in
  → [サブドメインを入力]
  → dev.keihi.com/subdomains/input     ← サブドメイン入力
  → [th-01を入力して送信]
  → th-01.dev.keihi.com/subdomains/sign_in  ← テナント専用ログイン
  → [メール+PW入力 → ログイン]
  → th-01.dev.keihi.com/transactions   ← テナントの経費一覧
```

### サブドメインログイン画面の特徴

TOKIUM IDログイン画面（dev.keihi.com/users/sign_in）と比較して:

| 項目 | TOKIUM IDログイン | サブドメインログイン |
|------|------------------|-------------------|
| メール+PW | ○ | ○ |
| Googleでログイン | ○ | **×** |
| Microsoft 365でログイン | ○ | **×** |
| SAML/SSOボタン | ○（環境による） | **×** |
| サブドメインを入力 | ○ | × |
| サブドメイン入力に戻る | × | ○ |

> サブドメインログイン画面では**メール+PW認証のみ**利用可能。

---

## 4. サブドメイン必須制限（TH-898）

### 概要

事業所に `sso_only_login_enabled_from` を設定すると、そのテナントのユーザーは**サブドメイン経由以外のTOKIUM IDログインが拒否**される。

### エラーメッセージ（実機確認済み）

| 画面 | 条件 | メッセージ |
|------|------|----------|
| dev.keihi.com/users/sign_in | サブドメイン必須アカウントで直接ログイン | ⚠「許可されていないログイン方法です。サブドメインを入力してからログインしてください。」 |
| [sd].dev.keihi.com/subdomains/sign_in | `sso_only_login_enabled_from`設定済み + ID/PWログイン試行 | ⚠「この事業所ではTOKIUM IDでのログインのみ許可されています。TOKIUM IDでログインしてください。」（※未実機確認。フラグ設定待ち） |

### 制限の影響範囲

| 操作 | 制限あり | 制限なし |
|------|---------|---------|
| TOKIUM ID直接ログイン（③） | **拒否** | 許可 |
| サブドメイン経由ログイン | 許可 | 許可 |
| invoicing直接ログイン（①） | 未確認 | 許可 |
| TOKIUM IDログイン invoicing経由（②） | **拒否**（dev.keihi.comで拒否） | 許可 |
| Googleログイン（④） | 未確認 | 許可 |
| Microsoft 365ログイン（⑤） | 未確認 | 許可 |
| TOKIUM管理ユーザー（th+*@tokium.jp） | **制限対象外**（常に許可） | 許可 |
| ログイン済みセッション | 影響なし | 影響なし |
| テナント切り替え | 影響なし | 影響なし |

---

## 5. 画面一覧と遷移関係

### 画面一覧

| # | 画面名 | URL | 到達方法 |
|---|--------|-----|---------|
| A | invoicingログイン | `invoicing-staging.keihi.com/login` | 直接アクセス |
| B | TOKIUM IDログイン | `dev.keihi.com/users/sign_in` | Aの「TOKIUM IDでログイン」or 直接アクセス |
| C | サブドメイン入力 | `dev.keihi.com/subdomains/input` | Bの「サブドメインを入力」 |
| D | サブドメインログイン | `[sd].dev.keihi.com/subdomains/sign_in` | Cで有効サブドメイン送信 |
| E | パスワード再発行 | `dev.keihi.com/users/password/new` | B or Dの「パスワードを忘れた方はこちら」 |
| F | invoicing請求書一覧 | `invoicing-staging.keihi.com/invoices` | Aのログイン成功 or B経由SSO成功 |
| G | 経費一覧 | `[sd].dev.keihi.com/transactions` | B or Dのログイン成功 |

### 画面遷移マトリクス

| 遷移元 → 遷移先 | A | B | C | D | E | F | G |
|----------------|---|---|---|---|---|---|---|
| **A** invoicingログイン | - | TOKIUM IDでログイン | - | - | - | ログイン成功 | - |
| **B** TOKIUM IDログイン | - | - | サブドメインを入力 | - | PW忘れ | SSO成功(②) | ログイン成功(③) |
| **C** サブドメイン入力 | - | ログイン画面に戻る | - | 有効SD送信 | - | - | - |
| **D** サブドメインログイン | - | - | SD入力に戻る | - | PW忘れ | - | ログイン成功 |
| **E** パスワード再発行 | - | ログイン画面に戻る | - | - | - | - | - |

---

## 6. テナント別の機能差分

サブドメインでログインした場合、テナントの契約内容に応じてサイドバーが変わる。

| メニュー | th-01 | th-02 |
|---------|-------|-------|
| TOKIUM経費精算（経費, カード明細, 集計） | ○ | ○ |
| TOKIUMインボイス（自動入力中書類, 請求書, 国税関係書類, 取引先, 集計） | × | ○ |
| TOKIUM請求書発行（外部リンク） | ○ | ○ |

---

## 7. 未確認事項

| # | 項目 | ブロッカー |
|---|------|----------|
| 1 | サブドメインログイン画面での `sso_only_login_enabled_from` エラーメッセージの実表示 | Railsコンソールでのフラグ設定待ち |
| 2 | invoicing直接ログイン（①）への制限影響 | フラグ設定後に確認 |
| 3 | Google/MS365ログインへの制限影響 | フラグ設定後に確認 |
| 4 | dev-ti環境のサブドメイン（ti-saml等）との差異 | 環境差の確認 |
