# AI-Powered E2E Test Generator

Claude API + Playwright で **自然言語からE2Eテストを自動生成** するツール。

## セットアップ

```bash
# 1. 依存パッケージインストール
pip install -r requirements.txt

# 2. Playwright ブラウザをインストール
playwright install chromium

# 3. Anthropic API キーを設定
export ANTHROPIC_API_KEY="sk-ant-..."
```

## 使い方

### Step 1: テストシナリオを書く

`scenarios/` に YAML ファイルを作成します。

```yaml
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
```

**ポイント**: `target` は日本語の自然言語で OK。AI がページを解析して最適なロケーターを選択します。

### Step 2: テストコードを生成

```bash
# 単一シナリオから生成
python generate.py scenarios/login.yaml

# 全シナリオを一括生成
python generate.py --all
```

### Step 3: テストを実行（高速！）

```bash
# 全テスト実行
pytest -v

# 特定テストのみ
pytest generated_tests/test_login.py -v

# ブラウザを表示して実行（デバッグ用）
pytest --headed -v

# 失敗時にスクリーンショットを保存
pytest --screenshot on -v
```

## 速度比較

| 手法 | ログインテスト1件 | 100テスト |
|------|-----------------|----------|
| Claude in Chrome（直接実行） | 〜30秒 | 〜50分 |
| **本ツール（生成済みテスト実行）** | **〜2秒** | **〜3分** |

## プロジェクト構成

```
e2e-test-generator/
├── scenarios/              ← テストシナリオ（YAML）
├── generator/              ← AI テスト生成エンジン
│   ├── page_analyzer.py    ← ページ構造解析
│   ├── code_generator.py   ← Claude API でコード生成
│   └── self_healer.py      ← 自動修復
├── generated_tests/        ← 生成されたテスト（自動生成）
├── generate.py             ← CLI エントリーポイント
├── conftest.py             ← pytest 共通設定
├── config.py               ← 設定
└── ARCHITECTURE.md         ← 詳細設計書
```
