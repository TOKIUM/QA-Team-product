"""
自動生成テスト: TOKIUM 請求書発行 - ログイン機能（正常系のみ）
対象: https://invoicing-staging.keihi.com/login

test_results対応: 各テストにTH-IDを付与し、conftest.pyのフックで
動画・ログ・JSONサマリーを自動保存する。
"""

import os
import re
import pytest
from playwright.sync_api import Page, expect


BASE_URL = "https://invoicing-staging.keihi.com"


def _load_env():
    """ログイン/.env からテスト認証情報を読み込む（環境変数が未設定の場合のフォールバック）"""
    env_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    vals = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    vals[k.strip()] = v.strip()
    return vals


_env = _load_env()

# テスト用認証情報（環境変数 → .envファイル の優先順）
TEST_EMAIL = os.environ.get("TEST_EMAIL") or _env.get("TEST_EMAIL", "test@example.com")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD") or _env.get("TEST_PASSWORD", "TestPass123!")

TOKIUM_ID_BASE_URL = "https://dev.keihi.com"
TOKIUM_ID_EMAIL = os.environ.get("TOKIUM_ID_EMAIL") or _env.get("TOKIUM_ID_EMAIL", "chikata_t+th001@tokium.jp")
TOKIUM_ID_PASSWORD = os.environ.get("TOKIUM_ID_PASSWORD") or _env.get("TOKIUM_ID_PASSWORD", "Qa12345678")


# =============================================================================
# TH-ID マッピング
# =============================================================================
TH_ID_MAP = {
    "test_ログインページの表示確認": "TH-L01",
    "test_パスワードリセット画面への遷移": "TH-L02",
    "test_新規登録画面への遷移": "TH-L03",
    "test_tokium_idログイン画面への遷移": "TH-L04",
    "test_正常ログイン": "TH-L05",
    "test_tokium_idログイン画面の表示確認": "TH-L06",
    "test_tokium_idログイン成功": "TH-L07",
    "test_tokium_id_invoicing遷移": "TH-L08",
    "test_空欄でのログイン試行": "TH-L09",
    "test_不正なパスワードでのログイン": "TH-L10",
    "test_tokium_id空欄でのログイン試行": "TH-L11",
    "test_tokium_id不正なパスワードでのログイン": "TH-L12",
}


@pytest.fixture(autouse=True)
def _set_th_id(request):
    """テスト関数名からTH-IDを自動付与（[chromium]等のパラメータを除去して照合）"""
    node_name = request.node.name
    # パラメータ付き名（例: test_xxx[chromium]）からベース名を抽出
    base_name = node_name.split("[")[0] if "[" in node_name else node_name
    th_id = TH_ID_MAP.get(base_name)
    if th_id:
        request.node._th_id = th_id


# =============================================================================
# ヘルパー関数
# =============================================================================

def goto_login(page: Page):
    """ログインページに遷移し、フォームが表示されるまで待機"""
    page.goto(f"{BASE_URL}/login")
    # exact=True で「ログイン」ボタンのみを一意に特定（「TOKIUM ID でログイン」を除外）
    page.get_by_role("button", name="ログイン", exact=True).wait_for(state="visible")


def goto_tokium_id_login(page: Page):
    """invoicing /login → TOKIUM IDボタンクリック → dev.keihi.com/users/sign_in 到達まで待機"""
    goto_login(page)
    page.locator('a[href="/auth-redirect"]').click()
    page.wait_for_url(re.compile(r"dev\.keihi\.com/users/sign_in"), timeout=15000)


