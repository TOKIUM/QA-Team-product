# AI-Powered E2E Test Generator - 全体設計書

## 1. コンセプト

```
┌─────────────────────────────────────────────────────────────┐
│                      開発者のワークフロー                       │
│                                                             │
│  ① 自然言語でテストシナリオを書く（YAML）                       │
│       ↓                                                     │
│  ② AI がページを解析し、Playwright テストコードを生成（遅い/1回） │
│       ↓                                                     │
│  ③ 生成されたテストを Playwright で高速実行（速い/何度でも）      │
│       ↓                                                     │
│  ④ UI が変わったら AI が自動修復（必要な時だけ）                 │
└─────────────────────────────────────────────────────────────┘
```

**ポイント**: AI の呼び出しは「生成時」と「修復時」だけ。
日常のテスト実行は Playwright のネイティブ速度（数百ms/テスト）で動く。

---

## 2. アーキテクチャ

```
e2e-test-generator/
├── scenarios/              # ① テストシナリオ（YAML）
│   └── login.yaml
├── generator/              # ② AI テストコード生成エンジン
│   ├── __init__.py
│   ├── page_analyzer.py    #    ページ解析（HTML → 構造化データ）
│   ├── code_generator.py   #    Claude API でテストコード生成
│   └── self_healer.py      #    テスト失敗時の自動修復
├── generated_tests/        # ③ 生成されたテストコード（自動生成）
│   └── test_login.py
├── config.py               # 設定
├── generate.py             # CLI: テスト生成
├── requirements.txt
└── pytest.ini
```

---

## 3. データフロー詳細

### Phase 1: シナリオ定義（人間が書く）

```yaml
# scenarios/login.yaml
name: ログイン機能テスト
base_url: https://your-app.example.com
tests:
  - name: 正常ログイン
    steps:
      - action: goto
        url: /login
      - action: fill
        target: メールアドレス入力欄
        value: "test@example.com"
      - action: fill
        target: パスワード入力欄
        value: "password123"
      - action: click
        target: ログインボタン
      - action: assert_url
        pattern: "/dashboard"
      - action: assert_visible
        target: ダッシュボードの見出し
```

### Phase 2: AI 解析 & コード生成

1. Playwright でページの **アクセシビリティツリー** を取得
2. Claude API に「シナリオ + ページ構造」を渡す
3. Claude が最適なロケーター（getByRole, getByLabel 等）を選択
4. pytest + playwright のテストコードを出力

### Phase 3: 高速実行

```bash
# 通常のテスト実行（AI不要、高速）
pytest generated_tests/ -v

# 失敗時に自動修復を試みる
python generate.py --heal
```

---

## 4. ロケーター戦略（優先順位）

| 優先度 | ロケーター             | 例                                          | 理由               |
|--------|----------------------|---------------------------------------------|-------------------|
| 1      | getByRole            | `page.get_by_role("button", name="ログイン")` | 意味ベースで最も安定   |
| 2      | getByLabel           | `page.get_by_label("メールアドレス")`          | フォーム要素に最適    |
| 3      | getByPlaceholder     | `page.get_by_placeholder("検索...")`         | ラベルがない場合      |
| 4      | getByText            | `page.get_by_text("送信完了")`               | テキスト要素         |
| 5      | getByTestId          | `page.get_by_test_id("submit-btn")`         | data-testid がある場合 |
| 6      | CSS Selector         | `page.locator(".btn-primary")`              | 最終手段            |

この優先順位を Claude に指示することで、**UI変更に強い**テストコードが生成される。

---

## 5. 自動修復（Self-Healing）の仕組み

```
テスト実行 → 失敗検知 → 失敗箇所の特定
                              ↓
                    現在のページ HTML を取得
                              ↓
                    Claude API に修復を依頼
                    「このロケーターが見つかりません。
                     現在のページ構造から正しいロケーターを提案してください」
                              ↓
                    テストコードを自動更新
                              ↓
                    再実行して成功を確認
```

---

## 6. 技術スタック

| コンポーネント        | 技術                      |
|---------------------|--------------------------|
| テストシナリオ        | YAML                     |
| テスト生成エンジン     | Python + Anthropic SDK    |
| ページ解析           | Playwright (Python)       |
| テスト実行           | pytest + pytest-playwright |
| テストフレームワーク   | Playwright (Python)       |
| CI/CD              | GitHub Actions / 任意     |
