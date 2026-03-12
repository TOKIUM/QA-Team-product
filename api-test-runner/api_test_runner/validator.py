"""レスポンス検証."""

from __future__ import annotations

from .models import ApiSpec, Parameter, TestCase, TestResult


class ResponseValidator:
    """レスポンスのスキーマ・ボディを検証する."""

    def __init__(self, config: dict):
        self.config = config

    @staticmethod
    def validate_schema(result: TestResult) -> None:
        """レスポンスのスキーマを検証し、警告を result.schema_warnings に追加."""
        tc = result.test_case
        # 検証対象: PASS かつ API 仕様あり かつ 200 期待
        if not result.passed or tc.api is None or tc.expected_status != 200:
            return
        body = result.response_body
        resource = tc.api.resource
        if not resource:
            return

        if body is None:
            result.schema_warnings.append(
                "スキーマ検証: レスポンスボディが空です。"
                "APIが正常にデータを返していない可能性があります")
            return
        if not isinstance(body, dict):
            result.schema_warnings.append(
                f"スキーマ検証: レスポンスがJSON Object(dict)ではなく "
                f"{type(body).__name__} です。API仕様と実装が異なる可能性があります")
            return
        if resource not in body:
            actual_keys = list(body.keys())
            # POST系バッチジョブ（job_id返却）の場合は専用メッセージ
            if "job_id" in actual_keys and tc.pattern in ("post_normal", "put_normal", "patch_normal", "delete_normal"):
                result.schema_warnings.append(
                    f"スキーマ検証: バッチジョブ登録APIのため、レスポンスは "
                    f"'{resource}' 配列ではなく job_id を返却しています。"
                    f"これはバッチジョブAPIの正常な動作です（実際のキー: {actual_keys}）")
            else:
                result.schema_warnings.append(
                    f"スキーマ検証: レスポンスに期待キー '{resource}' がありません。"
                    f"実際のキー: {actual_keys}。"
                    f"APIのレスポンス構造がCSV仕様と異なる可能性があります")
            return
        if not isinstance(body[resource], list):
            result.schema_warnings.append(
                f"スキーマ検証: '{resource}' が配列(list)ではなく "
                f"{type(body[resource]).__name__} です。"
                f"一覧APIは配列を返す仕様ですが、単一オブジェクトが返されています"
            )

    @staticmethod
    def validate_error_body(result: TestResult) -> None:
        """エラーレスポンス（400/401）のボディ構造を検証し、警告を追加."""
        if not result.passed:
            return
        tc = result.test_case
        body = result.response_body

        if tc.expected_status == 401:
            if body is None or body == {}:
                result.schema_warnings.append(
                    "エラー検証: 認証エラー(401)のレスポンスボディが空です。"
                    "エラーメッセージを返すのが望ましい実装です")
            return

        if tc.expected_status == 400:
            if body is None:
                result.schema_warnings.append(
                    "エラー検証: バリデーションエラー(400)のレスポンスボディが空です。"
                    "エラー内容をクライアントに伝えるためボディが必要です")
                return
            if not isinstance(body, dict):
                result.schema_warnings.append(
                    f"エラー検証: 400レスポンスがJSON Object(dict)ではなく "
                    f"{type(body).__name__} です。エラー詳細の解析ができません")
                return
            if "message" not in body:
                result.schema_warnings.append(
                    f"エラー検証: 400レスポンスに 'message' キーがありません。"
                    f"実際のキー: {list(body.keys())}。"
                    f"エラー原因の特定にmessageフィールドが推奨されます")
            if tc.pattern == "missing_required":
                has_detail = any(
                    k in body for k in ("param", "missing_values", "errors")
                )
                if not has_detail:
                    result.schema_warnings.append(
                        f"エラー検証: 必須パラメータ欠損(400)のレスポンスに "
                        f"詳細情報('param', 'missing_values', 'errors')がありません。"
                        f"実際のキー: {list(body.keys())}。"
                        f"どのパラメータが不足しているか特定できません")

    def validate_response_body(self, result: TestResult) -> None:
        """レスポンスボディの内容を検証し、警告を result.schema_warnings に追加.

        - 空ボディ検知: 200 で body が null/空/{} → WARN
        - pagination 件数チェック: limit=N なら結果が N件以下か
        - レスポンス要素キー一貫性: リソース配列の各要素で同じキーが存在するか
        """
        rv_config = self.config.get("test", {}).get("response_validation", {})
        if not rv_config.get("enabled", False):
            return

        tc = result.test_case
        # PASS + api あり + 200 期待のみ対象
        if not result.passed or tc.api is None or tc.expected_status != 200:
            return

        body = result.response_body
        resource = tc.api.resource if tc.api else None

        # 空ボディ検知
        if body is None or body == {} or body == []:
            result.schema_warnings.append(
                "レスポンス検証: 200 OKなのにボディが空です。"
                "データが0件の可能性、またはAPIの異常が考えられます")
            return

        if not isinstance(body, dict) or not resource:
            return

        items = body.get(resource)
        if not isinstance(items, list):
            return

        # pagination 件数チェック
        if rv_config.get("pagination_count_check", True):
            limit = tc.query_params.get("limit")
            if limit is not None and isinstance(limit, int) and limit > 0:
                if len(items) > limit:
                    result.schema_warnings.append(
                        f"レスポンス検証: limit={limit}を指定したのに"
                        f"{len(items)}件返却されています。"
                        f"ページネーションが正しく動作していない可能性があります")

        # キー一貫性チェック
        if rv_config.get("required_fields_check", True) and len(items) >= 2:
            all_keys = set()
            for item in items:
                if isinstance(item, dict):
                    all_keys |= set(item.keys())
            for i, item in enumerate(items):
                if isinstance(item, dict):
                    missing = all_keys - set(item.keys())
                    if missing:
                        result.schema_warnings.append(
                            f"レスポンス検証: {resource}の{i+1}件目に "
                            f"他の要素にあるキーが欠損しています: {sorted(missing)}。"
                            f"レスポンス構造が要素間で不一致です")
                        break  # 1件目の不一致で終了

    # デフォルトの除外パラメータ（クエリパラメータでありレスポンスフィールドではない）
    _DEFAULT_SKIP_PARAMS = frozenset(("offset", "limit", "fields"))

    def validate_json_schema(self, result: TestResult) -> None:
        """APISpec のパラメータ定義からレスポンスフィールドの型を検証する.

        GET 200 レスポンスのリソース配列要素を対象に、params で定義された
        フィールド名・型との照合を行う。
        """
        rv_config = self.config.get("test", {}).get("response_validation", {})
        if not rv_config.get("json_schema_check", False):
            return

        tc = result.test_case
        if not result.passed or tc.api is None or tc.expected_status != 200:
            return
        if tc.method != "GET":
            return

        body = result.response_body
        resource = tc.api.resource
        if not resource or not isinstance(body, dict):
            return

        items = body.get(resource)
        if not isinstance(items, list) or not items:
            return

        # 除外パラメータ: 設定で追加可能
        skip_params = self._DEFAULT_SKIP_PARAMS | set(
            rv_config.get("json_schema_skip_params", []))

        # params からフィールド名→期待型のマッピングを構築
        expected_fields = self._build_field_type_map(tc.api.params, skip_params)
        if not expected_fields:
            return

        # 最初の要素のみ検証（全要素チェックは重すぎる）
        item = items[0]
        if not isinstance(item, dict):
            return

        for field_name, expected_type in expected_fields.items():
            if field_name in item:
                actual_value = item[field_name]
                type_error = self._check_type(actual_value, expected_type)
                if type_error:
                    result.schema_warnings.append(
                        f"型検証: {resource}[0].{field_name} の型が "
                        f"CSV仕様と不一致です（仕様: {expected_type}, 実際: {type_error}）。"
                        f"CSV仕様の型定義かAPI実装を確認してください")
            else:
                result.schema_warnings.append(
                    f"型検証: {resource}の1件目に '{field_name}' フィールドがありません。"
                    f"CSV仕様では定義されていますが、レスポンスに含まれていません")

    @staticmethod
    def _build_field_type_map(
        params: list[Parameter],
        skip_params: set[str] | frozenset[str] | None = None,
    ) -> dict[str, str]:
        """パラメータリストからフィールド名→データ型のマッピングを構築する."""
        if skip_params is None:
            skip_params = ResponseValidator._DEFAULT_SKIP_PARAMS
        field_map: dict[str, str] = {}
        for p in params:
            if p.param_name in skip_params:
                continue
            field_map[p.param_name] = p.data_type
        return field_map

    @staticmethod
    def _check_type(value, expected_type: str) -> str | None:
        """値が期待型に合致するか検証する。不一致ならエラー説明文字列を返す."""
        if value is None:
            return None  # null は許容

        if "整数" in expected_type:
            if not isinstance(value, int) or isinstance(value, bool):
                return type(value).__name__
        elif "文字列" in expected_type:
            if not isinstance(value, str):
                return type(value).__name__
        elif "真偽" in expected_type:
            if not isinstance(value, bool):
                return type(value).__name__
        elif "配列" in expected_type:
            if not isinstance(value, list):
                return type(value).__name__
        elif "オブジェクト" in expected_type:
            if not isinstance(value, dict):
                return type(value).__name__
        return None

    @staticmethod
    def test_description(tc: TestCase) -> str:
        """テストの表示名を生成."""
        if tc.pattern == "auth":
            return f"{tc.method} /{tc.url_path} - 200 OK with valid token"
        elif tc.pattern == "no_auth":
            return f"{tc.method} /{tc.url_path} - 401 without token"
        elif tc.pattern == "pagination":
            return f"GET /{tc.url_path} with pagination (offset={tc.query_params.get('offset', 0)}, limit={tc.query_params.get('limit', 5)})"
        elif tc.pattern == "search":
            params_str = "&".join(f"{k}={v}" for k, v in tc.query_params.items())
            return f"GET /{tc.url_path} with search ({params_str})"
        elif tc.pattern == "boundary":
            params_str = "&".join(f"{k}={v}" for k, v in tc.query_params.items())
            return f"GET /{tc.url_path} boundary ({params_str}) - expect {tc.expected_status}"
        elif tc.pattern == "missing_required":
            suffix = ""
            if tc.request_body is not None:
                suffix = " with body"
            return f"{tc.method} /{tc.url_path} missing required{suffix} - expect {tc.expected_status}"
        elif tc.pattern == "post_normal":
            return f"POST /{tc.url_path} normal - expect {tc.expected_status}"
        elif tc.pattern == "put_normal":
            return f"PUT /{tc.url_path} normal - expect {tc.expected_status}"
        elif tc.pattern == "delete_normal":
            return f"DELETE /{tc.url_path} normal - expect {tc.expected_status}"
        elif tc.pattern == "patch_normal":
            return f"PATCH /{tc.url_path} normal - expect {tc.expected_status}"
        elif tc.pattern == "crud_chain":
            return f"CRUD chain /{tc.url_path} (POST→GET→DELETE→GET)"
        elif tc.pattern == "invalid_body":
            return f"{tc.method} /{tc.url_path} invalid body - expect {tc.expected_status}"
        elif tc.pattern == "custom":
            extras = []
            if tc.query_params:
                extras.append(f"params={tc.query_params}")
            if tc.request_body:
                extras.append("with body")
            suffix = f" ({', '.join(extras)})" if extras else ""
            return f"{tc.method} /{tc.url_path} - {tc.expected_status}{suffix}"
        return f"{tc.method} /{tc.url_path}"

    @staticmethod
    def print_result(result: TestResult) -> None:
        """テスト結果を1行表示."""
        tc = result.test_case
        desc = ResponseValidator.test_description(tc)
        status_label = "PASS" if result.passed else "FAIL"
        if result.passed:
            warn = f" [WARN: {'; '.join(result.schema_warnings)}]" if result.schema_warnings else ""
            print(f"  [{status_label}] {desc}{warn}")
        else:
            print(f"  [{status_label}] {desc} - Expected {tc.expected_status}, got {result.status_code}")
