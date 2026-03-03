"""
3000件CSVを生成（識別可能な請求書番号 + 備考に「自動生成」）
- 請求書番号: AUTO3K-0001 〜 AUTO3K-3000
- 備考: 自動生成
- cp932エンコーディング
- 元CSVと同じ列構成
"""

import os

test_dir = os.path.dirname(os.path.abspath(__file__))

header = "請求書番号,請求日,期日,取引先コード,取引先名称,取引先敬称,取引先郵便番号,取引先都道府県,取引先住所１,取引先住所２,当月請求額,備考,取引日付,内容,数量,単価,単位,金額,税率"

rows = []
for i in range(1, 3001):
    inv_num = f"AUTO3K-{i:04d}"
    # 税率は8と10を交互に
    tax_rate = 8 if i % 2 == 0 else 10
    # 金額は10000〜100000の範囲
    amount = 10000 + (i * 30) % 90001
    row = f"{inv_num},2025/02/16,2025/03/31,TH003,,,,,,,,自動生成,,,1,{amount},式,{amount},{tax_rate}"
    rows.append(row)

csv_content = header + "\n" + "\n".join(rows) + "\n"
csv_path = os.path.join(test_dir, "auto3k_invoices.csv")

with open(csv_path, "w", encoding="cp932") as f:
    f.write(csv_content)

print(f"生成完了: {csv_path}")
print(f"行数: {len(rows)} + ヘッダー1行")
print(f"先頭3行:")
for r in rows[:3]:
    print(f"  {r}")
print(f"末尾3行:")
for r in rows[-3:]:
    print(f"  {r}")
print(f"ファイルサイズ: {os.path.getsize(csv_path):,} bytes")
