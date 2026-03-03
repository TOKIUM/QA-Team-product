#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""evaluate_testcases.py / learn_benchmark.py 共通モジュール

ヘッダー自動検出、カラム検出、シートフィルタリング等の共通関数を集約。
"""
import re


# =====================================================================
# ヘッダー検出用キーワード辞書
# =====================================================================

HEADER_KEYWORDS = {
    'no':       ['No', 'NO', 'no', 'No.'],
    'confirm':  ['確認すること', '確認項目', 'テスト項目'],
    'screen':   ['画面'],
    'target':   ['確認対象'],
    'detail':   ['詳細'],
    'steps':    ['手順', 'テスト実行手順', '実行手順', 'テスト手順', '操作手順'],
    'expected': ['期待値', '期待結果', '確認結果'],
    'notes':    ['備考'],
}


# =====================================================================
# 学習/評価対象外のシート名パターン
# =====================================================================

SKIP_SHEET_PATTERNS = [
    '改善前',       # 改善前のテストケース（比較用に残されたもの）
    '質問',         # 質問・レビュー指摘・振り返りシート
    '振り返り',     # 同上
    'レビュー指摘', # 同上
    'memo',         # メモシート
    'シナリオ',     # テストシナリオシート（構造が異なる）
    '運用ルール',   # 運用ルールシート
    '進捗',         # 進捗管理シート
    'チェック表',   # テスト実施チェックシート
    'バグ',         # バグ一覧・バグ発生率シート
    'スクショ',     # スクリーンショットシート
]


# =====================================================================
# 曖昧表現の例外パターン（偽陽性除外用）
# =====================================================================

VAGUE_EXCEPTIONS = [
    # 「スペルと英語が適切であること」→ 英語化チェックの文脈では具体的
    r'(?:スペル|英語|英訳|翻訳|表記).*適切であること',
    # 「正しくありません」→ エラーメッセージの引用
    r'正しくありません',
    # 「正しく入力」→ バリデーションの文脈
    r'正しく入力',
]


# =====================================================================
# 共通関数
# =====================================================================

def detect_header_row(ws, max_search=10):
    """ヘッダー行を自動検出（最初の10行以内で「期待値」「手順」を含む行を探す）"""
    for row in range(1, min(max_search + 1, ws.max_row + 1)):
        row_text = ''
        for col in range(1, min(ws.max_column + 1, 30)):
            val = ws.cell(row=row, column=col).value
            if val:
                row_text += str(val)
        if '期待' in row_text or '手順' in row_text:
            return row
    return None


def detect_columns(ws, header_row):
    """ヘッダー行からカラムマッピングを検出（辞書ベース）"""
    col_map = {}
    for col in range(1, min(ws.max_column + 1, 30)):
        val = ws.cell(row=header_row, column=col).value
        if not val:
            continue
        val_str = str(val).strip()
        for key, keywords in HEADER_KEYWORDS.items():
            if key in col_map:
                continue
            for kw in keywords:
                if kw == val_str or kw in val_str:
                    col_map[key] = col
                    break
    return col_map


def find_sheet(wb, candidates):
    """候補名のリストからシートを探す"""
    for name in candidates:
        if name in wb.sheetnames:
            return wb[name]
    # 部分一致で探す
    for name in wb.sheetnames:
        for cand in candidates:
            if cand in name:
                return wb[name]
    return None


def should_skip_sheet(sheet_name):
    """シート名がスキップ対象かどうかを判定"""
    for pattern in SKIP_SHEET_PATTERNS:
        if pattern in sheet_name:
            return True
    return False


def merge_stats(all_stats):
    """複数シートの統計を統合"""
    merged = {
        'case_count': 0,
        'expected_lengths': [],
        'steps_lengths': [],
        'with_steps': 0,
        'with_numbered_steps': 0,
        'with_preconditions': 0,
        'koto_1': 0,
        'koto_2plus': 0,
        'vague_count': 0,
        'good_ending_count': 0,
        'expected_count': 0,
        'endings': {},
    }
    for s in all_stats:
        merged['case_count'] += s['case_count']
        merged['expected_lengths'].extend(s['expected_lengths'])
        merged['steps_lengths'].extend(s['steps_lengths'])
        merged['with_steps'] += s['with_steps']
        merged['with_numbered_steps'] += s['with_numbered_steps']
        merged['with_preconditions'] += s['with_preconditions']
        merged['koto_1'] += s['koto_1']
        merged['koto_2plus'] += s['koto_2plus']
        merged['vague_count'] += s['vague_count']
        merged['good_ending_count'] += s['good_ending_count']
        merged['expected_count'] += s['expected_count']
        for k, v in s['endings'].items():
            merged['endings'][k] = merged['endings'].get(k, 0) + v
    return merged


def strip_parens(text):
    """括弧内の補足コメントを除外する

    例: 「保存できること（保存しても作成した問題に支障がないこと)」
      → 括弧内の「こと」は補足メモなので除外
    """
    return re.sub(r'[（(][^）)]*[）)]', '', text)


def is_vague_exception(text):
    """曖昧表現の偽陽性チェック（例外パターンに該当するかどうか）"""
    return any(re.search(exc, text) for exc in VAGUE_EXCEPTIONS)
