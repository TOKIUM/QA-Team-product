"""
ファイルサイズ・ファイル数の条件別テストPDF作成スクリプト

作成するフォルダ構成:
  01_single_10MB_under/              ... 1ファイル 10MB以下  (9.9MB)
  02_single_10MB_over/               ... 1ファイル 10MB超     (10.1MB)
  03_10files_upload/                 ... 10ファイル (各100KB)
  04_11files_upload/                 ... 11ファイル (各100KB)
  05_total_10MB_under/               ... 複数ファイル合計 10MB以下 (5ファイル×1.9MB=9.5MB)
  06_total_10MB_over/                ... 複数ファイル合計 10MB超   (5ファイル×2.1MB=10.5MB)
  07_single_5MB/                     ... 1ファイル 5MB (5.0MB)
  08_single_5MB_over_10MB_under/     ... 1ファイル 5MB以上10MB未満 (5.1MB)

すべて reportlab で正規のPDFとして生成する。
サイズ調整はPDFコメント行（%始まり、PDF仕様上無視される）によるパディングで行う。
"""

import os
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

OUTPUT_ROOT = os.path.dirname(os.path.abspath(__file__))

MB = 1024 * 1024
PAGE_WIDTH, PAGE_HEIGHT = A4


def make_dir(path: str):
    os.makedirs(path, exist_ok=True)


def _create_base_pdf(label: str, filename: str, target_bytes: int) -> bytes:
    """ラベル情報付きの小さなベースPDFをメモリ上に生成して返す。"""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica", 16)
    c.drawString(72, 750, "Size Test PDF")
    c.setFont("Helvetica", 12)
    c.drawString(72, 720, f"Label: {label}")
    c.drawString(72, 700, f"Target: {target_bytes:,} bytes ({target_bytes / MB:.2f} MB)")
    c.drawString(72, 680, f"File: {filename}")
    c.showPage()
    c.save()
    return buf.getvalue()


def create_pdf_with_target_size(filepath: str, target_bytes: int, label: str):
    """
    目標サイズぴったりの正規PDFを生成する。
    ベースPDFにPDFコメント行（%始まり）でパディングして目標サイズに到達させる。
    PDF仕様上、%%EOF 以降のデータや % で始まるコメント行は無視される。
    """
    filename = os.path.basename(filepath)
    base_data = _create_base_pdf(label, filename, target_bytes)
    base_size = len(base_data)

    if base_size >= target_bytes:
        # ベースだけで目標以上ならそのまま書き出し
        with open(filepath, "wb") as f:
            f.write(base_data)
        return

    # パディング量を計算
    padding_needed = target_bytes - base_size

    # PDFコメント行で埋める（1行最大4096バイト、%Pxxx...xxx\n の形式）
    with open(filepath, "wb") as f:
        f.write(base_data)

        remaining = padding_needed
        chunk_line_size = 4096
        while remaining > 0:
            if remaining <= 2:
                # 最小: %\n (2バイト)
                f.write(b"%\n" if remaining == 2 else b"%")
                remaining = 0
            elif remaining <= chunk_line_size:
                # 最後のチャンク: % + (remaining-2)個のP + \n
                f.write(b"%" + b"P" * (remaining - 2) + b"\n")
                remaining = 0
            else:
                # フルチャンク
                f.write(b"%" + b"P" * (chunk_line_size - 2) + b"\n")
                remaining -= chunk_line_size


def fmt_size(size_bytes: int) -> str:
    if size_bytes >= MB:
        return f"{size_bytes:,} bytes ({size_bytes / MB:.2f} MB)"
    elif size_bytes >= 1024:
        return f"{size_bytes:,} bytes ({size_bytes / 1024:.1f} KB)"
    else:
        return f"{size_bytes:,} bytes"


def report(dirpath: str):
    files = sorted(f for f in os.listdir(dirpath) if os.path.isfile(os.path.join(dirpath, f)))
    total = sum(os.path.getsize(os.path.join(dirpath, f)) for f in files)
    is_10mb_under = total <= 10 * MB
    print(f"  Files: {len(files)}, Total: {fmt_size(total)}, <=10MB: {is_10mb_under}")
    for f in files:
        sz = os.path.getsize(os.path.join(dirpath, f))
        print(f"    {f}: {fmt_size(sz)}")
    print()


# ─────────────────────────────────────────────
# 条件1: 1ファイル 10MB以下 (9.9MB)
# ─────────────────────────────────────────────
def create_01():
    desc = "1ファイル 10MB以下"
    dirpath = os.path.join(OUTPUT_ROOT, "01_single_10MB_under")
    make_dir(dirpath)
    print(f"[01] {desc}")

    target = int(9.9 * MB)  # 10,380,902 bytes
    create_pdf_with_target_size(
        os.path.join(dirpath, "file_9.9MB.pdf"), target, desc
    )
    report(dirpath)


