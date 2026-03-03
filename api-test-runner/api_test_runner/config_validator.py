"""config.yaml のバリデーション."""

from __future__ import annotations

VALID_METHODS = {"GET", "POST", "PUT", "DELETE"}
VALID_PATTERNS = {"auth", "pagination", "search"}
KNOWN_TOP_KEYS = {"api", "test", "output", "custom_tests", "notification"}


def validate_config(config: dict) -> list[str]:
    """config.yaml をバリデーションし、エラーメッセージのリストを返す."""
    errors: list[str] = []

    if not isinstance(config, dict):
        return ["config.yaml のルートが辞書型ではありません"]

    # 未知のトップレベルキー警告
    for key in config:
        if key not in KNOWN_TOP_KEYS:
            errors.append(f"警告: 未知のトップレベルキー '{key}'")

    # api セクション
    api = config.get("api", {})
    if isinstance(api, dict):
        base_url = api.get("base_url", "")
        if base_url and isinstance(base_url, str):
            if not base_url.startswith(("http://", "https://")):
                errors.append("api.base_url は http:// または https:// で始まる必要があります")
        elif base_url and not isinstance(base_url, str):
            errors.append("api.base_url は文字列で指定してください")

    # test セクション
    test = config.get("test", {})
    if isinstance(test, dict):
        # timeout
        timeout = test.get("timeout")
        if timeout is not None:
            if not isinstance(timeout, int) or isinstance(timeout, bool):
                errors.append("test.timeout は整数で指定してください")
            elif not (1 <= timeout <= 300):
                errors.append("test.timeout は 1〜300 の範囲で指定してください")

        # concurrency
        concurrency = test.get("concurrency")
        if concurrency is not None:
            if not isinstance(concurrency, int) or isinstance(concurrency, bool):
                errors.append("test.concurrency は整数で指定してください")
            elif not (1 <= concurrency <= 20):
                errors.append("test.concurrency は 1〜20 の範囲で指定してください")

        # methods
        methods = test.get("methods")
        if methods is not None:
            if not isinstance(methods, list):
                errors.append("test.methods はリストで指定してください")
            else:
                for m in methods:
                    if m not in VALID_METHODS:
                        errors.append(
                            f"test.methods に無効な値 '{m}' があります "
                            f"(有効: {', '.join(sorted(VALID_METHODS))})")

        # patterns
        patterns = test.get("patterns")
        if patterns is not None:
            if not isinstance(patterns, list):
                errors.append("test.patterns はリストで指定してください")
            else:
                for p in patterns:
                    if p not in VALID_PATTERNS:
                        errors.append(
                            f"test.patterns に無効な値 '{p}' があります "
                            f"(有効: {', '.join(sorted(VALID_PATTERNS))})")

        # pagination
        pagination = test.get("pagination")
        if pagination is not None and isinstance(pagination, dict):
            offset = pagination.get("offset")
            if offset is not None:
                if not isinstance(offset, int) or isinstance(offset, bool):
                    errors.append("test.pagination.offset は整数で指定してください")
                elif offset < 0:
                    errors.append("test.pagination.offset は 0 以上で指定してください")

            limit = pagination.get("limit")
            if limit is not None:
                if not isinstance(limit, int) or isinstance(limit, bool):
                    errors.append("test.pagination.limit は整数で指定してください")
                elif limit < 1:
                    errors.append("test.pagination.limit は 1 以上で指定してください")

        # retry
        retry = test.get("retry")
        if retry is not None and isinstance(retry, dict):
            max_retries = retry.get("max_retries")
            if max_retries is not None:
                if not isinstance(max_retries, int) or isinstance(max_retries, bool):
                    errors.append("test.retry.max_retries は整数で指定してください")
                elif not (0 <= max_retries <= 10):
                    errors.append("test.retry.max_retries は 0〜10 の範囲で指定してください")

            delay = retry.get("delay")
            if delay is not None:
                if not isinstance(delay, (int, float)) or isinstance(delay, bool):
                    errors.append("test.retry.delay は数値で指定してください")
                elif not (0.1 <= delay <= 60):
                    errors.append("test.retry.delay は 0.1〜60 の範囲で指定してください")

    # output セクション
    output = config.get("output", {})
    if isinstance(output, dict):
        results_dir = output.get("results_dir")
        if results_dir is not None and not isinstance(results_dir, str):
            errors.append("output.results_dir は文字列で指定してください")

    # custom_tests セクション
    custom_tests = config.get("custom_tests")
    if custom_tests is not None:
        if not isinstance(custom_tests, list):
            errors.append("custom_tests はリストで指定してください")
        else:
            required_keys = {"name", "url_path", "method", "expected_status"}
            for i, ct in enumerate(custom_tests):
                if not isinstance(ct, dict):
                    errors.append(f"custom_tests[{i}] は辞書型で指定してください")
                    continue
                missing = required_keys - set(ct.keys())
                if missing:
                    errors.append(
                        f"custom_tests[{i}] ({ct.get('name', '?')}) に "
                        f"必須キーがありません: {', '.join(sorted(missing))}")

    return errors
