"""
テストコード生成モジュール

シナリオ定義 + ページ解析結果を Claude API に渡し、
Playwright の pytest テストコードを生成する。
"""

from __future__ import annotations

import re
import yaml
from pathlib import Path

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, GENERATED_TESTS_DIR
from generator.page_analyzer import PageSnapshot


SYSTEM_PROMPT = """\
あなたは Playwright (Python) の E2E テストコード生成の専門家です。
以下のルールに厳密に従って、pytest + playwright のテストコードを生成してください。

## ロケーター選択の優先順位（必ず上から順に検討すること）
1. get_by_role()     - ARIA ロール + アクセシブル名（最も安定）
2. get_by_label()    - <label> に紐づくフォーム要素
3. get_by_placeholder() - placeholder 属性
4. get_by_text()     - テキストコンテンツ（完全一致 or 部分一致）
5. get_by_test_id()  - data-testid 属性がある場合
6. locator()         - CSS セレクタ（最終手段）

## コード規約
- pytest スタイル（class ではなく関数ベース）
- 関数名は test_ で始め、内容が分かる英語名
- 日本語コメントで各ステップを説明
- expect() による明示的アサーション
- ハードコードの wait/sleep は禁止（Playwright の auto-wait を活用）
- 1テスト1ファイルの原則

## 出力形式
- Python コードのみを出力（説明文は不要）
- ```python で囲む
- import 文を含める
"""


def generate_test_code(
    scenario: dict,
    page_snapshots: dict[str, PageSnapshot],
) -> str:
    """
    シナリオとページスナップショットから Playwright テストコードを生成する。

    Args:
        scenario: YAML から読み込んだシナリオ定義
        page_snapshots: URL をキーとしたページスナップショットの辞書
    Returns:
        生成された Python テストコード文字列
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # ページコンテキストをまとめる
    page_context_parts = []
    for url, snapshot in page_snapshots.items():
        page_context_parts.append(f"### ページ: {url}\n{snapshot.to_prompt_context()}")
    page_context = "\n\n---\n\n".join(page_context_parts)

    # シナリオを YAML 文字列に変換
    scenario_yaml = yaml.dump(scenario, allow_unicode=True, default_flow_style=False)

    user_message = f"""\
以下のテストシナリオと、対象ページの構造情報から、Playwright (Python) のテストコードを生成してください。

## テストシナリオ
```yaml
{scenario_yaml}
```

## ページ構造情報
{page_context}

上記の情報を元に、最も安定するロケーターを選択してテストコードを生成してください。
base_url は "{scenario.get('base_url', '')}" です。
"""

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    # レスポンスからコードブロックを抽出
    code = _extract_code_block(response.content[0].text)
    return code


def _extract_code_block(text: str) -> str:
    """Claude の応答から Python コードブロックを抽出"""
    pattern = r"```python\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # コードブロックがない場合はそのまま返す
    return text.strip()


def load_scenario(path: Path) -> dict:
    """YAML シナリオファイルを読み込む"""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_generated_test(scenario_name: str, code: str) -> Path:
    """生成されたテストコードをファイルに保存"""
    GENERATED_TESTS_DIR.mkdir(parents=True, exist_ok=True)

    # ファイル名を安全な形式に
    safe_name = re.sub(r"[^\w]", "_", scenario_name).lower()
    filename = f"test_{safe_name}.py"
    filepath = GENERATED_TESTS_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code + "\n")

    return filepath
