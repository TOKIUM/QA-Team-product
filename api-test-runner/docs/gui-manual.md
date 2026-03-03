# API Test Runner GUI — 使い方ガイド

## 起動方法

### 方法 1: .exe をダブルクリック（推奨）

1. `build_exe.cmd` を実行して .exe をビルド
2. `dist\API Test Runner\` フォルダ内の **API Test Runner.exe** をダブルクリック

> **配布時**: `dist\API Test Runner\` フォルダごと渡してください。
> Python のインストールは不要です。

### 方法 2: コマンドラインから起動

```bash
cd api-tests
python -m api_test_runner gui
```

---

## フォルダ構成（.exe 配布時）

```
API Test Runner/
├── API Test Runner.exe   ← ダブルクリックで起動
├── config.yaml           ← テスト設定
├── .env                  ← 接続情報（BASE_URL, API_KEY）
├── document/             ← API 仕様 CSV ファイル
├── results/              ← テスト結果（自動作成）
│   ├── 20260227112509/
│   │   ├── report.json
│   │   └── get-members.json
│   └── latest.txt
└── _internal/            ← ランタイム（編集不要）
```

---

## 画面説明（4タブ）

### Tab 1: テスト実行

API テストを実行し、結果をリアルタイムで確認します。

| 項目 | 説明 |
|------|------|
| CSV | API 仕様 CSV のあるディレクトリ（デフォルト: `document`） |
| フォルダ変更... | CSV ディレクトリ自体を別の場所に切り替え |
| CSV追加... | ファイル選択ダイアログから CSV を選んで document フォルダにコピー |
| ▶ テスト実行 | テストを開始（実行中はボタン無効化） |

**CSV ファイル一覧**: 現在の CSV ディレクトリ内にあるファイルが表示されます。

**結果一覧**: 各テストの名前・パターン・期待/実際ステータス・応答時間・PASS/FAIL を表示します。
- PASS: 緑色
- FAIL: 赤色

**ログ欄**: テストの進行状況がリアルタイムで表示されます。

**サマリー**: 全体の成績（例: `12 passed, 0 failed / 12 total`）。

> テスト実行はバックグラウンドスレッドで動作するため、実行中も GUI は操作可能です。

### Tab 2: レスポンス

テスト実行で取得した API レスポンス JSON を閲覧します。

1. 上部のドロップダウンで実行回（タイムスタンプ）を選択
2. 左のファイル一覧からファイルをクリック
3. 右側に JSON の整形表示

### Tab 3: 設定

接続先やテストパターンを変更できます。

| 項目 | 説明 |
|------|------|
| Base URL | API のベース URL（例: `https://dev.keihi.com/api/v2`） |
| API Key | Bearer トークン（表示/隠すボタンで切替） |
| Timeout | HTTP タイムアウト秒数 |
| auth | 認証あり(200) + 認証なし(401) テスト |
| pagination | offset/limit パラメータ テスト |
| Offset / Limit | pagination パターンのパラメータ値 |

**保存** ボタンを押すと `config.yaml` と `.env` の両方に書き込まれます。

### Tab 4: 履歴

過去のテスト実行結果を一覧表示・比較します。

- **左ペイン**: `results/` 内のタイムスタンプ一覧（新しい順）
- **右ペイン**: 選択した回の `report.json` を表形式で表示
- **比較**: 2つの実行を選択して「比較...」ボタンをクリック
  - 結果が変化したテスト（PASS→FAIL、FAIL→PASS）を差分表示

---

## .exe のビルド手順

### 前提条件

- Python 3.10 以上
- pip でパッケージインストール済み

### ビルド

```bash
cd api-tests

# 初回のみ: PyInstaller インストール
pip install pyinstaller

# ビルド実行
build_exe.cmd
```

ビルド完了後、`dist\API Test Runner\` フォルダが生成されます。

### 再ビルド

CSV 仕様ファイルの追加やコード変更後は、再度 `build_exe.cmd` を実行してください。

---

## トラブルシューティング

| 症状 | 対処 |
|------|------|
| .exe が起動しない | `_internal` フォルダが同階層にあるか確認 |
| 「BASE_URL が未設定」 | `.env` ファイルに `BASE_URL=...` を記入、または設定タブで入力→保存 |
| 「API_KEY が未設定」 | `.env` ファイルに `API_KEY=...` を記入、または設定タブで入力→保存 |
| 「CSV ディレクトリが見つかりません」 | `document` フォルダが .exe と同階層にあるか確認 |
| テスト結果が保存されない | `results` フォルダの書き込み権限を確認 |
| GUI がフリーズする | 通常は発生しません（別スレッド実行）。API サーバーのタイムアウト値を短くしてみてください |

---

## CLI との併用

GUI と CLI は同じバックエンドを共有しています。CLI も引き続き使えます。

```bash
# CLI でテスト実行
python -m api_test_runner run

# CLI で CSV 解析のみ
python -m api_test_runner parse

# GUI 起動
python -m api_test_runner gui
```