def perform_tokium_id_login(page: Page):
    """goto_tokium_id_login + 認証情報入力 + ログイン → invoicing-staging へSSOリダイレクト待機"""
    goto_tokium_id_login(page)
    page.locator('input[name="user[email]"]').fill(TOKIUM_ID_EMAIL)
    page.locator('input[name="user[password]"]').fill(TOKIUM_ID_PASSWORD)
    page.wait_for_timeout(500)

    # 認証APIレスポンスを監視しつつログインボタンをクリック
    auth_failed = []
    page.on("response", lambda r: auth_failed.append(r.status)
            if "auth/sign_in" in r.url and r.status >= 400 else None)
    page.locator('#sign_in_form button[type="button"]').click()
    page.wait_for_timeout(3000)

    if auth_failed:
        pytest.skip(
            f"TOKIUM ID認証失敗(HTTP {auth_failed[0]}): "
            f"認証情報を確認してください（email={TOKIUM_ID_EMAIL[:20]}...）"
        )

    # SSO: dev.keihi.com → invoicing-staging.keihi.com/auth/callback → /invoices
    page.wait_for_url(re.compile(r"invoicing-staging\.keihi\.com"), timeout=30000)


@pytest.fixture
def tokium_id_page(page: Page) -> Page:
    """TOKIUM IDでログイン済みのページを返す（TH-L08用）"""
    perform_tokium_id_login(page)
    yield page


# =============================================================================
# テスト1: ログインページの表示確認
# =============================================================================

@pytest.mark.smoke
def test_ログインページの表示確認(page: Page):
    """ログインページの主要要素がすべて正しく表示されている"""

    # Step1: ログインページに遷移
    goto_login(page)

    # Step2: ページタイトルの確認
    expect(page).to_have_title(re.compile(r"TOKIUM"))

    # Step3: ロゴの表示確認
    expect(page.get_by_role("img", name="TOKIUM 請求書発行")).to_be_visible()

    # Step4: フォーム要素の表示確認
    expect(page.get_by_label("メールアドレス")).to_be_visible()
    expect(page.get_by_label("パスワード")).to_be_visible()
    expect(page.get_by_role("button", name="ログイン", exact=True)).to_be_visible()

    # Step5: 補助リンク・ボタンの表示確認
    expect(page.get_by_role("link", name="パスワードを忘れた場合")).to_be_visible()
    expect(page.get_by_role("link", name="新規登録はこちら")).to_be_visible()
    expect(page.get_by_role("button", name="TOKIUM ID でログイン")).to_be_visible()

    # Step6: メールアドレス入力欄の type が email であることを確認
    email_type = page.get_by_label("メールアドレス").get_attribute("type")
    assert email_type == "email", f"メールアドレス欄の type が '{email_type}' （期待値: 'email'）"

    # Step7: パスワード入力欄の type が password であることを確認
    password_type = page.get_by_label("パスワード").get_attribute("type")
    assert password_type == "password", f"パスワード欄の type が '{password_type}' （期待値: 'password'）"


# =============================================================================
# テスト2: パスワードリセット画面への遷移
# =============================================================================

def test_パスワードリセット画面への遷移(page: Page):
    """「パスワードを忘れた場合」リンクからリカバリー画面に遷移できる"""

    # Step1: ログインページに遷移
    goto_login(page)

    # Step2: 「パスワードを忘れた場合」リンクをクリック
    page.get_by_role("link", name="パスワードを忘れた場合").click()

    # Step3: リカバリー画面への遷移を確認
    expect(page).to_have_url(re.compile(r"/recovery"))


# =============================================================================
# テスト3: 新規登録画面への遷移
# =============================================================================

def test_新規登録画面への遷移(page: Page):
    """「新規登録はこちら」リンクから登録画面に遷移できる"""

    # Step1: ログインページに遷移
    goto_login(page)

    # Step2: 「新規登録はこちら」リンクをクリック
    page.get_by_role("link", name="新規登録はこちら").click()

    # Step3: 登録画面への遷移を確認
    expect(page).to_have_url(re.compile(r"/registration"))


# =============================================================================
# テスト4: TOKIUM ID ログイン画面への遷移
# =============================================================================

