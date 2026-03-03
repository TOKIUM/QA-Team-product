# ログイン画面 テスト設計書

**対象機能**: TOKIUM 請求書発行 ログイン機能
**対象URL**: https://invoicing-staging.keihi.com/login
**作成日**: 2026-02-18
**最終更新**: 2026-03-02
**テスト項目数**: 12件（自動12件）

---

## 1. 機能仕様サマリー

### 1-1. 画面フロー

```
ログインページ (/login)
  ├── メールアドレス入力
  ├── パスワード入力
  ├── 「ログイン」ボタン → 認証成功 → /invoices（請求書一覧）に遷移
  ├── 「パスワードを忘れた場合」リンク → /recovery に遷移
  ├── 「新規登録はこちら」リンク → /registration に遷移
  └── 「TOKIUM ID でログイン」ボタン → /auth-redirect に遷移
        └── dev.keihi.com/users/sign_in（TOKIUM IDログイン画面）
              ├── メール・パスワード入力 → ログイン
              │     └── SSO: auth/callback → invoicing-staging /invoices に直接リダイレクト
              ├── Googleでログイン
              ├── Microsoft 365でログイン
              └── サブドメインを入力
```

> **注意（2026-03-02 実機確認）**: TOKIUM IDログイン後、dev.keihi.com/transactions に留まるのではなく、
> SSOコールバック（invoicing-staging.keihi.com/auth/callback?token=...）経由で invoicing に直接リダイレクトされる。
> サイドバー「TOKIUM請求書発行」リンクから手動遷移する必要はない。

### 1-2. 画面構成要素

| 要素 | 種別 | 詳細 |
|------|------|------|
| TOKIUM ロゴ | img | alt="TOKIUM 請求書発行" |
| メールアドレス | input (email) | label="メールアドレス", type="email" |
| パスワード | input (password) | label="パスワード", type="password" |
| ログインボタン | button | name="ログイン" (exact=True で特定) |
| パスワードを忘れた場合 | link | → /recovery |
| 新規登録はこちら | link | → /registration |
| TOKIUM ID でログイン | button/link | href="/auth-redirect" |

### 1-3. 認証仕様

| 項目 | 仕様 |
|------|------|
| 認証方式 | メールアドレス + パスワード |
| 成功時遷移先 | /invoices（請求書一覧） |
| 外部認証 | TOKIUM ID ログイン（/auth-redirect → dev.keihi.com SSO → invoicing コールバック） |
| パスワードリカバリー | /recovery 画面 |
| 新規登録 | /registration 画面 |

---

## 2. テストカテゴリ一覧

| カテゴリ | 内容 | 件数 | 実行方法 |
|---------|------|------|---------|
| A. ページ表示 | ログインページ / TOKIUM IDログイン画面の要素表示確認 | 2 | 自動 |
| B. 画面遷移 | 各リンク・ボタンからの遷移確認 | 3 | 自動 |
| C. 認証 | 正常ログイン / TOKIUM IDログイン / invoicing遷移 | 3 | 自動 |
| D. 異常系 | 空欄ログイン / 不正パスワード（invoicing + TOKIUM ID） | 4 | 自動 |
| **合計** | | **12** | |

---

## 3. テストケース詳細

### カテゴリA: ページ表示（2件）

| TC-ID | テスト名 | 入力 | 期待結果 | 自動化 |
|-------|---------|------|---------|--------|
| TH-L01 | ログインページの表示確認 | /login にアクセス | ロゴ、メールアドレス欄(type=email)、パスワード欄(type=password)、ログインボタン、パスワードリセットリンク、新規登録リンク、TOKIUM IDボタンが全て表示 | test_ログインページの表示確認 |
| TH-L06 | TOKIUM IDログイン画面の表示確認 | /loginから「TOKIUM IDでログイン」→dev.keihi.com遷移 | メール欄、パスワード欄、ログインボタン、パスワードリセットリンク、Googleボタン、Microsoft 365ボタン、サブドメインボタン全て表示 | test_tokium_idログイン画面の表示確認 |

