"""
ページ解析モジュール

Playwright を使ってページのアクセシビリティツリーと HTML 構造を取得し、
Claude が理解しやすい形式に変換する。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from playwright.sync_api import Page


@dataclass
class PageSnapshot:
    """ページ構造のスナップショット"""
    url: str
    title: str
    accessibility_tree: str
    interactive_elements: list[dict] = field(default_factory=list)
    form_structure: list[dict] = field(default_factory=list)

    def to_prompt_context(self) -> str:
        """Claude API に渡すコンテキスト文字列を生成"""
        parts = [
            f"## ページ情報",
            f"- URL: {self.url}",
            f"- タイトル: {self.title}",
            "",
            f"## アクセシビリティツリー",
            self.accessibility_tree,
            "",
            f"## インタラクティブ要素一覧",
            json.dumps(self.interactive_elements, ensure_ascii=False, indent=2),
        ]
        if self.form_structure:
            parts.extend([
                "",
                f"## フォーム構造",
                json.dumps(self.form_structure, ensure_ascii=False, indent=2),
            ])
        return "\n".join(parts)


class PageAnalyzer:
    """Playwright を使ってページ構造を解析する"""

    def analyze(self, page: Page) -> PageSnapshot:
        """ページのスナップショットを取得"""
        # アクセシビリティツリーを取得
        a11y_tree = self._get_accessibility_tree(page)

        # インタラクティブ要素を収集
        interactive = self._get_interactive_elements(page)

        # フォーム構造を解析
        forms = self._get_form_structure(page)

        return PageSnapshot(
            url=page.url,
            title=page.title(),
            accessibility_tree=a11y_tree,
            interactive_elements=interactive,
            form_structure=forms,
        )

    def _get_accessibility_tree(self, page: Page) -> str:
        """アクセシビリティツリーをテキスト形式で取得"""
        snapshot = page.accessibility.snapshot()
        if not snapshot:
            return "(アクセシビリティツリーを取得できませんでした)"
        return self._format_a11y_node(snapshot)

    def _format_a11y_node(self, node: dict, indent: int = 0) -> str:
        """アクセシビリティノードを読みやすいテキストに整形"""
        prefix = "  " * indent
        role = node.get("role", "")
        name = node.get("name", "")
        value = node.get("value", "")

        parts = [f"{prefix}[{role}]"]
        if name:
            parts.append(f'"{name}"')
        if value:
            parts.append(f"value={value}")

        # 追加属性
        for attr in ("checked", "disabled", "required", "expanded", "selected"):
            if node.get(attr) is not None:
                parts.append(f"{attr}={node[attr]}")

        line = " ".join(parts)
        lines = [line]

        for child in node.get("children", []):
            lines.append(self._format_a11y_node(child, indent + 1))

        return "\n".join(lines)

    def _get_interactive_elements(self, page: Page) -> list[dict]:
        """クリック・入力可能な要素を一覧取得"""
        return page.evaluate("""() => {
            const selectors = [
                'a[href]', 'button', 'input', 'select', 'textarea',
                '[role="button"]', '[role="link"]', '[role="tab"]',
                '[role="menuitem"]', '[role="checkbox"]', '[role="radio"]',
                '[onclick]', '[tabindex]'
            ];
            const elements = document.querySelectorAll(selectors.join(','));
            return Array.from(elements).slice(0, 100).map(el => {
                const rect = el.getBoundingClientRect();
                return {
                    tag: el.tagName.toLowerCase(),
                    type: el.getAttribute('type') || null,
                    role: el.getAttribute('role') || null,
                    name: el.getAttribute('name') || null,
                    id: el.getAttribute('id') || null,
                    text: (el.textContent || '').trim().slice(0, 100),
                    ariaLabel: el.getAttribute('aria-label') || null,
                    placeholder: el.getAttribute('placeholder') || null,
                    label: (() => {
                        // 関連する <label> を探す
                        if (el.id) {
                            const lbl = document.querySelector(`label[for="${el.id}"]`);
                            if (lbl) return lbl.textContent.trim();
                        }
                        const parent = el.closest('label');
                        return parent ? parent.textContent.trim().slice(0, 100) : null;
                    })(),
                    testId: el.getAttribute('data-testid') || null,
                    visible: rect.width > 0 && rect.height > 0,
                    disabled: el.disabled || false,
                };
            }).filter(el => el.visible);
        }""")

    def _get_form_structure(self, page: Page) -> list[dict]:
        """フォームとその内部要素の構造を取得"""
        return page.evaluate("""() => {
            const forms = document.querySelectorAll('form');
            return Array.from(forms).map(form => ({
                id: form.id || null,
                action: form.action || null,
                method: form.method || 'get',
                fields: Array.from(form.querySelectorAll('input,select,textarea')).map(f => ({
                    tag: f.tagName.toLowerCase(),
                    type: f.getAttribute('type') || 'text',
                    name: f.getAttribute('name') || null,
                    id: f.getAttribute('id') || null,
                    label: (() => {
                        if (f.id) {
                            const lbl = document.querySelector(`label[for="${f.id}"]`);
                            if (lbl) return lbl.textContent.trim();
                        }
                        return null;
                    })(),
                    placeholder: f.getAttribute('placeholder') || null,
                    required: f.required || false,
                }))
            }));
        }""")