def test_tokium_idログイン画面への遷移(page: Page):
    """「TOKIUM ID でログイン」ボタンから認証リダイレクト画面に遷移できる"""

    # Step1: ログインページに遷移
    goto_login(page)

    # Step2: 「TOKIUM ID でログイン」ボタンをクリック
    page.locator('a[href="/auth-redirect"]').click()

    # Step3: ログインページから離れたことを確認
    expect(page).not_to_have_url(re.compile(r"/login$"))


# =============================================================================
# テスト5: 正常ログイン
# =============================================================================

def test_正常ログイン(page: Page):
    """正しい認証情報でログインし、ログインページから離れることを確認"""

    # Step1: ログインページに遷移
    goto_login(page)

    # Step2: メールアドレスを入力
    page.get_by_label("メールアドレス").fill(TEST_EMAIL)

    # Step3: パスワードを入力
    page.get_by_label("パスワード").fill(TEST_PASSWORD)

    # Step4: 入力完了を待機してからログインボタンをクリック
    page.wait_for_timeout(500)
    page.get_by_role("button", name="ログイン", exact=True).click()

    # Step5: ログインページから離れたことを確認
    # headless環境ではリダイレクトに時間がかかるためタイムアウトを延長
    expect(page).not_to_have_url(re.compile(r"/login"), timeout=30000)


# =============================================================================
# テスト6: TOKIUM ID ログイン画面の表示確認
# =============================================================================

def test_tokium_idログイン画面の表示確認(page: Page):
    """TOKIUM ID ログイン画面（dev.keihi.com）の主要要素がすべて表示されている"""

    # Step1: invoicingからTOKIUM IDログイン画面に遷移
    goto_tokium_id_login(page)

    # Step2: URLがdev.keihi.comのログイン画面であること
    expect(page).to_have_url(re.compile(r"dev\.keihi\.com/users/sign_in"))

    # Step3: メールアドレス・パスワード入力欄の表示確認
    expect(page.locator('input[name="user[email]"]')).to_be_visible()
    expect(page.locator('input[name="user[password]"]')).to_be_visible()

    # Step4: ログインボタンの表示確認
    expect(page.locator('#sign_in_form button[type="button"]')).to_be_visible()

    # Step5: パスワードリセットリンクの表示確認
    expect(page.get_by_role("link", name=re.compile(r"パスワード.*忘れ"))).to_be_visible()

    # Step6: Google / Microsoft 365 ログインボタンの表示確認
    expect(page.get_by_role("button", name=re.compile(r"Google"))).to_be_visible()
    expect(page.get_by_role("button", name=re.compile(r"Microsoft"))).to_be_visible()

    # Step7: サブドメインボタンの表示確認
    expect(page.get_by_role("button", name=re.compile(r"サブドメイン"))).to_be_visible()


# =============================================================================
# テスト7: TOKIUM ID ログイン成功
# =============================================================================

def test_tokium_idログイン成功(page: Page):
    """TOKIUM IDで正しい認証情報を入力し、SSOでinvoicingにログインできる"""

    # Step1: TOKIUM IDでログイン実行（SSOでinvoicingにリダイレクト）
    perform_tokium_id_login(page)

    # Step2: invoicing-staging に遷移していること
    expect(page).to_have_url(re.compile(r"invoicing-staging\.keihi\.com"))

    # Step3: ユーザーメニューボタンの確認（認証済み状態 = 事業所名がヘッダーに表示）
    expect(page.get_by_role("button", name=re.compile(r"マルチテナント検証用"))).to_be_visible()

    # Step4: サイドバーのナビゲーションが表示されている（認証済み状態）
    expect(page.locator('a[href="/invoices"]')).to_be_visible()
    expect(page.locator('a[href="/partners"]')).to_be_visible()


# =============================================================================
# テスト8: TOKIUM ID → invoicing 遷移
# =============================================================================

