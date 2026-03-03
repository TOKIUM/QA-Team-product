"""
PDF取り込み画面テスト

対象URL:
  - ファイル分割: /invoices/pdf-organizer/separation
  - ファイルリネーム: /invoices/pdf-organizer/rename

画面構成:
  - 親ページ: ヘッダー、サイドバー、パンくず、モード切替リンク、見出し
  - organizer iframe: ステッパー、アップロード領域、コンパクトモード、ボタン

技術的特徴:
  - メインコンテンツはクロスオリジンiframe（tpmlyr.dev.components.asaservice.inc）内
  - iframe name="organizer" → page.frame(name="organizer") で取得
  - /invoices/pdf-organizer は /invoices/pdf-organizer/separation にリダイレクト

test_results対応: 各テストにTH-IDを付与し、conftest.pyのフックで
スクリーンショット・ログ・JSONサマリーを自動保存する。
"""

import re
import pytest
from playwright.sync_api import Page, expect


BASE_URL = "https://invoicing-staging.keihi.com"
SEPARATION_URL = f"{BASE_URL}/invoices/pdf-organizer/separation"
RENAME_URL = f"{BASE_URL}/invoices/pdf-organizer/rename"
PDF_ORGANIZER_URL = f"{BASE_URL}/invoices/pdf-organizer"

# iframe読み込み待機時間（ミリ秒）
IFRAME_LOAD_WAIT = 8000
IFRAME_ACTION_WAIT = 3000


# =============================================================================
# TH-ID マッピング
# =============================================================================
TH_ID_MAP = {
    "test_ファイル分割モードにURL直接アクセスできる": "TH-PO01",
    "test_pdf_organizerリダイレクト": "TH-PO02",
    "test_ファイル分割モードの見出し": "TH-PO03",
    "test_ファイル分割モードのパンくず": "TH-PO04",
    "test_ファイル分割モードのモード切替リンク": "TH-PO05",
    "test_ファイルリネームモードにURL直接アクセスできる": "TH-PO06",
    "test_ファイルリネームモードの見出し": "TH-PO07",
    "test_ファイルリネームモードのパンくず": "TH-PO08",
    "test_ファイルリネームモードのモード切替リンク": "TH-PO09",
    "test_分割モードからリネームモードに切替できる": "TH-PO10",
    "test_リネームモードから分割モードに切替できる": "TH-PO11",
    "test_パンくず請求書リンクで一覧画面に遷移": "TH-PO12",
    "test_パンくずPDFを取り込むリンクで遷移": "TH-PO13",
    "test_ヘッダーが表示される": "TH-PO14",
    "test_サイドバーが表示される": "TH-PO15",
    "test_サイドバーから請求書画面に遷移できる": "TH-PO16",
    "test_organizer_iframeが存在する_分割モード": "TH-PO17",
    "test_organizer_iframeが存在する_リネームモード": "TH-PO18",
    "test_organizer_iframeのsrcが正しい": "TH-PO19",
    "test_分割モードのステッパー表示": "TH-PO20",
    "test_分割モードの案内テキスト": "TH-PO21",
    "test_分割モードのキャンセルボタン": "TH-PO22",
    "test_分割モードの次へボタン": "TH-PO23",
    "test_リネームモードのステッパー表示": "TH-PO24",
    "test_リネームモードの案内テキスト": "TH-PO25",
    "test_リネームモードのキャンセルボタン": "TH-PO26",
    "test_リネームモードの次へボタン": "TH-PO27",
}


@pytest.fixture(autouse=True)
def _set_th_id(request):
    """テスト関数名からTH-IDを自動付与（[chromium]等のパラメータを除去して照合）"""
    node_name = request.node.name
    base_name = node_name.split("[")[0] if "[" in node_name else node_name
    th_id = TH_ID_MAP.get(base_name)
    if th_id:
        request.node._th_id = th_id


# =============================================================================
# ヘルパー関数
# =============================================================================

def goto_separation(page: Page) -> Page:
    """ファイル分割モードに遷移"""
    page.goto(SEPARATION_URL)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(IFRAME_LOAD_WAIT)
    return page


def goto_rename(page: Page) -> Page:
    """ファイルリネームモードに遷移"""
    page.goto(RENAME_URL)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(IFRAME_LOAD_WAIT)
    return page


