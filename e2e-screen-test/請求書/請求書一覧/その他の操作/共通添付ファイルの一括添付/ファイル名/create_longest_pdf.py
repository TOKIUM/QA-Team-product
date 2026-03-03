"""
Windows で設定可能な最長のファイル名（NTFS上限255文字）を持つPDFを作成するスクリプト

Windows のファイル名制限:
  - NTFS ファイル名上限 = 255 文字（ファイルシステムの制約）
  - MAX_PATH = 260 文字（NUL終端を含む → 使用可能259文字）
  - フルパス = ディレクトリ + '\\' + ファイル名 <= 259
  - 255文字のファイル名を作るには ディレクトリ長 <= 3 が必要

手法:
  - subst コマンドで仮想ドライブ (Z:) を作成し、ドライブ直下に出力
  - Z:\\ (3文字) + ファイル名255文字 = 258文字 (MAX_PATH以内)
  - 作成後、仮想ドライブを解除
  - 実ファイルはスクリプトと同じフォルダに生成される

  ※ LongPathsEnabled の設定に関わらず、NTFSファイル名上限255文字は不変
"""

import os
import subprocess
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# subst で使用する仮想ドライブ文字
VIRTUAL_DRIVE = "Z:"


def find_free_drive():
    """未使用のドライブ文字を探す (Z→A の順)"""
    for letter in "ZYXWVUTSRQPONMLKJIHGFED":
        drive = f"{letter}:"
        if not os.path.exists(drive + os.sep):
            return drive
    raise RuntimeError("No free drive letter found")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    extension = ".pdf"

    # 仮想ドライブを作成してスクリプトのフォルダをマウント
    drive = find_free_drive()
    print(f"Using virtual drive: {drive}")

    try:
        # subst で仮想ドライブ作成
        subprocess.run(
            ["subst", drive, script_dir],
            check=True, capture_output=True, text=True,
        )
        print(f"Mounted: {drive} -> {script_dir}")

        output_dir = drive + os.sep  # "Z:\" (3文字)

        # MAX_PATH = 260, NUL終端で使用可能259文字
        # フルパス = "Z:\" (3文字) + ファイル名 <= 259
        max_path_usable = 259
        max_filename_from_path = max_path_usable - len(output_dir)  # 3文字
        ntfs_filename_limit = 255

        max_filename_len = min(max_filename_from_path, ntfs_filename_limit)
        # ファイル名 = ベース名 + ".pdf"
        max_base_len = max_filename_len - len(extension)

        print(f"Output directory : {output_dir}")
        print(f"Directory length : {len(output_dir)}")
        print(f"MAX_PATH usable  : {max_path_usable}")
        print(f"Max filename     : {max_filename_len} chars")
        print(f"Extension        : {extension} ({len(extension)} chars)")
        print(f"Max base name    : {max_base_len} chars")

        # ベース名を 'A' の繰り返しで構築
        base_name = "A" * max_base_len
        filename = base_name + extension
        filepath = os.path.join(output_dir, filename)

        print(f"\nFilename length  : {len(filename)} chars")
        print(f"Full path length : {len(filepath)} chars")
        print(f"Filename preview : {filename[:40]}...{filename[-10:]}")

        # PDF作成
        c = canvas.Canvas(filepath, pagesize=A4)
        c.setFont("Helvetica", 16)
        c.drawString(72, 750, "Longest filename PDF on Windows (NTFS max=255)")
        c.setFont("Helvetica", 12)
        c.drawString(72, 720, f"Actual directory: {script_dir}")
        c.drawString(72, 700, f"Virtual drive: {drive}")
        c.drawString(72, 680, f"Filename length: {len(filename)} chars")
        c.drawString(72, 660, f"Full path length (virtual): {len(filepath)} chars")
        c.drawString(72, 640, f"MAX_PATH limit: 260 (usable: 259)")
        c.drawString(72, 620, f"NTFS filename limit: 255")
        c.drawString(72, 600, f"Effective max filename: {max_filename_len} chars")
        c.save()

        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f"\n-> OK: Created successfully ({size} bytes)")
            # 実ファイルのパスを表示
            real_path = os.path.join(script_dir, filename)
            print(f"   Real path: {real_path[:60]}...{real_path[-10:]}")
        else:
            print("\n-> FAIL: File not found after creation")

    except Exception as e:
        print(f"\n-> ERROR: {e}")

    finally:
        # 仮想ドライブを解除
        subprocess.run(
            ["subst", drive, "/d"],
            capture_output=True, text=True,
        )
        print(f"\nUnmounted: {drive}")


if __name__ == "__main__":
    main()
