# ページ解析レポート: TOKIUM 請求書発行 ログイン画面

**URL**: https://invoicing-staging.keihi.com/login  
**タイトル**: TOKIUM 請求書発行  
**解析日**: 2026-02-13

---

## 検出されたアクセシビリティツリー

```
[banner]
  [heading] "ログイン"
    [link] → /
      [image] "TOKIUM 請求書発行"
    "ログイン"
[main]
  [form]
    [label] "メールアドレス"
    [textbox] "メールアドレス"        type="email"
    [label] "パスワード"
    [textbox] "8文字以上のパスワードを入力" type="password"
    [button] "ログイン"               type="submit"
    [link] "パスワードを忘れた場合"     → /recovery
    [link] → /auth-redirect
      [button] "TOKIUM ID でログイン"  type="button"
    [link] "新規登録はこちら"          → /registration
```

## 検出されたインタラクティブ要素（7個）

| # | 種類 | ロケーター | 推奨Playwright API |
|---|------|-----------|-------------------|
| 1 | テキスト入力 | label="メールアドレス", type="email" | `page.get_by_label("メールアドレス")` |
| 2 | パスワード入力 | label="パスワード", placeholder="8文字以上のパスワードを入力" | `page.get_by_label("パスワード")` |
| 3 | 送信ボタン | role="button", name="ログイン", type="submit" | `page.get_by_role("button", name="ログイン")` |
| 4 | リンク | text="パスワードを忘れた場合", href="/recovery" | `page.get_by_role("link", name="パスワードを忘れた場合")` |
| 5 | ボタン | role="button", name="TOKIUM ID でログイン" | `page.get_by_role("button", name="TOKIUM ID でログイン")` |
| 6 | リンク | text="新規登録はこちら", href="/registration" | `page.get_by_role("link", name="新規登録はこちら")` |
| 7 | ロゴリンク | image alt="TOKIUM 請求書発行", href="/" | `page.get_by_role("link").filter(has=page.get_by_role("img"))` |

## ロケーター品質評価

✅ **非常に良好** — このページは以下の点で E2E テストに適しています：

- **全フォーム要素に `<label>` が設定済み** → `get_by_label()` が使える（最も安定）
- **ボタンに明確な名前あり** → `get_by_role("button", name=...)` が使える
- **リンクにテキストあり** → `get_by_role("link", name=...)` が使える
- **CSS セレクタや XPath に頼る必要なし**

⚠️ **注意点**:
- `data-testid` 属性は検出されず → セマンティックロケーターで十分カバー可能
- TOKIUM ID ログインは `<a>` の中に `<button>` がネストされた構造