# ─────────────────────────────────────────────
# 条件2: 1ファイル 10MB超 (10.1MB)
# ─────────────────────────────────────────────
def create_02():
    desc = "1ファイル 10MB超"
    dirpath = os.path.join(OUTPUT_ROOT, "02_single_10MB_over")
    make_dir(dirpath)
    print(f"[02] {desc}")

    target = int(10.1 * MB)  # 10,590,617 bytes
    create_pdf_with_target_size(
        os.path.join(dirpath, "file_10.1MB.pdf"), target, desc
    )
    report(dirpath)


# ─────────────────────────────────────────────
# 条件3: 10ファイル (各100KB)
# ─────────────────────────────────────────────
def create_03():
    desc = "10ファイルUL"
    dirpath = os.path.join(OUTPUT_ROOT, "03_10files_upload")
    make_dir(dirpath)
    print(f"[03] {desc}")

    for i in range(1, 11):
        create_pdf_with_target_size(
            os.path.join(dirpath, f"file_{i:02d}.pdf"),
            100 * 1024,
            f"{desc} ({i}/10)",
        )
    report(dirpath)


# ─────────────────────────────────────────────
# 条件4: 11ファイル (各100KB)
# ─────────────────────────────────────────────
def create_04():
    desc = "11ファイルUL"
    dirpath = os.path.join(OUTPUT_ROOT, "04_11files_upload")
    make_dir(dirpath)
    print(f"[04] {desc}")

    for i in range(1, 12):
        create_pdf_with_target_size(
            os.path.join(dirpath, f"file_{i:02d}.pdf"),
            100 * 1024,
            f"{desc} ({i}/11)",
        )
    report(dirpath)


# ─────────────────────────────────────────────
# 条件5: 合計10MB以下 (5ファイル × 1.9MB = 9.5MB)
# ─────────────────────────────────────────────
def create_05():
    desc = "合計10MB以下"
    dirpath = os.path.join(OUTPUT_ROOT, "05_total_10MB_under")
    make_dir(dirpath)
    print(f"[05] {desc}")

    per_file = int(1.9 * MB)  # 1,992,294 bytes
    for i in range(1, 6):
        create_pdf_with_target_size(
            os.path.join(dirpath, f"file_{i:02d}.pdf"),
            per_file,
            f"{desc} ({i}/5, 各1.9MB)",
        )
    report(dirpath)


# ─────────────────────────────────────────────
# 条件6: 合計10MB超 (5ファイル × 2.1MB = 10.5MB)
# ─────────────────────────────────────────────
def create_06():
    desc = "合計10MB超"
    dirpath = os.path.join(OUTPUT_ROOT, "06_total_10MB_over")
    make_dir(dirpath)
    print(f"[06] {desc}")

    per_file = int(2.1 * MB)  # 2,202,009 bytes
    for i in range(1, 6):
        create_pdf_with_target_size(
            os.path.join(dirpath, f"file_{i:02d}.pdf"),
            per_file,
            f"{desc} ({i}/5, 各2.1MB)",
        )
    report(dirpath)


# ─────────────────────────────────────────────
# 条件7: 1ファイル 5MB
# 帳票システムで「5.00MB」と表示されるサイズ (5,211,130 bytes)
# ※ システムは (ファイルサイズ+帳票OH) / 1,048,576 を四捨五入2桁で表示
# ─────────────────────────────────────────────
def create_07():
    desc = "1ファイル 5MB"
    dirpath = os.path.join(OUTPUT_ROOT, "07_single_5MB")
    make_dir(dirpath)
    print(f"[07] {desc}")

    target = 5_211_130  # 帳票システムで5.00MB表示になる値
    create_pdf_with_target_size(
        os.path.join(dirpath, "file_5.0MB.pdf"), target, desc
    )
    report(dirpath)


# ─────────────────────────────────────────────
# 条件8: 1ファイル 5MB以上10MB未満 (5.1MB)
# ─────────────────────────────────────────────
def create_08():
    desc = "1ファイル 5MB以上10MB未満"
    dirpath = os.path.join(OUTPUT_ROOT, "08_single_5MB_over_10MB_under")
    make_dir(dirpath)
    print(f"[08] {desc}")

    target = int(5.1 * MB)  # 5.1MB = 5,347,737 bytes (1MB=1,048,576)
    create_pdf_with_target_size(
        os.path.join(dirpath, "file_5.1MB.pdf"), target, desc
    )
    report(dirpath)


# ─────────────────────────────────────────────
def main():
    print(f"Output: {OUTPUT_ROOT}\n")
    print("=" * 60)

    create_01()
    create_02()
    create_03()
    create_04()
    create_05()
    create_06()
    create_07()
    create_08()

    print("=" * 60)
    print("All done.")


if __name__ == "__main__":
    main()
