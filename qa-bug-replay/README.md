# QA Bug Replay

バグ発見時に直近30秒の動画 + Consoleログ + Networkリクエストを自動保存するChrome拡張機能。

## 構成

```
qa-bug-replay/
  qa-bug-replay-v12.html      # スタンドアロン版（単体HTMLで動作）
  qa-bug-replay-extension/     # Chrome拡張版
    manifest.json
    background/                # Service Worker
    content/                   # Content Script
    offscreen/                 # Offscreen Document（録画処理）
    sidepanel/                 # サイドパネルUI
    report/                    # レポート生成
    icons/                     # 拡張アイコン
```

## 機能

- **30秒リプレイバッファ**: 常時録画し、直近30秒を保持
- **ショートカットキー**: `Ctrl+B`（Mac: `Cmd+B`）でバグ発見時に即保存
- **自動キャプチャ**: 動画 + Consoleログ + Networkリクエストをまとめて保存
- **レポート生成**: 保存データからバグレポートを自動生成

## Chrome拡張のインストール

1. `chrome://extensions/` を開く
2. 「デベロッパーモード」を有効化
3. 「パッケージ化されていない拡張機能を読み込む」で `qa-bug-replay-extension/` フォルダを選択

## スタンドアロン版

`qa-bug-replay-v12.html` をブラウザで直接開いて使用できます。
