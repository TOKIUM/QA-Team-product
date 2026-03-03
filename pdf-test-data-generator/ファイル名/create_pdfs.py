"""
各種文字種をファイル名に設定したPDFを作成するスクリプト
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ファイル名と説明の定義
FILE_DEFINITIONS = [
    ("ひらがな.pdf", "ひらがな"),
    ("ﾊﾝｶｸｶﾀｶﾅ.pdf", "半角カタカナ"),
    ("全角カタカナ.pdf", "全角カタカナ"),
    ("漢字.pdf", "漢字"),
    ("1234567890.pdf", "半角数字"),
    ("１２３４５６７８９０.pdf", "全角数字"),
    ("ＡＢＣＤＥＦＧ.pdf", "全角英語"),
    ("abcdefg.pdf", "半角英語"),
    ("!@#$%&()=~.pdf", "記号"),
    ("%5Ct%5Cn%5Cr%5C0.pdf", "エスケープ文字"),
]


def create_pdf(filepath: str, description: str) -> bool:
    """指定パスにPDFを作成する。成功時True、失敗時Falseを返す。"""
    try:
        c = canvas.Canvas(filepath, pagesize=A4)
        c.setFont("Helvetica", 24)
        c.drawString(72, 750, f"Category: {description}")
        c.setFont("Helvetica", 16)
        c.drawString(72, 700, f"Filename: {os.path.basename(filepath)}")
        c.save()
        return True
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


def main():
    success_count = 0
    fail_count = 0

    for filename, description in FILE_DEFINITIONS:
        filepath = os.path.join(OUTPUT_DIR, filename)
        print(f"Creating: {filename} ({description})")

        if create_pdf(filepath, description):
            if os.path.exists(filepath):
                size = os.path.getsize(filepath)
                print(f"  -> OK ({size} bytes)")
                success_count += 1
            else:
                print(f"  -> FAIL: file not found after creation")
                fail_count += 1
        else:
            fail_count += 1

    print(f"\nDone: {success_count} succeeded, {fail_count} failed")


if __name__ == "__main__":
    main()
