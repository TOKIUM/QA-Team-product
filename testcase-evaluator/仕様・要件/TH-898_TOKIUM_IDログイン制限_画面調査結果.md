# TH-898 TOKIUM IDログイン制限 — 画面調査結果

**調査日**: 2026-03-02（E2Eテスト知見追記: 2026-03-02）
**対象環境**: dev-ti（`ti-saml.dev-ti.keihi.com`）
**対象機能**: 「TOKIUM IDでのログインのみ許可する」設定（TH-898）

---

## 1. 調査目的

サブドメインを使用したログイン画面で「TOKIUM IDでログインしてください」等のメッセージが表示される条件を特定する。

## 2. 調査結果サマリー

**結論: 現環境では該当メッセージは表示されない。表示にはサーバー側でのフラグ設定が必要。**

### エラーメッセージの仕様（TH-898より）

- **メッセージ全文**: 「この事業所ではTOKIUM IDでのログインのみ許可されています。TOKIUM IDでログインしてください。」
- **表示条件**: 事業所の `sso_only_login_enabled_from` が本日以前の日付に設定されている状態で、ID/PWログインを試行した場合
- **表示方式**: Railsフラッシュメッセージ（サーバーサイドレンダリング）
- **表示場所**: ログイン画面上部のフラッシュメッセージ領域

### フラッシュメッセージのHTML構造（実機確認済み）

```html
<div class="row">
  <div class="col-sm-12">
    <div class="card card-info">        <!-- 成功時: card-info / エラー時: card-alert等 -->
      <div class="card-content txt">
        <span class="fa fa-fw fa-exclamation-circle"></span>
        <span>メッセージ本文</span>
      </div>
    </div>
  </div>
</div>
```

## 3. 画面別調査結果

### 3-1. サブドメイン入力画面

| 項目 | 内容 |
|------|------|
| URL | `https://dev-ti.keihi.com/subdomains/input` |
| 画面構成 | TOKIUMロゴ、サブドメイン入力欄、送信ボタン、「ログイン画面に戻る」リンク |
| 該当メッセージ | **なし** |

### 3-2. サブドメインログイン画面（ti-saml）

| 項目 | 内容 |
|------|------|
| URL | `https://ti-saml.dev-ti.keihi.com/subdomains/sign_in` |
| 画面構成 | TOKIUMロゴ、「ログインはこちらから」見出し、ID/PW入力欄、ログインボタン、「パスワードを忘れた方はこちら」リンク、Googleログイン、MS365ログイン、SAMLボタン（「テスト作成2」）、「サブドメイン入力に戻る」リンク、TOKIUMシリーズリンク |
| 該当メッセージ | **なし** |
| 備考 | 「TOKIUM IDでログイン」ボタンは存在しない（請求書発行システムとは異なるUI） |

### 3-3. サブドメインなしのログイン画面

| 項目 | 内容 |
|------|------|
| URL | `https://dev-ti.keihi.com/users/sign_in` |
| 画面構成 | 3-2とほぼ同じ。SAMLボタンの代わりに「サブドメインを入力」ボタンがある |
| 該当メッセージ | **なし** |

### 3-4. ログイン成功後の画面

| 項目 | 内容 |
|------|------|
| URL | `https://ti-saml.dev-ti.keihi.com/members`（従業員一覧） |
| 認証情報 | tokiumdevti@gmail.com / 12345678 |
| フラッシュメッセージ | 「ログインしました。」（card-info） |
| 該当メッセージ | **なし** |

### 3-5. SAMLボタン（「テスト作成2」）押下後

| 項目 | 内容 |
|------|------|
| リダイレクト先 | `https://login.microsoftonline.com/481efdb8-...` |
| 画面タイトル | 「アカウントにサインイン」（Microsoft Entra ID） |
| 表示内容 | エラー: AADSTS700016 — アプリケーション `urn:amazon:cognito:sp:ap-northeast-1_nnM9ZACC3` が見つからない |
| 該当メッセージ | **なし**（Microsoft側のエラーのみ） |

## 4. フロントエンド調査

