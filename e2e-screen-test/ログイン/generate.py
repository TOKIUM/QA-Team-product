#!/usr/bin/env python3
"""
E2E テスト生成 CLI

使い方:
    # シナリオからテストコードを生成
    python generate.py scenarios/login.yaml

    # 全シナリオを一括生成
    python generate.py --all

    # 失敗したテストを自動修復
    python generate.py --heal generated_tests/test_login.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from playwright.sync_api import sync_playwright

from config import SCENARIOS_DIR, GENERATED_TESTS_DIR, HEADLESS, VIEWPORT, DEFAULT_TIMEOUT
from generator.page_analyzer import PageAnalyzer
from generator.code_generator import generate_test_code, load_scenario, save_generated_test

console = Console()


def collect_page_snapshots(scenario: dict) -> dict:
    """
    シナリオに含まれる URL を巡回し、各ページのスナップショットを収集する。
    """
    base_url = scenario.get("base_url", "")
    analyzer = PageAnalyzer()
    snapshots = {}

    # シナリオから一意な URL を抽出
    urls = set()
    for test in scenario.get("tests", []):
        for step in test.get("steps", []):
            if step.get("action") == "goto":
                url = step.get("url", "")
                full_url = f"{base_url}{url}" if url.startswith("/") else url
                urls.add(full_url)

    if not urls:
        urls.add(base_url)

    console.print(f"\n[bold blue]📡 {len(urls)} ページを解析中...[/bold blue]")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context(viewport=VIEWPORT)
        context.set_default_timeout(DEFAULT_TIMEOUT)
        page = context.new_page()

        for url in sorted(urls):
            try:
                console.print(f"  → {url}")
                page.goto(url, wait_until="networkidle")
                snapshot = analyzer.analyze(page)
                snapshots[url] = snapshot
                console.print(f"    ✅ 要素数: {len(snapshot.interactive_elements)}")
            except Exception as e:
                console.print(f"    [red]❌ エラー: {e}[/red]")

        browser.close()

    return snapshots


def generate_from_scenario(scenario_path: Path) -> None:
    """1つのシナリオファイルからテストを生成"""
    console.print(Panel(
        f"[bold]シナリオ読み込み: {scenario_path.name}[/bold]",
        style="blue",
    ))

    scenario = load_scenario(scenario_path)
    scenario_name = scenario.get("name", scenario_path.stem)

    # Step 1: ページ解析
    snapshots = collect_page_snapshots(scenario)

    if not snapshots:
        console.print("[red]ページのスナップショットを取得できませんでした。[/red]")
        return

    # Step 2: AI でテストコード生成
    console.print(f"\n[bold blue]🤖 Claude API でテストコード生成中...[/bold blue]")
    code = generate_test_code(scenario, snapshots)

    # Step 3: ファイル保存
    filepath = save_generated_test(scenario_name, code)
    console.print(f"\n[bold green]✅ テスト生成完了![/bold green]")
    console.print(f"   📄 {filepath}")
    console.print(f"\n[dim]実行: pytest {filepath} -v[/dim]")

    # 生成されたコードをプレビュー
    console.print(Panel(code, title="生成されたテストコード", border_style="green"))


def generate_all() -> None:
    """全シナリオファイルからテストを生成"""
    scenario_files = list(SCENARIOS_DIR.glob("*.yaml")) + list(SCENARIOS_DIR.glob("*.yml"))

    if not scenario_files:
        console.print(f"[red]シナリオファイルが見つかりません: {SCENARIOS_DIR}[/red]")
        return

    console.print(f"[bold]{len(scenario_files)} 個のシナリオを処理します[/bold]\n")

    for path in sorted(scenario_files):
        generate_from_scenario(path)
        console.print()


def main():
    parser = argparse.ArgumentParser(description="AI-Powered E2E テスト生成ツール")
    parser.add_argument("scenario", nargs="?", type=Path, help="シナリオファイルパス (.yaml)")
    parser.add_argument("--all", action="store_true", help="全シナリオを一括生成")
    parser.add_argument("--heal", type=Path, help="失敗したテストファイルを自動修復")

    args = parser.parse_args()

    if args.all:
        generate_all()
    elif args.heal:
        console.print("[yellow]自動修復モードは次のバージョンで実装予定です[/yellow]")
        # TODO: pytest を実行し、失敗箇所を検出して SelfHealer を呼び出す
    elif args.scenario:
        if not args.scenario.exists():
            console.print(f"[red]ファイルが見つかりません: {args.scenario}[/red]")
            sys.exit(1)
        generate_from_scenario(args.scenario)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