def get_organizer_frame(page: Page):
    """organizer iframeを取得して返す（name="organizer"で取得）"""
    frame = page.frame(name="organizer")
    if frame is None:
        # フォールバック: 外部ドメインURLパターンで取得
        frame = page.frame(
            url=lambda url: "tpmlyr.dev.components.asaservice.inc" in url
        )
    assert frame is not None, "organizer iframeが見つからない"
    frame.wait_for_load_state("networkidle")
    page.wait_for_timeout(IFRAME_ACTION_WAIT)
    return frame


# =============================================================================
# 1. 画面遷移・基本表示テスト（ファイル分割モード）
# =============================================================================

def test_ファイル分割モードにURL直接アクセスできる(logged_in_page: Page):
    """ファイル分割URLを直接指定して画面が表示される"""
    page = goto_separation(logged_in_page)
    expect(page).to_have_url(re.compile(r"/invoices/pdf-organizer/separation"))


def test_pdf_organizerリダイレクト(logged_in_page: Page):
    """/invoices/pdf-organizer にアクセスすると /separation にリダイレクトされる"""
    page = logged_in_page
    page.goto(PDF_ORGANIZER_URL)
    page.wait_for_load_state("networkidle")
    expect(page).to_have_url(re.compile(r"/invoices/pdf-organizer/separation"), timeout=15000)


def test_ファイル分割モードの見出し(logged_in_page: Page):
    """見出し「PDFを分割して取り込む」が表示される"""
    page = goto_separation(logged_in_page)
    heading = page.get_by_role("heading", name="PDFを分割して取り込む")
    expect(heading).to_be_visible()


def test_ファイル分割モードのパンくず(logged_in_page: Page):
    """パンくず「請求書 > PDFを取り込む > ファイル分割」が表示される"""
    page = goto_separation(logged_in_page)

    breadcrumb = page.locator("#main-content").locator("nav")
    # 「請求書」リンク
    expect(breadcrumb.get_by_role("link", name="請求書")).to_be_visible()
    # 「PDFを取り込む」リンク
    expect(breadcrumb.get_by_role("link", name="PDFを取り込む")).to_be_visible()
    # 現在ページ「ファイル分割」テキスト
    expect(page.locator("#main-content nav span", has_text="ファイル分割")).to_be_visible()


def test_ファイル分割モードのモード切替リンク(logged_in_page: Page):
    """「ファイルリネームに切り替える」リンクが表示される"""
    page = goto_separation(logged_in_page)
    link = page.get_by_role("link", name="ファイルリネームに切り替える")
    expect(link).to_be_visible()


# =============================================================================
# 2. 画面遷移・基本表示テスト（ファイルリネームモード）
# =============================================================================

def test_ファイルリネームモードにURL直接アクセスできる(logged_in_page: Page):
    """ファイルリネームURLを直接指定して画面が表示される"""
    page = goto_rename(logged_in_page)
    expect(page).to_have_url(re.compile(r"/invoices/pdf-organizer/rename"))


def test_ファイルリネームモードの見出し(logged_in_page: Page):
    """見出し「PDFをリネームして取り込む」が表示される"""
    page = goto_rename(logged_in_page)
    heading = page.get_by_role("heading", name="PDFをリネームして取り込む")
    expect(heading).to_be_visible()


def test_ファイルリネームモードのパンくず(logged_in_page: Page):
    """パンくず「請求書 > PDFを取り込む > ファイルリネーム」が表示される"""
    page = goto_rename(logged_in_page)

    breadcrumb = page.locator("#main-content").locator("nav")
    expect(breadcrumb.get_by_role("link", name="請求書")).to_be_visible()
    expect(breadcrumb.get_by_role("link", name="PDFを取り込む")).to_be_visible()
    expect(page.locator("#main-content nav span", has_text="ファイルリネーム")).to_be_visible()


def test_ファイルリネームモードのモード切替リンク(logged_in_page: Page):
    """「ファイル分割に切り替える」リンクが表示される"""
    page = goto_rename(logged_in_page)
    link = page.get_by_role("link", name="ファイル分割に切り替える")
    expect(link).to_be_visible()


# =============================================================================
# 3. モード切替テスト
# =============================================================================

