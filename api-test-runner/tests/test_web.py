"""Tests for Web UI (app.py + run_manager.py)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from api_test_runner.models import TestCase, TestResult
from api_test_runner.web.run_manager import RunManager, RunState


# ── RunState ─────────────────────────────────────────────

class TestRunState:
    def test_defaults(self):
        state = RunState()
        assert state.status == "idle"
        assert state.total == 0
        assert state.results == []

    def test_custom_values(self):
        state = RunState(status="running", total=10, passed=5)
        assert state.status == "running"
        assert state.total == 10
        assert state.passed == 5


# ── RunManager ───────────────────────────────────────────

class TestRunManager:
    def test_initial_state(self, tmp_path):
        mgr = RunManager(tmp_path)
        state = mgr.get_state()
        assert state["status"] == "idle"
        assert state["total"] == 0
        assert state["completed"] == 0

    def test_start_returns_error_when_already_running(self, tmp_path):
        mgr = RunManager(tmp_path)
        mgr._state.status = "running"
        result = mgr.start({}, "http://x", "key", "doc")
        assert "error" in result
        assert "実行中" in result["error"]

    def test_start_returns_started(self, tmp_path):
        """start() がスレッドを起動して 'started' を返す."""
        (tmp_path / "document").mkdir()
        mgr = RunManager(tmp_path)
        with patch.object(mgr, "_run_thread"):
            result = mgr.start({}, "http://x", "key", "document")
        assert result["status"] == "started"

    def test_set_error(self, tmp_path):
        mgr = RunManager(tmp_path)
        mgr._set_error("something went wrong")
        state = mgr.get_state()
        assert state["status"] == "error"
        assert state["error"] == "something went wrong"

    def test_run_thread_missing_csv_dir(self, tmp_path):
        """CSV ディレクトリが存在しない場合はエラー."""
        mgr = RunManager(tmp_path)
        mgr._run_thread({}, "http://x", "key", "nonexistent", None, None)
        state = mgr.get_state()
        assert state["status"] == "error"
        assert "見つかりません" in state["error"]

    def test_run_thread_no_specs(self, tmp_path):
        """CSV があるがパースで何も返らない場合."""
        csv_dir = tmp_path / "document"
        csv_dir.mkdir()
        (csv_dir / "empty.csv").write_text("", encoding="utf-8")
        mgr = RunManager(tmp_path)
        mgr._run_thread({}, "http://x", "key", "document", None, None)
        state = mgr.get_state()
        assert state["status"] == "error"


# ── FastAPI app エンドポイント ────────────────────────────

@pytest.fixture
def web_project(tmp_path):
    """テスト用プロジェクト構造を作成."""
    # templates / static ディレクトリ
    pkg_dir = Path(__file__).resolve().parent.parent
    templates_dir = pkg_dir / "templates"
    static_dir = pkg_dir / "static"

    # config.yaml
    config = {
        "api": {"base_url": "https://example.com/api/v2"},
        "test": {"patterns": ["auth"], "timeout": 30},
        "output": {"results_dir": "results"},
        "notification": {"slack": {"webhook_url": "", "on_failure_only": True}},
    }
    (tmp_path / "config.yaml").write_text(
        __import__("yaml").dump(config), encoding="utf-8")

    # .env
    (tmp_path / ".env").write_text(
        "BASE_URL=https://example.com/api/v2\nAPI_KEY=testkey123\n",
        encoding="utf-8")

    # results ディレクトリ
    results_dir = tmp_path / "results"
    ts_dir = results_dir / "20260310120000"
    ts_dir.mkdir(parents=True)

    report = {
        "summary": {"total": 2, "passed": 2, "failed": 0},
        "tests": [
            {"name": "test-a", "passed": True, "elapsed_ms": 100},
            {"name": "test-b", "passed": True, "elapsed_ms": 200},
        ],
    }
    (ts_dir / "report.json").write_text(
        json.dumps(report), encoding="utf-8")
    (ts_dir / "test-a.json").write_text(
        json.dumps({"data": []}), encoding="utf-8")

    (results_dir / "latest.txt").write_text("20260310120000", encoding="utf-8")

    # document ディレクトリ
    (tmp_path / "document").mkdir()

    return tmp_path


@pytest.fixture
def client(web_project):
    """FastAPI TestClient."""
    from fastapi.testclient import TestClient
    from api_test_runner.web.app import create_app
    app = create_app(web_project)
    return TestClient(app)


class TestAppEndpoints:
    def test_root_redirects_to_run(self, client):
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 307
        assert "/run" in resp.headers["location"]

    def test_page_run(self, client):
        resp = client.get("/run")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_page_response(self, client):
        resp = client.get("/response")
        assert resp.status_code == 200

    def test_page_settings(self, client):
        resp = client.get("/settings")
        assert resp.status_code == 200

    def test_page_history(self, client):
        resp = client.get("/history")
        assert resp.status_code == 200

    def test_api_csv_files_empty(self, client):
        resp = client.get("/api/csv-files")
        data = resp.json()
        assert "files" in data
        assert data["files"] == []

    def test_api_csv_files_missing_dir(self, client):
        resp = client.get("/api/csv-files?csv_dir=nonexistent")
        data = resp.json()
        assert "error" in data

    def test_api_timestamps(self, client):
        resp = client.get("/api/timestamps")
        data = resp.json()
        assert "20260310120000" in data["timestamps"]

    def test_api_response_files(self, client):
        resp = client.get("/api/response/20260310120000")
        data = resp.json()
        assert "test-a.json" in data["files"]
        assert "report.json" not in data["files"]  # report.json は除外

    def test_api_response_file_content(self, client):
        resp = client.get("/api/response/20260310120000/test-a.json")
        data = resp.json()
        assert data["data"] == {"data": []}

    def test_api_response_missing_ts(self, client):
        resp = client.get("/api/response/99999999999999")
        assert "error" in resp.json()

    def test_api_response_missing_file(self, client):
        resp = client.get("/api/response/20260310120000/missing.json")
        assert "error" in resp.json()

    def test_api_report(self, client):
        resp = client.get("/api/report/20260310120000")
        data = resp.json()
        assert data["summary"]["total"] == 2
        assert data["timestamp"] == "20260310120000"

    def test_api_report_missing(self, client):
        resp = client.get("/api/report/99999999999999")
        assert "error" in resp.json()

    def test_api_settings_get(self, client):
        resp = client.get("/api/settings")
        data = resp.json()
        assert data["base_url"] == "https://example.com/api/v2"
        assert data["api_key"] == "testkey123"
        assert "auth" in data["patterns"]

    def test_api_settings_save(self, client, web_project):
        resp = client.post("/api/settings", json={
            "base_url": "https://new.example.com",
            "api_key": "newkey",
            "timeout": 60,
            "patterns": ["auth", "search"],
            "pagination_offset": 0,
            "pagination_limit": 10,
            "concurrency": 5,
            "slack_webhook_url": "",
            "slack_failure_only": True,
        })
        data = resp.json()
        assert data["status"] == "saved"

        # 設定が書き込まれたことを確認
        import yaml
        with open(web_project / "config.yaml", encoding="utf-8") as f:
            saved = yaml.safe_load(f)
        assert saved["test"]["concurrency"] == 5

    def test_api_run_status_idle(self, client):
        resp = client.get("/api/run/status")
        data = resp.json()
        assert data["status"] == "idle"

    def test_api_compare_missing_timestamps(self, client):
        resp = client.post("/api/compare", json={"ts1": "", "ts2": ""})
        assert "error" in resp.json()

    def test_api_trend(self, client):
        resp = client.get("/api/trend?last=5")
        data = resp.json()
        assert "runs" in data