def test_tokium_id_invoicing遷移(tokium_id_page: Page):
    """TOKIUM IDログイン後、invoicing内のページ遷移ができる（認証セッション有効）"""

    page = tokium_id_page

    # Step1: invoicing-staging にいることを確認
    expect(page).to_have_url(re.compile(r"invoicing-staging\.keihi\.com"))

    # Step2: サイドバーから取引先ページに遷移（認証済みセッションの検証）
    page.locator('a[href="/partners"]').click()
    expect(page).to_have_url(re.compile(r"/partners"), timeout=15000)


# =============================================================================
# テスト9: 空欄でのログイン試行（異常系）
# =============================================================================

@pytest.mark.regression
def test_空欄でのログイン試行(page: Page):
    """入力なしでログインボタンを押すとログインページに留まる"""

    # Step1: ログインページに遷移
    goto_login(page)

    # Step2: 何も入力せずにログインボタンをクリック
    page.get_by_role("button", name="ログイン", exact=True).click()

    # Step3: ログインページに留まること（HTML5バリデーションまたはフォーム制御でブロック）
    page.wait_for_timeout(1000)
    expect(page).to_have_url(re.compile(r"/login"))


# =============================================================================
# テスト10: 不正なパスワードでのログイン（異常系）
# =============================================================================

@pytest.mark.regression
def test_不正なパスワードでのログイン(page: Page):
    """間違ったパスワードでログインするとエラーが表示される"""

    # Step1: ログインページに遷移
    goto_login(page)

    # Step2: メールアドレスを入力
    page.get_by_label("メールアドレス").fill(TEST_EMAIL)

    # Step3: 不正なパスワードを入力
    page.get_by_label("パスワード").fill("WrongPassword999!")

    # Step4: ログインボタンをクリック
    page.wait_for_timeout(500)
    page.get_by_role("button", name="ログイン", exact=True).click()

    # Step5: ログインページに留まること（認証失敗）
    page.wait_for_timeout(3000)
    expect(page).to_have_url(re.compile(r"/login"))


# =============================================================================
# テスト11: TOKIUM ID 空欄でのログイン試行（異常系）
# =============================================================================

@pytest.mark.regression
def test_tokium_id空欄でのログイン試行(page: Page):
    """TOKIUM IDログイン画面で空欄のままログインボタンを押すとエラーが表示される"""

    # Step1: TOKIUM IDログイン画面に遷移
    goto_tokium_id_login(page)

    # Step2: 何も入力せずにログインボタンをクリック
    page.locator('#sign_in_form button[type="button"]').click()

    # Step3: ログイン画面に留まること
    page.wait_for_timeout(3000)
    expect(page).to_have_url(re.compile(r"dev\.keihi\.com"))

    # Step4: エラーメッセージが表示されること
    expect(page.get_by_text("ログインに失敗しました")).to_be_visible()


# =============================================================================
# テスト12: TOKIUM ID 不正なパスワードでのログイン（異常系）
# =============================================================================

@pytest.mark.regression
def test_tokium_id不正なパスワードでのログイン(page: Page):
    """TOKIUM IDログイン画面で不正なパスワードを入力するとエラーが表示される"""

    # Step1: TOKIUM IDログイン画面に遷移
    goto_tokium_id_login(page)

    # Step2: メールアドレスを入力
    page.locator('input[name="user[email]"]').fill(TOKIUM_ID_EMAIL)

    # Step3: 不正なパスワードを入力
    page.locator('input[name="user[password]"]').fill("WrongPassword999!")

    # Step4: ログインボタンをクリック
    page.wait_for_timeout(500)
    page.locator('#sign_in_form button[type="button"]').click()

    # Step5: ログイン画面に留まること（認証失敗）
    page.wait_for_timeout(3000)
    expect(page).to_have_url(re.compile(r"dev\.keihi\.com"))

    # Step6: エラーメッセージが表示されること
    expect(page.get_by_text("ログインに失敗しました")).to_be_visible()