| 調査項目 | 結果 |
|----------|------|
| DOM内の隠し要素（hidden/CSS非表示）| 「TOKIUM ID」「許可されています」「sso_only」を含む要素なし |
| インラインScript内 | 該当テキストなし |
| 外部JSバンドル（6ファイル）| インラインには該当なし。外部JSはminified |
| ネットワークリクエスト | ログインはフォームPOST→サーバーサイドリダイレクト方式 |

**判定: エラーメッセージはサーバーサイド（Rails）でのみ生成され、クライアント側には事前に埋め込まれていない**

## 5. メッセージ表示に必要な条件

### 必須条件（TH-898仕様書より）

1. **事業所に `sso_only_login_enabled_from` を設定する**（Railsコンソールで実行）
   ```ruby
   rg = User.find_by(email: "tokiumdevti@gmail.com").root_group
   rg.update!(sso_only_login_enabled_from: Date.current)
   ```
2. **ID/PWでログインを試行する**（TOKIUM IDではなく）
3. **TOKIUM管理ユーザー（th+*@tokium.jp）ではないこと**

### 制限対象外（メッセージが出ない操作）

- TOKIUM IDでのログイン
- ログイン済みユーザーの操作（セッション継続）
- テナント（事業所）切り替え
- TOKIUM管理ユーザーのID/PWログイン

## 6. TOKIUM IDログインのSSOフロー（実機確認済み 2026-03-02）

E2Eテスト実装時に判明した、invoicingからのTOKIUM IDログインの実際のフロー:

```
invoicing-staging.keihi.com/login
  │ 「TOKIUM IDでログイン」ボタン（href="/auth-redirect"）クリック
  ▼
invoicing-staging.keihi.com/auth-redirect
  │ 自動リダイレクト
  ▼
dev.keihi.com/users/sign_in                ← TOKIUM IDログイン画面
  │ メール・パスワード入力 → ログインボタンクリック
  ▼
invoicing-staging.keihi.com/auth/callback?token=eyJ...  ← SSOコールバック
  │ トークン処理・セッション作成
  ▼
invoicing-staging.keihi.com/invoices       ← 最終着地点（請求書一覧）
```

> **重要**: 当初の想定では「dev.keihi.com/transactions に留まり、サイドバーから手動でinvoicingに遷移する」と考えていたが、
> 実際にはSSOコールバックにより**invoicingに直接リダイレクト**される。dev.keihi.com/transactions を経由しない。

### dev.keihi.com/users/sign_in の画面要素（実機確認済み）

| 要素 | 種別 | セレクタ/ロケーター |
|------|------|-------------------|
| メールアドレス | input (email) | `input[name="user[email]"]` placeholder="ログインID (メールアドレス)" |
| パスワード | input (password) | `input[name="user[password]"]` |
| ログインボタン | **button (type="button")** | `#sign_in_form button[type="button"]` ※JS制御 |
| パスワードリセット | link | テキスト: 「パスワードを忘れた方はこちら」 href="/users/password/new" |
| Googleでログイン | **button (type="submit")** | ※linkではない |
| Microsoft 365でログイン | **button (type="submit")** | ※linkではない |
| サブドメインを入力 | **button (type="submit")** | ※linkではない |

### dev.keihi.com のログイン失敗メッセージ（実機確認済み）

| 失敗パターン | エラーメッセージ | 表示方式 |
|-------------|----------------|---------|
| 空欄で送信 | 「ログインに失敗しました。あと○回失敗すると、アカウントがロックされます。パスワード再設定を行なってください。」 | ページ本文テキスト（CSSクラスなし、`.alert`等の要素ではない） |
| 不正パスワード | 同上 | 同上 |

> **注意**: dev-ti環境（3-2〜3-5）のフラッシュメッセージは `div.card.card-info` だが、
> dev環境（dev.keihi.com）のログイン失敗メッセージはCSSクラスなしのプレーンテキストとして表示される。
> `sso_only_login_enabled_from` 設定時のエラーメッセージが同じ方式かは未確認。

