"""
自動修復（Self-Healing）モジュール

テスト失敗時に、現在のページ状態を解析して
壊れたロケーターを自動的に修復する。
"""

from __future__ import annotations

import re
from pathlib import Path

import anthropic
from playwright.sync_api import Page

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, MAX_HEAL_ATTEMPTS
from generator.page_analyzer import PageAnalyzer


HEAL_PROMPT = """\
あなたは Playwright (Python) テストの自動修復エキスパートです。

テストが失敗しました。失敗した箇所のコードと、現在のページ構造を提供します。
壊れたロケーターを修正し、修正後のコード行のみを返してください。

## ルール
- ロケーター優先順位: get_by_role > get_by_label > get_by_placeholder > get_by_text > get_by_test_id > locator
- 修正後のコード行のみを出力（説明不要）
- ```python で囲む
"""


class SelfHealer:
    """テスト失敗時にロケーターを自動修復する"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.analyzer = PageAnalyzer()

    def heal_locator(
        self,
        page: Page,
        failed_line: str,
        error_message: str,
    ) -> str | None:
        """
        壊れたロケーターを修復する。

        Args:
            page: 現在の Playwright Page オブジェクト
            failed_line: 失敗したコード行
            error_message: エラーメッセージ
        Returns:
            修復されたコード行。修復できない場合は None。
        """
        # 現在のページ状態を解析
        snapshot = self.analyzer.analyze(page)

        user_message = f"""\
## 失敗したコード行
```python
{failed_line}
```

## エラーメッセージ
```
{error_message}
```

## 現在のページ構造
{snapshot.to_prompt_context()}

上記の情報から、正しいロケーターに修正してください。
"""

        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=500,
            system=HEAL_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        fixed_line = self._extract_code_block(response.content[0].text)
        return fixed_line if fixed_line != failed_line else None

    def heal_test_file(
        self,
        test_file: Path,
        failed_line_number: int,
        failed_line: str,
        fixed_line: str,
    ) -> bool:
        """
        テストファイル内の壊れた行を修正して書き戻す。

        Args:
            test_file: テストファイルパス
            failed_line_number: 失敗した行番号（1始まり）
            failed_line: 元の行
            fixed_line: 修正後の行
        Returns:
            修正が成功したかどうか
        """
        lines = test_file.read_text(encoding="utf-8").splitlines(keepends=True)
        idx = failed_line_number - 1

        if idx < 0 or idx >= len(lines):
            return False

        # インデントを保持
        original_indent = re.match(r"(\s*)", lines[idx]).group(1)
        fixed_stripped = fixed_line.strip()
        lines[idx] = f"{original_indent}{fixed_stripped}\n"

        test_file.write_text("".join(lines), encoding="utf-8")
        return True

    def _extract_code_block(self, text: str) -> str:
        """応答からコードを抽出"""
        pattern = r"```python\s*\n(.*?)```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()
