"""
自動生成されたテスト: ログイン機能テスト
シナリオ: scenarios/login.yaml
生成日: 2026-02-13

※ このファイルは AI が生成したサンプルです。
   実際には generate.py を実行して対象サイトに合わせたコードが生成されます。
"""

import re
import pytest
from playwright.sync_api import Page, expect


BASE_URL = "https://your-app.example.com"


# -------------------------------------------------
# テスト1: 正常ログイン
# -------------------------------------------------
def test_正常ログイン(page: Page):
    """正しいメールアドレスとパスワードでログインできる"""

    # ログインページに遷移
    page.goto(f"{BASE_URL}/login")

    # メールアドレスを入力
    page.get_by_label("メールアドレス").fill("test@example.com")

    # パスワードを入力
    page.get_by_label("パスワード").fill("SecurePass123!")

    # ログインボタンをクリック
    page.get_by_role("button", name="ログイン").click()

    # ダッシュボードに遷移したことを確認
    expect(page).to_have_url(re.compile(r"/dashboard"))

    # ウェルカムメッセージが表示されていることを確認
    expect(page.get_by_role("heading", name=re.compile("ようこそ"))).to_be_visible()


# -------------------------------------------------
# テスト2: 空欄でのログイン試行
# -------------------------------------------------
def test_空欄でのログイン試行(page: Page):
    """入力なしでログインボタンを押すとエラーが表示される"""

    # ログインページに遷移
    page.goto(f"{BASE_URL}/login")

    # 何も入力せずにログインボタンをクリック
    page.get_by_role("button", name="ログイン").click()

    # バリデーションエラーが表示されることを確認
    expect(page.get_by_text("メールアドレスを入力してください")).to_be_visible()


# -------------------------------------------------
# テスト3: 不正なパスワードでのログイン
# -------------------------------------------------
def test_不正なパスワードでのログイン(page: Page):
    """間違ったパスワードでエラーメッセージが表示される"""

    # ログインページに遷移
    page.goto(f"{BASE_URL}/login")

    # メールアドレスを入力
    page.get_by_label("メールアドレス").fill("test@example.com")

    # 不正なパスワードを入力
    page.get_by_label("パスワード").fill("wrong-password")

    # ログインボタンをクリック
    page.get_by_role("button", name="ログイン").click()

    # 認証エラーメッセージが表示されることを確認
    expect(page.get_by_role("alert")).to_contain_text("メールアドレスまたはパスワードが正しくありません")