### カテゴリB: 画面遷移（3件）

| TC-ID | テスト名 | 入力 | 期待結果 | 自動化 |
|-------|---------|------|---------|--------|
| TH-L02 | パスワードリセット画面への遷移 | 「パスワードを忘れた場合」クリック | URL が /recovery に遷移 | test_パスワードリセット画面への遷移 |
| TH-L03 | 新規登録画面への遷移 | 「新規登録はこちら」クリック | URL が /registration に遷移 | test_新規登録画面への遷移 |
| TH-L04 | TOKIUM ID ログイン画面への遷移 | 「TOKIUM ID でログイン」クリック | URL が /login 以外に遷移 | test_tokium_idログイン画面への遷移 |

### カテゴリC: 認証（3件）

| TC-ID | テスト名 | 入力 | 期待結果 | 自動化 |
|-------|---------|------|---------|--------|
| TH-L05 | 正常ログイン | 正しいメール+パスワード入力→ログインボタン | URL が /login 以外に遷移（認証成功） | test_正常ログイン |
| TH-L07 | TOKIUM IDログイン成功 | dev.keihi.comで正しい認証情報入力→ログイン | SSO経由でinvoicing-staging.keihi.comに遷移、ユーザー名「智片拓海」表示、サイドバーナビ表示 | test_tokium_idログイン成功 |
| TH-L08 | TOKIUM ID invoicing遷移 | TOKIUM IDログイン後の状態 | invoicing内で/partnersに遷移できる（認証セッション有効） | test_tokium_id_invoicing遷移 |

### カテゴリD: 異常系（4件）

| TC-ID | テスト名 | 入力 | 期待結果 | 自動化 |
|-------|---------|------|---------|--------|
| TH-L09 | 空欄でのログイン試行 | /loginで何も入力せず→ログインボタン | URL が /login のまま | test_空欄でのログイン試行 |
| TH-L10 | 不正なパスワードでのログイン | 正しいメール+不正パスワード→ログインボタン | URL が /login のまま | test_不正なパスワードでのログイン |
| TH-L11 | TOKIUM ID空欄でのログイン試行 | dev.keihi.comで何も入力せず→ログインボタン | dev.keihi.comに留まり「ログインに失敗しました」表示 | test_tokium_id空欄でのログイン試行 |
| TH-L12 | TOKIUM ID不正パスワードでのログイン | dev.keihi.comで正しいメール+不正パスワード→ログイン | dev.keihi.comに留まり「ログインに失敗しました」表示 | test_tokium_id不正なパスワードでのログイン |

---

## 4. テスト関数とTC-IDの対応

| TC-ID | テスト関数名 | ファイル |
|-------|------------|---------|
| TH-L01 | test_ログインページの表示確認 | test_tokium_login.py |
| TH-L02 | test_パスワードリセット画面への遷移 | test_tokium_login.py |
| TH-L03 | test_新規登録画面への遷移 | test_tokium_login.py |
| TH-L04 | test_tokium_idログイン画面への遷移 | test_tokium_login.py |
| TH-L05 | test_正常ログイン | test_tokium_login.py |
| TH-L06 | test_tokium_idログイン画面の表示確認 | test_tokium_login.py |
| TH-L07 | test_tokium_idログイン成功 | test_tokium_login.py |
| TH-L08 | test_tokium_id_invoicing遷移 | test_tokium_login.py |
| TH-L09 | test_空欄でのログイン試行 | test_tokium_login.py |
| TH-L10 | test_不正なパスワードでのログイン | test_tokium_login.py |
| TH-L11 | test_tokium_id空欄でのログイン試行 | test_tokium_login.py |
| TH-L12 | test_tokium_id不正なパスワードでのログイン | test_tokium_login.py |