def test_分割モードからリネームモードに切替できる(logged_in_page: Page):
    """ファイル分割モードの切替リンクでリネームモードに遷移できる"""
    page = goto_separation(logged_in_page)

    link = page.get_by_role("link", name="ファイルリネームに切り替える")
    link.click()
    expect(page).to_have_url(re.compile(r"/invoices/pdf-organizer/rename"), timeout=15000)

    # 見出し変化を確認
    heading = page.get_by_role("heading", name="PDFをリネームして取り込む")
    expect(heading).to_be_visible(timeout=10000)


def test_リネームモードから分割モードに切替できる(logged_in_page: Page):
    """ファイルリネームモードの切替リンクで分割モードに遷移できる"""
    page = goto_rename(logged_in_page)

    link = page.get_by_role("link", name="ファイル分割に切り替える")
    link.click()
    expect(page).to_have_url(re.compile(r"/invoices/pdf-organizer/separation"), timeout=15000)

    # 見出し変化を確認
    heading = page.get_by_role("heading", name="PDFを分割して取り込む")
    expect(heading).to_be_visible(timeout=10000)


# =============================================================================
# 4. パンくず遷移テスト
# =============================================================================

def test_パンくず請求書リンクで一覧画面に遷移(logged_in_page: Page):
    """パンくず「請求書」クリックで請求書一覧画面に遷移"""
    page = goto_separation(logged_in_page)

    breadcrumb = page.locator("#main-content").locator("nav")
    breadcrumb.get_by_role("link", name="請求書").click()
    expect(page).to_have_url(re.compile(r"/invoices"), timeout=15000)


def test_パンくずPDFを取り込むリンクで遷移(logged_in_page: Page):
    """パンくず「PDFを取り込む」クリックでPDF取り込み画面に遷移"""
    page = goto_separation(logged_in_page)

    breadcrumb = page.locator("#main-content").locator("nav")
    breadcrumb.get_by_role("link", name="PDFを取り込む").click()
    # /invoices/pdf-organizer は /separation にリダイレクト
    expect(page).to_have_url(re.compile(r"/invoices/pdf-organizer"), timeout=15000)


# =============================================================================
# 5. ヘッダー・サイドバーテスト
# =============================================================================

def test_ヘッダーが表示される(logged_in_page: Page):
    """ヘッダーにロゴ・ユーザー名・ヘルプが表示される"""
    page = goto_separation(logged_in_page)

    # ロゴ
    logo = page.get_by_role("img", name="TOKIUM 請求書発行")
    expect(logo).to_be_visible()

    # ユーザー名
    expect(page.locator("text=池田尚人").first).to_be_visible()

    # ヘルプリンク
    help_link = page.get_by_role("link", name="TOKIUM 請求書発行 - ヘルプセンター")
    expect(help_link).to_be_visible()


def test_サイドバーが表示される(logged_in_page: Page):
    """サイドバーに3つのリンクが表示される"""
    page = goto_separation(logged_in_page)

    expect(page.get_by_role("link", name="請求書", exact=True).first).to_be_visible()
    expect(page.get_by_role("link", name="取引先").first).to_be_visible()
    expect(page.get_by_role("link", name="帳票レイアウト").first).to_be_visible()


def test_サイドバーから請求書画面に遷移できる(logged_in_page: Page):
    """サイドバー「請求書」から/invoicesに遷移できる"""
    page = goto_separation(logged_in_page)

    page.get_by_role("link", name="請求書", exact=True).first.click()
    expect(page).to_have_url(re.compile(r"/invoices"), timeout=10000)


# =============================================================================
# 6. organizer iframe テスト
# =============================================================================

def test_organizer_iframeが存在する_分割モード(logged_in_page: Page):
    """ファイル分割モードでorganizer iframeが正常にロードされる"""
    page = goto_separation(logged_in_page)

    # iframeのDOM存在確認
    iframe_el = page.locator("iframe#organizer")
    expect(iframe_el).to_be_attached()

    # frameオブジェクト取得確認
    frame = page.frame(url=lambda url: "organizer" in url)
    assert frame is not None, "organizer iframe frameオブジェクトが取得できない"


def test_organizer_iframeが存在する_リネームモード(logged_in_page: Page):
    """ファイルリネームモードでorganizer iframeが正常にロードされる"""
    page = goto_rename(logged_in_page)

    iframe_el = page.locator("iframe#organizer")
    expect(iframe_el).to_be_attached()

    frame = page.frame(url=lambda url: "organizer" in url)
    assert frame is not None, "organizer iframe frameオブジェクトが取得できない"


