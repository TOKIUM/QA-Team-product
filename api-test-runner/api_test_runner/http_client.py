"""requests ベースの HTTP 実行（リトライ付き）."""

from __future__ import annotations

import time

import requests

from .models import TestCase, TestResult


class ApiClient:
    """API テスト用 HTTP クライアント."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 30,
        max_retries: int = 0,
        retry_delay: float = 1.0,
    ):
        self.session = requests.Session()
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def execute(self, test_case: TestCase) -> TestResult:
        """TestCase を実行して TestResult を返す（リトライ付き）."""
        result = self._execute_once(test_case)

        for attempt in range(self.max_retries):
            if not self._should_retry(result):
                break
            time.sleep(self.retry_delay * (2 ** attempt))
            result = self._execute_once(test_case)

        return result

    def _should_retry(self, result: TestResult) -> bool:
        """リトライすべきか判定（5xx / 接続エラーのみ）."""
        if result.passed:
            return False
        return result.status_code == 0 or result.status_code >= 500

    def _execute_once(self, test_case: TestCase) -> TestResult:
        """1回の HTTP リクエスト実行."""
        url = self.base_url + "/" + test_case.url_path
        headers = {"Accept": "application/json"}

        if test_case.use_auth:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # リクエストボディがある場合は Content-Type を追加
        json_body = None
        if test_case.request_body:
            headers["Content-Type"] = "application/json"
            json_body = test_case.request_body

        start = time.time()
        try:
            response = self.session.request(
                method=test_case.method,
                url=url,
                params=test_case.query_params or None,
                headers=headers,
                json=json_body,
                timeout=self.timeout,
            )
            elapsed = (time.time() - start) * 1000

            content_type = response.headers.get("content-type", "")
            body = None
            if "application/json" in content_type:
                try:
                    body = response.json()
                except ValueError:
                    pass

            passed = response.status_code == test_case.expected_status

            return TestResult(
                test_case=test_case,
                status_code=response.status_code,
                response_body=body,
                elapsed_ms=round(elapsed, 1),
                passed=passed,
                request_url=response.request.url,
                request_headers=dict(response.request.headers),
            )

        except requests.RequestException as e:
            elapsed = (time.time() - start) * 1000
            return TestResult(
                test_case=test_case,
                status_code=0,
                response_body={"error": str(e)},
                elapsed_ms=round(elapsed, 1),
                passed=False,
                request_url=url,
                request_headers=dict(headers),
            )

    def close(self):
        self.session.close()