## 7. 2つのシステムのログイン画面比較

| 項目 | TOKIUM 請求書発行 | TOKIUM 経費精算/インボイス |
|------|-------------------|---------------------------|
| URL | `invoicing-staging.keihi.com/login` | `ti-saml.dev-ti.keihi.com/subdomains/sign_in` |
| 認証方式 | メール+PW / TOKIUM ID | メール+PW / Google / MS365 / SAML |
| 「TOKIUM IDでログイン」ボタン | **あり** | **なし** |
| TOKIUM IDログイン先 | dev.keihi.com/users/sign_in（SSO→invoicingに自動戻り） | — |
| サブドメイン | なし | あり |
| パスワードリセット | `/recovery` | `/users/password/new` |
| 新規登録 | `/registration` | なし |
| ログイン失敗メッセージ | /loginに留まる（メッセージ未特定） | 「ログインに失敗しました。あと○回失敗すると...」 |
| フラッシュメッセージ構造 | 未確認 | `div.card.card-info > div.card-content > span` |
| TOKIUM IDログイン失敗 | dev.keihi.comでエラー表示（プレーンテキスト） | — |

## 8. E2Eテスト自動化の状況（2026-03-02時点）

invoicing-staging のログイン機能に対するE2Eテスト（Playwright）が12件整備済み:

| TC-ID | テスト名 | カテゴリ | 結果 |
|-------|---------|---------|------|
| TH-L01〜L04 | ページ表示・画面遷移 | 正常系 | ALL PASS |
| TH-L05 | invoicing正常ログイン | 正常系 | PASS |
| TH-L06 | TOKIUM IDログイン画面の表示確認 | 正常系 | PASS |
| TH-L07 | TOKIUM IDログイン成功（SSO→invoicing） | 正常系 | PASS |
| TH-L08 | TOKIUM IDログイン後のinvoicing内遷移 | 正常系 | PASS |
| TH-L09〜L10 | invoicing空欄・不正PW | 異常系 | ALL PASS |
| TH-L11〜L12 | TOKIUM ID空欄・不正PW | 異常系 | ALL PASS |

- テストコード: `C:\Users\池田尚人\ClaudeCode用\画面テスト\TH\ログイン\generated_tests\test_tokium_login.py`
- 動画証跡: `C:\Users\池田尚人\ClaudeCode用\画面テスト\TH\ログイン\test_results\TH-L01〜L12\`

### TH-898対応で追加が見込まれるテスト

| 想定TC-ID | テスト名 | 前提条件 |
|-----------|---------|---------|
| TH-L13（仮） | sso_only設定時のID/PWログイン拒否 | `sso_only_login_enabled_from` 設定済み環境 |
| TH-L14（仮） | sso_only設定時のエラーメッセージ確認 | 同上 |
| TH-L15（仮） | sso_only設定時のTOKIUM IDログイン許可 | 同上 |
| TH-L16（仮） | TOKIUM管理ユーザーのID/PWログイン許可 | 同上 + th+*@tokium.jp アカウント |

> これらは `sso_only_login_enabled_from` の設定が完了してから実装する。

## 9. 次のアクション

| 優先度 | アクション | 担当 | 状態 |
|--------|-----------|------|------|
| 高 | dev-ti環境のRailsコンソールで `sso_only_login_enabled_from` を設定し、エラーメッセージの実表示を確認 | 開発チームへ依頼 | 未着手 |
| 中 | エラー表示時のCSSクラス（card-alert等）を特定し、テスト自動化のセレクタに反映 | フラグ設定後に確認 | 未着手 |
| 中 | TH-L13〜L16（sso_only関連テスト）の実装 | フラグ設定後に実装 | 未着手 |
| 低 | SAML SSO設定の修正（AADSTS700016エラーの解消） | 別途対応 | 未着手 |
| 完了 | TOKIUM IDログインのSSOフロー実態調査 | E2Eテストで確認済み | **完了** |
| 完了 | dev.keihi.comの画面要素・エラーメッセージ特定 | E2Eテストで確認済み | **完了** |