def test_organizer_iframeのsrcが正しい(logged_in_page: Page):
    """organizer iframeのsrcが外部ドメインを指している"""
    page = goto_separation(logged_in_page)

    iframe_el = page.locator("iframe#organizer")
    src = iframe_el.get_attribute("src")
    assert src is not None, "iframe srcが設定されていない"
    assert "tpmlyr" in src, f"想定外のiframe src: {src}"
    assert "organizer" in src, f"organizer パスが含まれていない: {src}"


# =============================================================================
# 7. organizer iframe内テスト（ファイル分割モード）
# =============================================================================

def test_分割モードのステッパー表示(logged_in_page: Page):
    """ファイル分割モードで3ステップのステッパーが表示される"""
    page = goto_separation(logged_in_page)
    frame = get_organizer_frame(page)

    # ステッパーの各ステップテキスト確認
    expect(frame.locator("text=ファイルアップロード").first).to_be_visible(timeout=10000)
    expect(frame.locator("text=ファイルの分割").first).to_be_visible(timeout=10000)
    expect(frame.locator("text=プレビュー").first).to_be_visible(timeout=10000)


def test_分割モードの案内テキスト(logged_in_page: Page):
    """案内テキスト「アップロードするファイルを選択し...」が表示される"""
    page = goto_separation(logged_in_page)
    frame = get_organizer_frame(page)

    guide_text = frame.locator("text=アップロードするファイルを選択し")
    expect(guide_text.first).to_be_visible(timeout=10000)


def test_分割モードのキャンセルボタン(logged_in_page: Page):
    """キャンセルボタンが表示される"""
    page = goto_separation(logged_in_page)
    frame = get_organizer_frame(page)

    cancel_btn = frame.locator('button:has-text("キャンセル")')
    if cancel_btn.count() == 0:
        cancel_btn = frame.get_by_role("button", name="キャンセル")
    expect(cancel_btn.first).to_be_visible(timeout=10000)


def test_分割モードの次へボタン(logged_in_page: Page):
    """次へボタンが表示され、初期状態でdisabledである"""
    page = goto_separation(logged_in_page)
    frame = get_organizer_frame(page)

    next_btn = frame.locator('button:has-text("次へ")')
    if next_btn.count() == 0:
        next_btn = frame.get_by_role("button", name="次へ")
    expect(next_btn.first).to_be_visible(timeout=10000)

    # 初期状態でdisabledであること確認（ファイル未選択のため）
    expect(next_btn.first).to_be_disabled()


# =============================================================================
# 8. organizer iframe内テスト（ファイルリネームモード）
# =============================================================================

def test_リネームモードのステッパー表示(logged_in_page: Page):
    """ファイルリネームモードで2ステップのステッパーが表示される"""
    page = goto_rename(logged_in_page)
    frame = get_organizer_frame(page)

    expect(frame.locator("text=ファイルアップロード").first).to_be_visible(timeout=10000)
    expect(frame.locator("text=ファイル名の変換").first).to_be_visible(timeout=10000)


def test_リネームモードの案内テキスト(logged_in_page: Page):
    """案内テキストが表示される"""
    page = goto_rename(logged_in_page)
    frame = get_organizer_frame(page)

    guide_text = frame.locator("text=アップロードするファイルを選択し")
    expect(guide_text.first).to_be_visible(timeout=10000)


def test_リネームモードのキャンセルボタン(logged_in_page: Page):
    """キャンセルボタンが表示される"""
    page = goto_rename(logged_in_page)
    frame = get_organizer_frame(page)

    cancel_btn = frame.locator('button:has-text("キャンセル")')
    if cancel_btn.count() == 0:
        cancel_btn = frame.get_by_role("button", name="キャンセル")
    expect(cancel_btn.first).to_be_visible(timeout=10000)


def test_リネームモードの次へボタン(logged_in_page: Page):
    """次へボタンが表示され、初期状態でdisabledである"""
    page = goto_rename(logged_in_page)
    frame = get_organizer_frame(page)

    next_btn = frame.locator('button:has-text("次へ")')
    if next_btn.count() == 0:
        next_btn = frame.get_by_role("button", name="次へ")
    expect(next_btn.first).to_be_visible(timeout=10000)
    expect(next_btn.first).to_be_disabled()
