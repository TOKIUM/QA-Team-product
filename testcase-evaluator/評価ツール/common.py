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
    'priority': ['優先度', '優先', 'Priority'],
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
# 画面名NGパターン（チェック7: 画面名・フォーマット）
# =====================================================================

# 7a. 画面名フォーマット
SCREEN_NAME_URL_PATTERN = r'[（(]/[a-zA-Z]'  # URL混入（例: 「画面名（/admin/...）」）
SCREEN_NAME_IMPL_TERMS = ['モーダル', 'ドロワー', 'コンポーネント', 'ダイアログ']
SCREEN_NAME_VAGUE = ['全画面共通', '全画面', '共通画面', '各画面']

# 7b. 手順フォーマット
FORMAT_PRECONDITION_KEYWORDS = ['【前提条件】', '【セットアップ】', '【前提】']
FORMAT_EXECUTION_KEYWORDS = ['【実行手順】']

# セキュリティ関連キーワード（チェック6拡張: P1推奨）
SECURITY_KEYWORDS = [
    '認証', 'ログイン', 'パスワード', 'セッション', '権限',
    'SAML', 'SSO', '脆弱性', 'XSS', 'SQLi', 'CSRF',
    'アクセス制御', 'トークン', '暗号', '署名',
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


# =====================================================================
# テスト手順フォーマッター
# =====================================================================

def format_test_steps(preconditions, steps):
    """前提条件と実行手順を統一フォーマットで整形する。

    Args:
        preconditions: 前提条件のリスト（文字列のリスト）。空リストなら省略。
        steps: 実行手順のリスト（文字列のリスト）。番号なしで渡す。

    Returns:
        整形済みの手順文字列。

    出力例:
        【前提条件】
        ・パスワード変更画面でパスワードを入力済みであること

        【実行手順】
        1. 「パスワードを変更する」ボタンをクリックする
    """
    parts = []
    if preconditions:
        parts.append("【前提条件】")
        for p in preconditions:
            parts.append(f"・{p}")
        parts.append("")  # 空行で区切り

    parts.append("【実行手順】")
    for i, s in enumerate(steps, 1):
        parts.append(f"{i}. {s}")

    return "\n".join(parts)
