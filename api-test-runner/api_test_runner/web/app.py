"""FastAPI Web アプリケーション."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .run_manager import RunManager


def create_app(project_root: Path) -> FastAPI:
    """FastAPI アプリを生成."""
    app = FastAPI(title="API Test Runner")

    # パッケージルート (api_test_runner/) の親 = プロジェクトルート
    pkg_dir = Path(__file__).resolve().parent.parent  # api_test_runner/
    repo_root = pkg_dir.parent  # api-test-runner/

    templates_dir = repo_root / "templates"
    static_dir = repo_root / "static"

    templates = Jinja2Templates(directory=str(templates_dir))
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    manager = RunManager(project_root)

    # ─── ヘルパー ───────────────────────────────────

    def _load_config() -> dict:
        config_path = project_root / "config.yaml"
        if not config_path.exists():
            return {}
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _load_env() -> dict[str, str]:
        from ..__main__ import load_env
        return load_env(project_root / ".env")

    def _resolve_settings(config: dict, env: dict) -> tuple[str, str]:
        from ..__main__ import resolve_settings
        return resolve_settings(config, env)

    def _get_results_dir(config: dict) -> Path:
        name = config.get("output", {}).get("results_dir", "results")
        return project_root / name

    def _get_timestamps(config: dict) -> list[str]:
        results_dir = _get_results_dir(config)
        if not results_dir.exists():
            return []
        return sorted(
            [d.name for d in results_dir.iterdir() if d.is_dir() and d.name.isdigit()],
            reverse=True,
        )

    # ─── ページルート ──────────────────────────────

    @app.get("/", response_class=RedirectResponse)
    async def root():
        return RedirectResponse(url="/run")

    @app.get("/run", response_class=HTMLResponse)
    async def page_run(request: Request):
        return templates.TemplateResponse("run.html", {"request": request, "tab": "run"})

    @app.get("/response", response_class=HTMLResponse)
    async def page_response(request: Request):
        return templates.TemplateResponse("response.html", {"request": request, "tab": "response"})

    @app.get("/settings", response_class=HTMLResponse)
    async def page_settings(request: Request):
        return templates.TemplateResponse("settings.html", {"request": request, "tab": "settings"})

    @app.get("/history", response_class=HTMLResponse)
    async def page_history(request: Request):
        return templates.TemplateResponse("history.html", {"request": request, "tab": "history"})

    # ─── API: CSV ファイル ─────────────────────────

    @app.get("/api/csv-files")
    async def api_csv_files(csv_dir: str = "document"):
        d = project_root / csv_dir
        if not d.exists():
            return {"files": [], "error": f"ディレクトリが見つかりません: {csv_dir}"}
        files = sorted([f.name for f in d.glob("*.csv")])
        return {"files": files, "csv_dir": csv_dir}

    # ─── API: テスト実行 ──────────────────────────

    @app.post("/api/run")
    async def api_run(request: Request):
        body = await request.json()
        csv_dir = body.get("csv_dir", "document")
        patterns = body.get("patterns")  # list or None
        csv_files = body.get("csv_files")  # list of filenames or None

        config = _load_config()
        env = _load_env()
        base_url, api_key = _resolve_settings(config, env)

        if not base_url or not api_key:
            return {"error": "BASE_URL または API_KEY が未設定です。設定タブで入力してください。"}

        # バリデーション
        from ..config_validator import validate_config
        errors = validate_config(config)
        real_errors = [e for e in errors if not e.startswith("警告:")]
        if real_errors:
            return {"error": "設定エラー: " + "; ".join(real_errors)}

        result = manager.start(config, base_url, api_key, csv_dir, patterns, csv_files)
        return result

    @app.get("/api/run/status")
    async def api_run_status():
        return manager.get_state()

    # ─── API: タイムスタンプ ──────────────────────

    @app.get("/api/timestamps")
    async def api_timestamps():
        config = _load_config()
        return {"timestamps": _get_timestamps(config)}

    # ─── API: レスポンス閲覧 ─────────────────────

    @app.get("/api/response/{ts}")
    async def api_response_files(ts: str):
        config = _load_config()
        results_dir = _get_results_dir(config)
        run_dir = results_dir / ts
        if not run_dir.exists():
            return {"error": f"ディレクトリが見つかりません: {ts}"}
        files = sorted([
            f.name for f in run_dir.iterdir()
            if f.is_file() and f.suffix == ".json" and f.name != "report.json"
        ])
        return {"files": files, "timestamp": ts}

    @app.get("/api/response/{ts}/{filename}")
    async def api_response_file(ts: str, filename: str):
        config = _load_config()
        results_dir = _get_results_dir(config)
        filepath = results_dir / ts / filename
        if not filepath.exists():
            return {"error": f"ファイルが見つかりません: {filename}"}
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            return {"data": data, "filename": filename}
        except Exception as e:
            return {"error": str(e)}

    # ─── API: レポート ───────────────────────────

    @app.get("/api/report/{ts}")
    async def api_report(ts: str):
        config = _load_config()
        results_dir = _get_results_dir(config)
        report_path = results_dir / ts / "report.json"
        if not report_path.exists():
            return {"error": f"report.json が見つかりません: {ts}"}
        with open(report_path, encoding="utf-8") as f:
            data = json.load(f)
        data["timestamp"] = ts
        return data

    # ─── API: 設定 ───────────────────────────────

    @app.get("/api/settings")
    async def api_settings_get():
        config = _load_config()
        env = _load_env()
        base_url, api_key = _resolve_settings(config, env)
        test_config = config.get("test", {})
        return {
            "base_url": base_url,
            "api_key": api_key,
            "timeout": test_config.get("timeout", 30),
            "patterns": test_config.get("patterns", ["auth", "pagination"]),
            "pagination": test_config.get("pagination", {"offset": 0, "limit": 5}),
            "concurrency": test_config.get("concurrency", 3),
            "slack_webhook_url": config.get("notification", {}).get("slack", {}).get("webhook_url", ""),
            "slack_failure_only": config.get("notification", {}).get("slack", {}).get("on_failure_only", True),
        }

    @app.post("/api/settings")
    async def api_settings_save(request: Request):
        body = await request.json()

        # config.yaml 更新
        config_path = project_root / "config.yaml"
        config: dict = {}
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

        config.setdefault("api", {})["base_url"] = body.get("base_url", "")
        config.setdefault("test", {})["timeout"] = body.get("timeout", 30)
        config["test"]["patterns"] = body.get("patterns", ["auth", "pagination"])
        config["test"].setdefault("pagination", {})
        config["test"]["pagination"]["offset"] = body.get("pagination_offset", 0)
        config["test"]["pagination"]["limit"] = body.get("pagination_limit", 5)
        config["test"]["concurrency"] = body.get("concurrency", 3)

        config.setdefault("notification", {}).setdefault("slack", {})
        config["notification"]["slack"]["webhook_url"] = body.get("slack_webhook_url", "")
        config["notification"]["slack"]["on_failure_only"] = body.get("slack_failure_only", True)

        with open(config_path, "w", encoding="utf-8", newline="\n") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        # .env 更新
        env_path = project_root / ".env"
        env_lines: list[str] = []
        if env_path.exists():
            with open(env_path, encoding="utf-8") as f:
                env_lines = f.readlines()

        new_env = {
            "BASE_URL": body.get("base_url", ""),
            "API_KEY": body.get("api_key", ""),
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
        from ..config_validator import validate_config
        errors = validate_config(config)
        if errors:
            real_errors = [e for e in errors if not e.startswith("警告:")]
            warnings = [e for e in errors if e.startswith("警告:")]
            if real_errors:
                return {"status": "error", "errors": real_errors, "warnings": warnings}
            return {"status": "saved", "warnings": warnings}

        return {"status": "saved"}

    # ─── API: 比較 ───────────────────────────────

    @app.post("/api/compare")
    async def api_compare(request: Request):
        body = await request.json()
        ts1 = body.get("ts1", "")
        ts2 = body.get("ts2", "")

        config = _load_config()
        results_dir = _get_results_dir(config)

        if not ts1 or not ts2:
            return {"error": "2つのタイムスタンプを指定してください"}

        # レポート比較
        report1_path = results_dir / ts1 / "report.json"
        report2_path = results_dir / ts2 / "report.json"

        if not report1_path.exists() or not report2_path.exists():
            return {"error": "レポートが見つかりません"}

        with open(report1_path, encoding="utf-8") as f:
            report1 = json.load(f)
        with open(report2_path, encoding="utf-8") as f:
            report2 = json.load(f)

        # ステータス変化の検出
        tests1 = {t["name"]: t for t in report1.get("tests", [])}
        tests2 = {t["name"]: t for t in report2.get("tests", [])}

        status_changes = []
        all_names = sorted(set(tests1.keys()) | set(tests2.keys()))
        for name in all_names:
            t1 = tests1.get(name)
            t2 = tests2.get(name)
            if t1 and t2:
                if t1["passed"] != t2["passed"]:
                    status_changes.append({
                        "name": name,
                        "old_status": "PASS" if t1["passed"] else "FAIL",
                        "new_status": "PASS" if t2["passed"] else "FAIL",
                        "old_elapsed": t1.get("elapsed_ms", 0),
                        "new_elapsed": t2.get("elapsed_ms", 0),
                    })
            elif t1 and not t2:
                status_changes.append({
                    "name": name,
                    "old_status": "PASS" if t1["passed"] else "FAIL",
                    "new_status": "REMOVED",
                    "old_elapsed": t1.get("elapsed_ms", 0),
                    "new_elapsed": 0,
                })
            elif not t1 and t2:
                status_changes.append({
                    "name": name,
                    "old_status": "NEW",
                    "new_status": "PASS" if t2["passed"] else "FAIL",
                    "old_elapsed": 0,
                    "new_elapsed": t2.get("elapsed_ms", 0),
                })

        # スキーマ差分
        from ..diff import ResponseDiffer
        differ = ResponseDiffer(results_dir)
        prev_dir = results_dir / ts1
        curr_dir = results_dir / ts2
        schema_diffs = []
        try:
            diffs = differ.compare_responses(prev_dir, curr_dir)
            for d in diffs:
                schema_diffs.append({
                    "name": d.name,
                    "changes": [{"kind": c.kind, "path": c.path, "detail": c.detail}
                                for c in d.changes],
                })
        except Exception:
            pass

        return {
            "ts1": ts1,
            "ts2": ts2,
            "status_changes": status_changes,
            "schema_diffs": schema_diffs,
            "summary1": report1.get("summary", {}),
            "summary2": report2.get("summary", {}),
        }

    # ─── API: トレンド ───────────────────────────

    @app.get("/api/trend")
    async def api_trend(last: int = 10):
        config = _load_config()
        results_dir = _get_results_dir(config)

        if not results_dir.exists():
            return {"error": "results ディレクトリが見つかりません"}

        from ..trend import TrendAnalyzer
        analyzer = TrendAnalyzer(results_dir)
        runs = analyzer.load_runs(last_n=last)

        if not runs:
            return {"runs": [], "degradations": [], "timeline": {}}

        timeline = analyzer.get_timeline(runs)
        degradations = analyzer.detect_degradations(runs)

        timeline_data = {}
        for name, entries in timeline.items():
            timeline_data[name] = [
                {"timestamp": e.timestamp, "elapsed_ms": e.elapsed_ms, "passed": e.passed}
                for e in entries
            ]

        degradation_data = [
            {"name": d.name, "prev_ms": d.prev_ms, "curr_ms": d.curr_ms, "ratio": round(d.ratio, 2)}
            for d in degradations
        ]

        return {
            "runs": [{"timestamp": r["timestamp"], "summary": r.get("summary", {})}
                     for r in runs],
            "timeline": timeline_data,
            "degradations": degradation_data,
        }

    return app
