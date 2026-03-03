"""Tkinter デスクトップ GUI."""

from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import yaml

from .csv_parser import parse_directory
from .http_client import ApiClient
from .reporter import Reporter
from .test_runner import TestRunner


class App(tk.Tk):
    """API Test Runner GUI."""

    def __init__(self, project_root: Path):
        super().__init__()
        self.project_root = project_root
        self.title("API Test Runner")
        self.geometry("900x650")
        self.minsize(750, 500)

        self._queue: queue.Queue = queue.Queue()
        self._running = False
        self._results_map: dict = {}  # name -> TestResult
        self._current_hist_ts: str | None = None  # 選択中の履歴タイムスタンプ

        # タブ構成
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self._tab_run = ttk.Frame(notebook)
        self._tab_response = ttk.Frame(notebook)
        self._tab_settings = ttk.Frame(notebook)
        self._tab_history = ttk.Frame(notebook)

        notebook.add(self._tab_run, text=" テスト実行 ")
        notebook.add(self._tab_response, text=" レスポンス ")
        notebook.add(self._tab_settings, text=" 設定 ")
        notebook.add(self._tab_history, text=" 履歴 ")

        self._build_run_tab()
        self._build_response_tab()
        self._build_settings_tab()
        self._build_history_tab()

    # ──────────────────────────────────────────────
    # Tab 1: テスト実行
    # ──────────────────────────────────────────────
    def _build_run_tab(self):
        tab = self._tab_run

        # CSV ディレクトリ選択
        top = ttk.Frame(tab)
        top.pack(fill=tk.X, padx=8, pady=(8, 4))

        ttk.Label(top, text="CSV:").pack(side=tk.LEFT)
        self._csv_var = tk.StringVar(value="document")
        csv_entry = ttk.Entry(top, textvariable=self._csv_var, width=40)
        csv_entry.pack(side=tk.LEFT, padx=(4, 4))
        ttk.Button(top, text="フォルダ変更...", command=self._browse_csv_dir).pack(side=tk.LEFT)
        ttk.Button(top, text="CSV追加...", command=self._add_csv_files).pack(side=tk.LEFT, padx=(4, 0))

        self._info_label = ttk.Label(top, text="")
        self._info_label.pack(side=tk.RIGHT, padx=8)

        # CSV ファイル一覧
        csv_list_frame = ttk.LabelFrame(tab, text="CSV ファイル一覧")
        csv_list_frame.pack(fill=tk.X, padx=8, pady=(0, 4))
        self._csv_listbox = tk.Listbox(csv_list_frame, height=4)
        self._csv_listbox.pack(fill=tk.X, padx=4, pady=4)
        self._refresh_csv_list()

        # 実行ボタン
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=8, pady=4)
        self._run_btn = ttk.Button(btn_frame, text="\u25b6 テスト実行", command=self._start_tests)
        self._run_btn.pack(side=tk.LEFT)
        self._progress_label = ttk.Label(btn_frame, text="")
        self._progress_label.pack(side=tk.LEFT, padx=12)

        # 結果 Treeview
        tree_frame = ttk.LabelFrame(tab, text="結果一覧")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        columns = ("pattern", "expected", "actual", "time", "result")
        self._tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=8)
        self._tree.heading("pattern", text="パターン")
        self._tree.heading("expected", text="期待")
        self._tree.heading("actual", text="実際")
        self._tree.heading("time", text="時間")
        self._tree.heading("result", text="結果")

        self._tree.column("pattern", width=100, anchor=tk.CENTER)
        self._tree.column("expected", width=60, anchor=tk.CENTER)
        self._tree.column("actual", width=60, anchor=tk.CENTER)
        self._tree.column("time", width=80, anchor=tk.E)
        self._tree.column("result", width=60, anchor=tk.CENTER)

        # Treeview に テスト名列を追加 (#0 を使わず columns の先頭に)
        self._tree["columns"] = ("name",) + columns
        self._tree.heading("name", text="テスト名")
        self._tree.column("name", width=200)

        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=tree_scroll.set)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._tree.tag_configure("pass", foreground="#228B22")
        self._tree.tag_configure("fail", foreground="#DC143C")
        self._tree.tag_configure("warn", foreground="#E67E22")
        self._tree.bind("<<TreeviewSelect>>", lambda e: self._on_result_selected())

        # リクエスト詳細パネル
        detail_frame = ttk.LabelFrame(tab, text="リクエスト詳細 (行を選択)")
        detail_frame.pack(fill=tk.X, padx=8, pady=4)
        self._detail_text = tk.Text(detail_frame, height=5, state=tk.DISABLED,
                                    wrap=tk.WORD, font=("Consolas", 9))
        self._detail_text.pack(fill=tk.X, padx=4, pady=4)

        # ログ欄
        log_frame = ttk.LabelFrame(tab, text="ログ")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))

        self._log = tk.Text(log_frame, height=6, state=tk.DISABLED, wrap=tk.WORD,
                            font=("Consolas", 9))
        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self._log.yview)
        self._log.configure(yscrollcommand=log_scroll.set)
        self._log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # サマリー
        self._summary_label = ttk.Label(tab, text="")
        self._summary_label.pack(fill=tk.X, padx=8, pady=(0, 6))

    def _refresh_csv_list(self):
        """CSV ディレクトリ内のファイル一覧を更新."""
        self._csv_listbox.delete(0, tk.END)
        csv_dir = self.project_root / self._csv_var.get()
        if csv_dir.exists():
            for f in sorted(csv_dir.glob("*.csv")):
                self._csv_listbox.insert(tk.END, f.name)
        count = self._csv_listbox.size()
        if count == 0:
            self._csv_listbox.insert(tk.END, "(CSV ファイルがありません)")

    def _browse_csv_dir(self):
        """CSV ディレクトリ自体を変更する."""
        d = filedialog.askdirectory(
            initialdir=str(self.project_root),
            title="CSV ディレクトリを選択",
        )
        if d:
            try:
                rel = Path(d).relative_to(self.project_root)
                self._csv_var.set(str(rel))
            except ValueError:
                self._csv_var.set(d)
            self._refresh_csv_list()

    def _add_csv_files(self):
        """CSV ファイルを選択して document フォルダにコピー."""
        import shutil
        files = filedialog.askopenfilenames(
            initialdir=str(Path.home() / "Desktop"),
            title="追加する CSV ファイルを選択",
            filetypes=[("CSV ファイル", "*.csv"), ("すべてのファイル", "*.*")],
        )
        if not files:
            return
        csv_dir = self.project_root / self._csv_var.get()
        csv_dir.mkdir(parents=True, exist_ok=True)
        added = []
        for src in files:
            src_path = Path(src)
            dest = csv_dir / src_path.name
            shutil.copy2(str(src_path), str(dest))
            added.append(src_path.name)
        self._refresh_csv_list()
        messagebox.showinfo("CSV 追加", f"{len(added)} ファイルを追加しました:\n" + "\n".join(added))

    def _log_append(self, msg: str):
        self._log.configure(state=tk.NORMAL)
        self._log.insert(tk.END, msg + "\n")
        self._log.see(tk.END)
        self._log.configure(state=tk.DISABLED)

    def _start_tests(self):
        if self._running:
            return

        # 設定読み込み
        from .__main__ import load_config, load_env, resolve_settings

        config = load_config(self.project_root / "config.yaml")
        env = load_env(self.project_root / ".env")
        base_url, api_key = resolve_settings(config, env)

        if not base_url or not api_key:
            messagebox.showerror("設定エラー", "BASE_URL または API_KEY が未設定です。\n設定タブで入力してください。")
            return

        csv_dir = self.project_root / self._csv_var.get()
        if not csv_dir.exists():
            messagebox.showerror("エラー", f"CSV ディレクトリが見つかりません:\n{csv_dir}")
            return

        methods = config.get("test", {}).get("methods", ["GET", "POST"])
        specs = parse_directory(csv_dir, methods=methods)
        if not specs:
            messagebox.showerror("エラー", f"有効な API 仕様が見つかりません:\n{csv_dir}")
            return

        # UI 準備
        self._tree.delete(*self._tree.get_children())
        self._results_map.clear()
        self._detail_text.configure(state=tk.NORMAL)
        self._detail_text.delete("1.0", tk.END)
        self._detail_text.configure(state=tk.DISABLED)
        self._log.configure(state=tk.NORMAL)
        self._log.delete("1.0", tk.END)
        self._log.configure(state=tk.DISABLED)
        self._summary_label.configure(text="")
        self._running = True
        self._run_btn.configure(state=tk.DISABLED)

        test_config = config.get("test", {})
        timeout = test_config.get("timeout", 30)
        retry_config = test_config.get("retry", {})
        max_retries = retry_config.get("max_retries", 0)
        retry_delay = retry_config.get("delay", 1.0)
        results_dir_name = config.get("output", {}).get("results_dir", "results")
        results_dir = self.project_root / results_dir_name

        client = ApiClient(base_url, api_key, timeout=timeout,
                           max_retries=max_retries, retry_delay=retry_delay)
        runner = TestRunner(config, client, results_dir)
        test_cases = runner.generate_test_cases(specs)
        custom_tests = runner.load_custom_tests()
        test_cases.extend(custom_tests)

        get_count = sum(1 for tc in test_cases if tc.method == "GET")
        post_count = sum(1 for tc in test_cases if tc.method == "POST")
        method_info = f"GET:{get_count}"
        if post_count:
            method_info += f" POST:{post_count}"
        self._info_label.configure(text=f"{len(specs)} APIs / {len(test_cases)} tests ({method_info})")
        self._log_append(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] テスト開始 ({len(test_cases)} cases)")

        t = threading.Thread(
            target=self._run_tests_thread,
            args=(runner, client, test_cases, results_dir),
            daemon=True,
        )
        t.start()
        self.after(100, self._check_queue)

    def _run_tests_thread(self, runner: TestRunner, client: ApiClient,
                          test_cases: list, results_dir: Path):
        """バックグラウンドでテスト実行し、結果を queue に送る."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        run_dir = results_dir / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)

        results = []
        for tc in test_cases:
            result = client.execute(tc)

            # スキーマ検証
            if result.passed and result.response_body is not None:
                warnings = TestRunner._validate_schema(result)
                result.schema_warnings = warnings

            # JSON 保存
            if result.response_body is not None:
                output_file = run_dir / f"{tc.name}.json"
                with open(output_file, "w", encoding="utf-8", newline="\n") as f:
                    json.dump(result.response_body, f,
                              indent=runner.json_indent, ensure_ascii=False)
                    f.write("\n")
                result.output_file = str(output_file)

            results.append(result)
            self._queue.put(("result", result))

        # latest.txt 更新
        latest_file = results_dir / "latest.txt"
        with open(latest_file, "w", encoding="utf-8") as f:
            f.write(timestamp + "\n")

        # レポート保存
        reporter = Reporter()
        reporter.save_report(results, results_dir)
        reporter.save_html_report(results, results_dir)
        reporter.save_csv_report(results, results_dir)
        client.close()

        self._queue.put(("done", results))

    def _check_queue(self):
        try:
            while True:
                msg_type, data = self._queue.get_nowait()
                if msg_type == "result":
                    self._on_test_result(data)
                elif msg_type == "done":
                    self._on_tests_done(data)
        except queue.Empty:
            pass

        if self._running:
            self.after(100, self._check_queue)

    def _on_test_result(self, result):
        tc = result.test_case
        if not result.passed:
            tag = "fail"
            label = "FAIL"
        elif result.schema_warnings:
            tag = "warn"
            label = "WARN"
        else:
            tag = "pass"
            label = "PASS"
        elapsed = f"{result.elapsed_ms:.0f}ms"

        self._tree.insert("", tk.END, values=(
            tc.name, tc.pattern, tc.expected_status,
            result.status_code, elapsed, label,
        ), tags=(tag,))
        self._results_map[tc.name] = result

        desc = TestRunner._test_description(tc)
        log_msg = f"[{label}] {desc} ({elapsed})"
        if result.schema_warnings:
            log_msg += f" [{'; '.join(result.schema_warnings)}]"
        self._log_append(log_msg)

    def _on_result_selected(self):
        """結果行クリック → リクエスト詳細を表示."""
        sel = self._tree.selection()
        if not sel:
            return
        values = self._tree.item(sel[0], "values")
        name = values[0]
        result = self._results_map.get(name)
        if not result:
            return
        self._show_request_detail(self._detail_text, result)

    def _show_request_detail(self, text_widget: tk.Text, result):
        """TestResult からリクエスト詳細を Text ウィジェットに表示."""
        tc = result.test_case
        lines = []
        lines.append(f"{tc.method} {result.request_url or tc.url_path}")
        lines.append("")
        if result.request_headers:
            for k, v in result.request_headers.items():
                if k.lower() == "authorization":
                    v = v[:12] + "***" if len(v) > 12 else "***"
                lines.append(f"{k}: {v}")
        else:
            lines.append("Authorization: " + ("Bearer ***" if tc.use_auth else "(なし)"))
            lines.append("Accept: application/json")
        if tc.query_params:
            lines.append("")
            lines.append("Query Parameters:")
            for k, v in tc.query_params.items():
                lines.append(f"  {k} = {v}")
        lines.append("")
        if not result.passed:
            label = "FAIL"
        elif result.schema_warnings:
            label = "WARN"
        else:
            label = "PASS"
        lines.append(f"Status: {result.status_code} (expected {tc.expected_status}) [{label}] - {result.elapsed_ms:.0f}ms")

        if result.schema_warnings:
            lines.append("")
            lines.append("Schema Warnings:")
            for w in result.schema_warnings:
                lines.append(f"  - {w}")

        text_widget.configure(state=tk.NORMAL)
        text_widget.delete("1.0", tk.END)
        text_widget.insert("1.0", "\n".join(lines))
        text_widget.configure(state=tk.DISABLED)

    def _on_tests_done(self, results: list):
        self._running = False
        self._run_btn.configure(state=tk.NORMAL)
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        warn_count = sum(1 for r in results if r.passed and r.schema_warnings)

        # パターン別集計
        by_pattern: dict[str, dict[str, int]] = {}
        for r in results:
            pat = r.test_case.pattern
            if pat not in by_pattern:
                by_pattern[pat] = {"total": 0, "passed": 0}
            by_pattern[pat]["total"] += 1
            if r.passed:
                by_pattern[pat]["passed"] += 1

        summary = f"Results: {passed} passed, {failed} failed"
        if warn_count:
            summary += f", {warn_count} warn"
        summary += f" / {total} total"
        # パターン別を括弧内に追加
        pat_parts = [f"{p}:{c['passed']}/{c['total']}" for p, c in by_pattern.items()]
        if pat_parts:
            summary += "  [" + " ".join(pat_parts) + "]"
        self._summary_label.configure(text=summary)

        self._log_append(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] 完了 - {passed}/{total} passed")
        if warn_count:
            self._log_append(f"  Schema warnings: {warn_count} test(s)")
        # パターン別ログ
        for pat, counts in by_pattern.items():
            f = counts["total"] - counts["passed"]
            status = "ALL PASS" if f == 0 else f"{f} FAIL"
            self._log_append(f"  {pat}: {counts['passed']}/{counts['total']} ({status})")

        # 履歴・レスポンスタブを更新
        self._refresh_history_list()
        self._refresh_response_runs()

    # ──────────────────────────────────────────────
    # Tab 2: レスポンス閲覧
    # ──────────────────────────────────────────────
    def _build_response_tab(self):
        tab = self._tab_response
        self._resp_report_data: dict | None = None  # 選択中の report.json

        top = ttk.Frame(tab)
        top.pack(fill=tk.X, padx=8, pady=(8, 4))
        ttk.Label(top, text="実行結果:").pack(side=tk.LEFT)
        self._resp_run_var = tk.StringVar()
        self._resp_combo = ttk.Combobox(top, textvariable=self._resp_run_var,
                                        state="readonly", width=20)
        self._resp_combo.pack(side=tk.LEFT, padx=4)
        self._resp_combo.bind("<<ComboboxSelected>>", lambda e: self._on_resp_run_selected())

        # 左右ペイン
        paned = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 8))

        # ファイル一覧
        left = ttk.LabelFrame(paned, text="ファイル一覧")
        self._resp_listbox = tk.Listbox(left, width=24)
        self._resp_listbox.pack(fill=tk.BOTH, expand=True)
        self._resp_listbox.bind("<<ListboxSelect>>", lambda e: self._on_resp_file_selected())
        paned.add(left, weight=1)

        # 右ペイン: リクエスト/レスポンス サブタブ
        right = ttk.Frame(paned)
        paned.add(right, weight=3)

        resp_notebook = ttk.Notebook(right)
        resp_notebook.pack(fill=tk.BOTH, expand=True)

        # リクエストタブ
        req_tab = ttk.Frame(resp_notebook)
        resp_notebook.add(req_tab, text=" リクエスト ")
        self._resp_req_text = tk.Text(req_tab, state=tk.DISABLED, wrap=tk.WORD,
                                      font=("Consolas", 10))
        req_scroll = ttk.Scrollbar(req_tab, orient=tk.VERTICAL, command=self._resp_req_text.yview)
        self._resp_req_text.configure(yscrollcommand=req_scroll.set)
        self._resp_req_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        req_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # レスポンスタブ
        res_tab = ttk.Frame(resp_notebook)
        resp_notebook.add(res_tab, text=" レスポンス ")
        self._resp_text = tk.Text(res_tab, state=tk.DISABLED, wrap=tk.NONE,
                                  font=("Consolas", 10))
        resp_xscroll = ttk.Scrollbar(res_tab, orient=tk.HORIZONTAL, command=self._resp_text.xview)
        resp_yscroll = ttk.Scrollbar(res_tab, orient=tk.VERTICAL, command=self._resp_text.yview)
        self._resp_text.configure(xscrollcommand=resp_xscroll.set, yscrollcommand=resp_yscroll.set)
        self._resp_text.grid(row=0, column=0, sticky="nsew")
        resp_yscroll.grid(row=0, column=1, sticky="ns")
        resp_xscroll.grid(row=1, column=0, sticky="ew")
        res_tab.columnconfigure(0, weight=1)
        res_tab.rowconfigure(0, weight=1)

        self._refresh_response_runs()

    def _get_result_timestamps(self) -> list[str]:
        results_dir = self.project_root / "results"
        if not results_dir.exists():
            return []
        stamps = sorted(
            [d.name for d in results_dir.iterdir() if d.is_dir() and d.name.isdigit()],
            reverse=True,
        )
        return stamps

    def _refresh_response_runs(self):
        stamps = self._get_result_timestamps()
        self._resp_combo["values"] = stamps
        if stamps:
            self._resp_combo.current(0)
            self._on_resp_run_selected()

    def _on_resp_run_selected(self):
        ts = self._resp_run_var.get()
        if not ts:
            return
        run_dir = self.project_root / "results" / ts

        # report.json を読み込み（リクエスト情報用）
        report_path = run_dir / "report.json"
        if report_path.exists():
            with open(report_path, encoding="utf-8") as f:
                self._resp_report_data = json.load(f)
        else:
            self._resp_report_data = None

        # レスポンスファイル一覧（report.json は除外）
        files = sorted([
            f.name for f in run_dir.iterdir()
            if f.is_file() and f.suffix == ".json" and f.name != "report.json"
        ])
        self._resp_listbox.delete(0, tk.END)
        for f in files:
            self._resp_listbox.insert(tk.END, f)
        # クリア
        self._clear_text(self._resp_text)
        self._clear_text(self._resp_req_text)

    def _on_resp_file_selected(self):
        sel = self._resp_listbox.curselection()
        if not sel:
            return
        filename = self._resp_listbox.get(sel[0])
        ts = self._resp_run_var.get()

        # レスポンス JSON 表示
        filepath = self.project_root / "results" / ts / filename
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            pretty = json.dumps(data, indent=4, ensure_ascii=False)
        except Exception as e:
            pretty = f"Error: {e}"

        self._set_text(self._resp_text, pretty)

        # リクエスト情報表示（report.json から取得）
        req_info = self._build_request_info(filename)
        self._set_text(self._resp_req_text, req_info)

    def _build_request_info(self, filename: str) -> str:
        """report.json からファイル名に対応するリクエスト情報を組み立てる."""
        if not self._resp_report_data:
            return "(report.json がないため、リクエスト情報を表示できません)"

        # ファイル名 → テストエントリを検索
        entry = None
        for t in self._resp_report_data.get("tests", []):
            if t.get("output_file") == filename:
                entry = t
                break
        if not entry:
            return f"(report.json に {filename} の情報がありません)"

        lines = []
        # メソッド + URL
        url = entry.get("request_url") or entry.get("url_path", "")
        lines.append(f"{entry.get('method', 'GET')} {url}")
        lines.append("")

        # ヘッダー
        headers = entry.get("request_headers")
        if headers:
            lines.append("Headers:")
            for k, v in headers.items():
                lines.append(f"  {k}: {v}")
        else:
            lines.append("Headers:")
            lines.append("  Accept: application/json")
            if entry.get("use_auth"):
                lines.append("  Authorization: Bearer ***")
            else:
                lines.append("  (認証なし)")

        # クエリパラメータ
        params = entry.get("query_params", {})
        if params:
            lines.append("")
            lines.append("Query Parameters:")
            for k, v in params.items():
                lines.append(f"  {k} = {v}")

        # 結果
        lines.append("")
        passed = entry.get("passed", False)
        label = "PASS" if passed else "FAIL"
        lines.append(f"Status: {entry.get('actual_status')} "
                      f"(expected {entry.get('expected_status')}) "
                      f"[{label}] - {entry.get('elapsed_ms', 0):.0f}ms")

        return "\n".join(lines)

    @staticmethod
    def _set_text(widget: tk.Text, content: str):
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", content)
        widget.configure(state=tk.DISABLED)

    @staticmethod
    def _clear_text(widget: tk.Text):
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.configure(state=tk.DISABLED)

    # ──────────────────────────────────────────────
    # Tab 3: 設定
    # ──────────────────────────────────────────────
    def _build_settings_tab(self):
        tab = self._tab_settings

        from .__main__ import load_config, load_env

        config = load_config(self.project_root / "config.yaml")
        env = load_env(self.project_root / ".env")

        # 接続設定
        conn = ttk.LabelFrame(tab, text="接続設定")
        conn.pack(fill=tk.X, padx=8, pady=(8, 4))

        ttk.Label(conn, text="Base URL:").grid(row=0, column=0, sticky=tk.W, padx=4, pady=2)
        self._base_url_var = tk.StringVar(
            value=env.get("BASE_URL", config.get("api", {}).get("base_url", "")))
        ttk.Entry(conn, textvariable=self._base_url_var, width=50).grid(row=0, column=1,
                                                                         columnspan=2, sticky=tk.W, padx=4, pady=2)

        ttk.Label(conn, text="API Key:").grid(row=1, column=0, sticky=tk.W, padx=4, pady=2)
        self._api_key_var = tk.StringVar(value=env.get("API_KEY", ""))
        self._key_entry = ttk.Entry(conn, textvariable=self._api_key_var, width=50, show="\u2022")
        self._key_entry.grid(row=1, column=1, sticky=tk.W, padx=4, pady=2)
        self._key_visible = False
        ttk.Button(conn, text="表示/隠す", command=self._toggle_key).grid(row=1, column=2, padx=4)

        ttk.Label(conn, text="Timeout:").grid(row=2, column=0, sticky=tk.W, padx=4, pady=2)
        self._timeout_var = tk.IntVar(value=config.get("test", {}).get("timeout", 30))
        timeout_frame = ttk.Frame(conn)
        timeout_frame.grid(row=2, column=1, sticky=tk.W, padx=4, pady=2)
        ttk.Spinbox(timeout_frame, textvariable=self._timeout_var, from_=1, to=120, width=5).pack(side=tk.LEFT)
        ttk.Label(timeout_frame, text=" 秒").pack(side=tk.LEFT)

        # テストパターン
        pat_frame = ttk.LabelFrame(tab, text="テストパターン")
        pat_frame.pack(fill=tk.X, padx=8, pady=4)

        patterns = config.get("test", {}).get("patterns", ["auth", "pagination"])
        self._auth_var = tk.BooleanVar(value="auth" in patterns)
        ttk.Checkbutton(pat_frame, text="auth (認証あり 200 + 認証なし 401)",
                        variable=self._auth_var).pack(anchor=tk.W, padx=4, pady=2)

        self._pagination_var = tk.BooleanVar(value="pagination" in patterns)
        ttk.Checkbutton(pat_frame, text="pagination (offset/limit テスト)",
                        variable=self._pagination_var).pack(anchor=tk.W, padx=4, pady=2)

        pag_detail = ttk.Frame(pat_frame)
        pag_detail.pack(anchor=tk.W, padx=24, pady=2)
        pagination = config.get("test", {}).get("pagination", {"offset": 0, "limit": 5})
        ttk.Label(pag_detail, text="Offset:").pack(side=tk.LEFT)
        self._offset_var = tk.IntVar(value=pagination.get("offset", 0))
        ttk.Spinbox(pag_detail, textvariable=self._offset_var, from_=0, to=9999, width=5).pack(side=tk.LEFT, padx=(2, 12))
        ttk.Label(pag_detail, text="Limit:").pack(side=tk.LEFT)
        self._limit_var = tk.IntVar(value=pagination.get("limit", 5))
        ttk.Spinbox(pag_detail, textvariable=self._limit_var, from_=1, to=9999, width=5).pack(side=tk.LEFT, padx=2)

        # 通知設定
        notify_frame = ttk.LabelFrame(tab, text="通知設定")
        notify_frame.pack(fill=tk.X, padx=8, pady=4)

        ttk.Label(notify_frame, text="Slack Webhook URL:").grid(
            row=0, column=0, sticky=tk.W, padx=4, pady=2)
        slack_url = config.get("notification", {}).get("slack", {}).get("webhook_url", "")
        self._slack_url_var = tk.StringVar(value=slack_url)
        ttk.Entry(notify_frame, textvariable=self._slack_url_var, width=50).grid(
            row=0, column=1, sticky=tk.W, padx=4, pady=2)

        on_fail = config.get("notification", {}).get("slack", {}).get("on_failure_only", True)
        self._slack_fail_only_var = tk.BooleanVar(value=on_fail)
        ttk.Checkbutton(notify_frame, text="FAIL 時のみ通知",
                        variable=self._slack_fail_only_var).grid(
            row=1, column=1, sticky=tk.W, padx=4, pady=2)

        # 保存ボタン
        ttk.Button(tab, text="保存", command=self._save_settings).pack(anchor=tk.W, padx=8, pady=8)

    def _toggle_key(self):
        self._key_visible = not self._key_visible
        self._key_entry.configure(show="" if self._key_visible else "\u2022")

    def _save_settings(self):
        # config.yaml 更新
        config_path = self.project_root / "config.yaml"
        config = {}
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

        config.setdefault("api", {})["base_url"] = self._base_url_var.get()

        config.setdefault("test", {})["timeout"] = self._timeout_var.get()
        patterns = []
        if self._auth_var.get():
            patterns.append("auth")
        if self._pagination_var.get():
            patterns.append("pagination")
        config["test"]["patterns"] = patterns
        config["test"].setdefault("pagination", {})
        config["test"]["pagination"]["offset"] = self._offset_var.get()
        config["test"]["pagination"]["limit"] = self._limit_var.get()

        # 通知設定
        config.setdefault("notification", {}).setdefault("slack", {})
        config["notification"]["slack"]["webhook_url"] = self._slack_url_var.get()
        config["notification"]["slack"]["on_failure_only"] = self._slack_fail_only_var.get()

        with open(config_path, "w", encoding="utf-8", newline="\n") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        # .env 更新
        env_path = self.project_root / ".env"
        env_lines: list[str] = []
        if env_path.exists():
            with open(env_path, encoding="utf-8") as f:
                env_lines = f.readlines()

        new_env: dict[str, str] = {
            "BASE_URL": self._base_url_var.get(),
            "API_KEY": self._api_key_var.get(),
        }
        written_keys: set[str] = set()
        updated_lines: list[str] = []
        for line in env_lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key = stripped.split("=", 1)[0].strip()
                if key in new_env:
                    updated_lines.append(f"{key}={new_env[key]}\n")
                    written_keys.add(key)
                    continue
            updated_lines.append(line if line.endswith("\n") else line + "\n")

        for key, val in new_env.items():
            if key not in written_keys:
                updated_lines.append(f"{key}={val}\n")

        with open(env_path, "w", encoding="utf-8", newline="\n") as f:
            f.writelines(updated_lines)

        # バリデーション
        from .config_validator import validate_config
        validation_errors = validate_config(config)
        if validation_errors:
            has_error = any(not e.startswith("警告:") for e in validation_errors)
            msg = "設定にエラーがあります:\n" + "\n".join(f"- {e}" for e in validation_errors)
            if has_error:
                messagebox.showerror("バリデーションエラー", msg)
                return
            messagebox.showwarning("バリデーション警告", msg)

        messagebox.showinfo("保存完了", "config.yaml と .env を更新しました。")

    # ──────────────────────────────────────────────
    # Tab 4: 履歴
    # ──────────────────────────────────────────────
    def _build_history_tab(self):
        tab = self._tab_history

        paned = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # 左: 実行一覧
        left = ttk.LabelFrame(paned, text="過去の実行")
        self._hist_listbox = tk.Listbox(left, width=18, selectmode=tk.EXTENDED)
        self._hist_listbox.pack(fill=tk.BOTH, expand=True)
        self._hist_listbox.bind("<<ListboxSelect>>", lambda e: self._on_history_selected())
        paned.add(left, weight=1)

        # 右: レポート詳細
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=3)

        # サマリー行 + HTML ボタン
        summary_frame = ttk.Frame(right_frame)
        summary_frame.pack(fill=tk.X, padx=4, pady=(4, 2))
        self._hist_summary = ttk.Label(summary_frame, text="", font=("", 10, "bold"))
        self._hist_summary.pack(side=tk.LEFT)
        self._html_btn = ttk.Button(summary_frame, text="HTML レポートを開く",
                                    command=self._open_html_report)
        self._html_btn.pack(side=tk.RIGHT)

        # パターン別集計ラベル
        self._hist_pattern_label = ttk.Label(right_frame, text="", foreground="#555")
        self._hist_pattern_label.pack(fill=tk.X, padx=4, pady=(0, 2))

        hist_tree_frame = ttk.Frame(right_frame)
        hist_tree_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        cols = ("pattern", "result", "time")
        self._hist_tree = ttk.Treeview(hist_tree_frame, columns=("name",) + cols,
                                       show="headings", height=10)
        self._hist_tree.heading("name", text="テスト名")
        self._hist_tree.heading("pattern", text="パターン")
        self._hist_tree.heading("result", text="結果")
        self._hist_tree.heading("time", text="時間")
        self._hist_tree.column("name", width=200)
        self._hist_tree.column("pattern", width=80, anchor=tk.CENTER)
        self._hist_tree.column("result", width=60, anchor=tk.CENTER)
        self._hist_tree.column("time", width=80, anchor=tk.E)

        hist_scroll = ttk.Scrollbar(hist_tree_frame, orient=tk.VERTICAL, command=self._hist_tree.yview)
        self._hist_tree.configure(yscrollcommand=hist_scroll.set)
        self._hist_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        hist_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._hist_tree.tag_configure("pass", foreground="#228B22")
        self._hist_tree.tag_configure("fail", foreground="#DC143C")
        self._hist_tree.tag_configure("warn", foreground="#E67E22")

        # 比較ボタン + HTML + トレンド
        bottom = ttk.Frame(right_frame)
        bottom.pack(fill=tk.X, padx=4, pady=(0, 4))
        ttk.Button(bottom, text="比較...", command=self._compare_runs).pack(side=tk.LEFT)
        ttk.Button(bottom, text="トレンド表示", command=self._show_trend).pack(side=tk.LEFT, padx=4)
        ttk.Label(bottom, text="2つ選択して比較 / トレンドで推移確認").pack(side=tk.LEFT, padx=8)

        self._compare_text = tk.Text(right_frame, height=8, state=tk.DISABLED,
                                     wrap=tk.WORD, font=("Consolas", 9))
        self._compare_text.pack(fill=tk.X, padx=4, pady=(0, 4))

        self._refresh_history_list()

    def _refresh_history_list(self):
        self._hist_listbox.delete(0, tk.END)
        stamps = self._get_result_timestamps()
        for ts in stamps:
            # YYYYMMDDHHMMSS → 表示用フォーマット
            try:
                dt = datetime.strptime(ts, "%Y%m%d%H%M%S")
                label = dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                label = ts
            self._hist_listbox.insert(tk.END, label)
        # 内部用にタイムスタンプを保持
        self._hist_timestamps = stamps

    def _on_history_selected(self):
        sel = self._hist_listbox.curselection()
        if not sel:
            return
        # 単一選択時のみレポート表示
        if len(sel) == 1:
            ts = self._hist_timestamps[sel[0]]
            self._show_report(ts)

    def _show_report(self, timestamp: str):
        self._current_hist_ts = timestamp
        report_path = self.project_root / "results" / timestamp / "report.json"
        self._hist_tree.delete(*self._hist_tree.get_children())
        self._hist_pattern_label.configure(text="")

        if not report_path.exists():
            self._hist_summary.configure(text="report.json が見つかりません")
            return

        with open(report_path, encoding="utf-8") as f:
            report = json.load(f)

        summary = report.get("summary", {})
        total = summary.get("total", 0)
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        self._hist_summary.configure(text=f"Total: {total} / Passed: {passed} / Failed: {failed}")

        # パターン別集計表示
        by_pattern = summary.get("by_pattern", {})
        if by_pattern:
            parts = []
            for pat, counts in by_pattern.items():
                f = counts["total"] - counts["passed"]
                status = "OK" if f == 0 else f"{f}FAIL"
                parts.append(f"{pat}: {counts['passed']}/{counts['total']}({status})")
            self._hist_pattern_label.configure(text="  ".join(parts))

        for t in report.get("tests", []):
            warnings = t.get("schema_warnings", [])
            if not t.get("passed"):
                tag = "fail"
                label = "FAIL"
            elif warnings:
                tag = "warn"
                label = "WARN"
            else:
                tag = "pass"
                label = "PASS"
            elapsed = f"{t.get('elapsed_ms', 0):.0f}ms"
            pattern = t.get("pattern", "")
            self._hist_tree.insert("", tk.END,
                                   values=(t.get("name", ""), pattern, label, elapsed),
                                   tags=(tag,))

    def _compare_runs(self):
        sel = self._hist_listbox.curselection()
        if len(sel) != 2:
            messagebox.showwarning("比較", "比較するには2つの実行を選択してください。")
            return

        ts_a = self._hist_timestamps[sel[0]]
        ts_b = self._hist_timestamps[sel[1]]

        report_a = self._load_report(ts_a)
        report_b = self._load_report(ts_b)

        if report_a is None or report_b is None:
            messagebox.showerror("比較エラー", "report.json が見つかりません。")
            return

        # テスト結果を名前でマッピング
        results_a = {t["name"]: t for t in report_a.get("tests", [])}
        results_b = {t["name"]: t for t in report_b.get("tests", [])}

        lines: list[str] = []
        lines.append(f"=== 比較: {ts_a} vs {ts_b} ===\n")

        all_names = sorted(set(results_a.keys()) | set(results_b.keys()))
        diffs = 0
        for name in all_names:
            a = results_a.get(name)
            b = results_b.get(name)

            if a and b:
                if a["passed"] != b["passed"]:
                    status_a = "PASS" if a["passed"] else "FAIL"
                    status_b = "PASS" if b["passed"] else "FAIL"
                    lines.append(f"  {name}: {status_a} -> {status_b}")
                    diffs += 1
            elif a and not b:
                lines.append(f"  {name}: 削除 (was {'PASS' if a['passed'] else 'FAIL'})")
                diffs += 1
            elif b and not a:
                lines.append(f"  {name}: 追加 ({'PASS' if b['passed'] else 'FAIL'})")
                diffs += 1

        if diffs == 0:
            lines.append("  差分なし（全テスト同一結果）")

        # レスポンス差分検知
        from .diff import ResponseDiffer
        differ = ResponseDiffer(self.project_root / "results")
        prev_dir = self.project_root / "results" / ts_a
        curr_dir = self.project_root / "results" / ts_b
        schema_diffs = differ.compare_responses(prev_dir, curr_dir)

        if schema_diffs:
            lines.append("")
            lines.append(f"=== レスポンス差分: {len(schema_diffs)} file(s) ===")
            for d in schema_diffs:
                lines.append(f"  [{d.name}]")
                for c in d.changes:
                    lines.append(f"    {c.kind}: {c.path} ({c.detail})")
        else:
            lines.append("")
            lines.append("=== レスポンス差分なし ===")

        self._compare_text.configure(state=tk.NORMAL)
        self._compare_text.delete("1.0", tk.END)
        self._compare_text.insert("1.0", "\n".join(lines))
        self._compare_text.configure(state=tk.DISABLED)

    def _open_html_report(self):
        """選択中の実行の HTML レポートをブラウザで開く."""
        ts = getattr(self, "_current_hist_ts", None)
        if not ts:
            sel = self._hist_listbox.curselection()
            if sel:
                ts = self._hist_timestamps[sel[0]]
        if not ts:
            messagebox.showinfo("HTML レポート", "履歴を選択してください。")
            return

        html_path = self.project_root / "results" / ts / "report.html"
        if not html_path.exists():
            messagebox.showwarning("HTML レポート", f"report.html が見つかりません:\n{html_path}")
            return

        import webbrowser
        webbrowser.open(str(html_path))

    def _show_trend(self):
        """トレンド情報を比較テキスト欄に表示."""
        from .trend import TrendAnalyzer

        results_dir = self.project_root / "results"
        if not results_dir.exists():
            self._set_text(self._compare_text, "結果ディレクトリが見つかりません。")
            return

        analyzer = TrendAnalyzer(results_dir)
        runs = analyzer.load_runs(last_n=10)

        if not runs:
            self._set_text(self._compare_text, "テスト実行履歴がありません。")
            return

        lines: list[str] = []
        lines.append(f"=== Performance Trend ({len(runs)} runs) ===\n")

        # 実行履歴
        for run in runs:
            ts = run["timestamp"]
            s = run.get("summary", {})
            total = s.get("total", 0)
            passed_count = s.get("passed", 0)
            failed_count = s.get("failed", 0)
            display_ts = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]} {ts[8:10]}:{ts[10:12]}:{ts[12:]}"
            status = "ALL PASS" if failed_count == 0 else f"{failed_count} FAIL"
            lines.append(f"  {display_ts}  {passed_count}/{total} ({status})")

        lines.append("")

        # 劣化検知
        degradations = analyzer.detect_degradations(runs)
        if degradations:
            lines.append("  Degradations (>= 2x slower):")
            for d in degradations:
                lines.append(f"    {d.name}: {d.prev_ms:.0f}ms -> {d.curr_ms:.0f}ms ({d.ratio:.1f}x)")
            lines.append("")
        else:
            lines.append("  No performance degradations detected.\n")

        # 最新応答時間
        timeline = analyzer.get_timeline(runs)
        lines.append("  Latest response times:")
        pad = max((len(name) for name in timeline), default=0)
        for name in sorted(timeline.keys()):
            entries = timeline[name]
            latest = entries[-1]
            if len(entries) >= 2:
                prev = entries[-2]
                diff = latest.elapsed_ms - prev.elapsed_ms
                arrow = "+" if diff > 0 else ""
                lines.append(f"    {name:<{pad}}  {latest.elapsed_ms:>7.0f}ms  ({arrow}{diff:.0f}ms)")
            else:
                lines.append(f"    {name:<{pad}}  {latest.elapsed_ms:>7.0f}ms")

        self._set_text(self._compare_text, "\n".join(lines))

    def _load_report(self, timestamp: str) -> dict | None:
        path = self.project_root / "results" / timestamp / "report.json"
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)


def launch(project_root: Path) -> int:
    """GUI エントリポイント."""
    app = App(project_root)
    app.mainloop()
    return 0
