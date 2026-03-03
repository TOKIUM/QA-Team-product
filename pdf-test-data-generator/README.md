# PDF テストデータ生成ツール

ファイルアップロード機能のテストに使用するテストデータ（PDF・各種ファイル）を生成するツール。

## 概要

4カテゴリのテストデータを生成できる。

| カテゴリ | 内容 | スクリプト |
|---|---|---|
| ファイルサイズ | 境界値テスト用PDF（5MB/10MB境界、ファイル数上限） | `ファイルサイズ/create_size_pdfs.py` |
| ファイル名 | 各種文字種のファイル名（ひらがな・漢字・記号・NTFS上限255字等） | `ファイル名/create_pdfs.py`, `create_longest_pdf.py` |
| ファイル数 | ファイル数制限テスト用（手動配置） | - |
| 拡張子 | 14種類のファイル形式（jpg, png, pdf, xlsx, docx, pptx等） | `拡張子/create_various_files.py` |

## セットアップ

```bash
pip install reportlab Pillow openpyxl python-docx python-pptx
```

## 使い方

### ファイルサイズテスト用PDF生成

```bash
cd ファイルサイズ
python create_size_pdfs.py
```

生成される8パターン:
- `01_single_10MB_under` — 1ファイル 9.9MB（10MB以下）
- `02_single_10MB_over` — 1ファイル 10.1MB（10MB超）
- `03_10files_upload` — 10ファイル（各100KB）
- `04_11files_upload` — 11ファイル（各100KB）
- `05_total_10MB_under` — 5ファイル合計9.5MB（合計10MB以下）
- `06_total_10MB_over` — 5ファイル合計10.5MB（合計10MB超）
- `07_single_5MB` — 1ファイル 5.0MB
- `08_single_5MB_over_10MB_under` — 1ファイル 5.1MB

### ファイル名テスト用PDF生成

```bash
cd ファイル名
python create_pdfs.py          # 10種類の文字種PDF
python create_longest_pdf.py   # NTFS上限255文字のファイル名PDF（要管理者権限）
```

### 拡張子テスト用ファイル生成

```bash
cd 拡張子
python create_various_files.py
```

生成: jpg, jpeg, png, pdf, xlsx, xls, csv, txt, doc, docx, gif, pptx, 名前なしファイル

## 注意事項

- `create_longest_pdf.py` は Windows の `subst` コマンドを使うため、管理者権限が必要
- 生成済みの大容量PDF（ファイルサイズフォルダ内）は `.gitignore` で除外済み。ローカルで `create_size_pdfs.py` を実行して生成すること
- NTFS上限255文字のファイル名PDFもgitで扱えないため除外。`create_longest_pdf.py` で生成すること
