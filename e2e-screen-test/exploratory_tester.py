"""
探索的テストモジュール v2

ISTQB/JSTQB + HTSM(James Bach) + Hendrickson Cheat Sheet + OWASP に基づく
10カテゴリの自動探索的テスト。画面調査JSONからURL一覧を抽出しPlaywrightで実行。

カテゴリ:
  1. コンソール・ページエラー (console)
  2. ネットワーク・レスポンス (network)
  3. パフォーマンス・Core Web Vitals (performance)
  4. リンク検証 (links)
  5. UI/レイアウト整合性 (ui_integrity)
  6. フォーム検証 (forms)
  7. セキュリティ (security)
  8. アクセシビリティ (accessibility)
  9. 国際化・日本語 (i18n)
  10. ナビゲーション・状態 (navigation)

使い方:
  python exploratory_tester.py                    # 全カテゴリ実行
  python exploratory_tester.py --url <URL>        # 特定URLのみ
  python exploratory_tester.py --categories console,security  # カテゴリ指定
  python exploratory_tester.py --max-pages 10     # 最大ページ数制限
"""

import json
import os
import re
import time
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, Page, BrowserContext
from dotenv import load_dotenv


BASE_DIR = Path(__file__).parent
INVESTIGATION_DIR = BASE_DIR / "screen_investigation"
SCREENSHOT_DIR = INVESTIGATION_DIR / "screenshots" / "exploratory"

ALL_CATEGORIES = [
    "console", "network", "performance", "links", "ui_integrity",
    "forms", "security", "accessibility", "i18n", "navigation",
]


# ---------------------------------------------------------------------------
# URL収集
# ---------------------------------------------------------------------------

def collect_urls_from_json() -> list[dict]:
    """screen_investigation/*.json からURL一覧を収集"""
    urls = []
    seen = set()

    for json_file in sorted(INVESTIGATION_DIR.glob("*.json")):
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        for url in _extract_urls(data):
            if url not in seen and _is_testable_url(url):
                seen.add(url)
                urls.append({"url": url, "source": json_file.name})
    return urls


def _extract_urls(obj, depth=0) -> list[str]:
    if depth > 10:
        return []
    urls = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("url", "href", "link") and isinstance(v, str) and v.startswith("http"):
                urls.append(v)
            urls.extend(_extract_urls(v, depth + 1))
    elif isinstance(obj, list):
        for item in obj:
            urls.extend(_extract_urls(item, depth + 1))
    elif isinstance(obj, str) and obj.startswith("https://") and ".keihi.com" in obj:
        urls.append(obj)
    return urls


def _is_testable_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    if not parsed.hostname or ".keihi.com" not in parsed.hostname:
        return False
    skip = ["/sign_out", "/logout", "/destroy", "/delete", "/remove"]
    return not any(p in parsed.path.lower() for p in skip)


# ---------------------------------------------------------------------------
# 1. コンソール・ページエラー (SFDIPOT: Function)
# ---------------------------------------------------------------------------

def check_console(page: Page, _url: str) -> dict:
    """ページ読み込み後のコンソールエラー・ページエラーを収集（イベント登録は呼び出し元で実施済み前提）"""
    # この関数は test_page 内で console_errors/page_errors を収集した後に呼ばれる
    # → test_page で直接処理するため、ここではスタブ
    return {}


# ---------------------------------------------------------------------------
# 2. ネットワーク・レスポンス (SFDIPOT: Interfaces)
# ---------------------------------------------------------------------------

def check_network(page: Page, _url: str) -> dict:
    # test_page で直接処理するため、ここではスタブ
    return {}


# ---------------------------------------------------------------------------
# 3. パフォーマンス・Core Web Vitals (HTSM: Performance)
# ---------------------------------------------------------------------------

def check_performance(page: Page, url: str) -> dict:
    """DOM規模・Core Web Vitals・リソース負荷を計測"""
    result = {"findings": []}
    try:
        metrics = page.evaluate("""() => {
            const res = {};
            // DOM node count
            res.dom_nodes = document.querySelectorAll('*').length;
            // JS heap (Chrome only)
            if (performance.memory) {
                res.js_heap_mb = Math.round(performance.memory.usedJSHeapSize / 1024 / 1024 * 10) / 10;
            }
            // performance.timing (legacy but widely supported)
            const t = performance.timing;
            if (t.navigationStart > 0) {
                res.dom_complete_ms = t.domComplete - t.navigationStart;
                res.load_event_ms = t.loadEventEnd - t.navigationStart;
                res.ttfb_ms = t.responseStart - t.navigationStart;
            }
            // resource count & total size
            const entries = performance.getEntriesByType('resource');
            res.resource_count = entries.length;
            res.total_transfer_kb = Math.round(
                entries.reduce((s, e) => s + (e.transferSize || 0), 0) / 1024
            );
            // large images (>500KB)
            res.large_images = entries
                .filter(e => e.initiatorType === 'img' && (e.transferSize || 0) > 500 * 1024)
                .map(e => ({url: e.name.slice(0, 150), size_kb: Math.round(e.transferSize / 1024)}));
            return res;
        }""")

        if metrics.get("dom_nodes", 0) > 3000:
            result["findings"].append({
                "severity": "high", "category": "performance",
                "detail": f"DOM要素数過多: {metrics['dom_nodes']}ノード (閾値3000)"
            })
        elif metrics.get("dom_nodes", 0) > 1500:
            result["findings"].append({
                "severity": "medium", "category": "performance",
                "detail": f"DOM要素数やや多い: {metrics['dom_nodes']}ノード (閾値1500)"
            })

        if metrics.get("js_heap_mb", 0) > 50:
            result["findings"].append({
                "severity": "high", "category": "performance",
                "detail": f"JSヒープ過大: {metrics['js_heap_mb']}MB (閾値50MB)"
            })

        if metrics.get("ttfb_ms", 0) > 1000:
            result["findings"].append({
                "severity": "medium", "category": "performance",
                "detail": f"TTFB遅延: {metrics['ttfb_ms']}ms (閾値1000ms)"
            })

        if metrics.get("resource_count", 0) > 100:
            result["findings"].append({
                "severity": "medium", "category": "performance",
                "detail": f"リクエスト数過多: {metrics['resource_count']}件 (閾値100)"
            })

        for img in metrics.get("large_images", []):
            result["findings"].append({
                "severity": "low", "category": "performance",
                "detail": f"大サイズ画像: {img['size_kb']}KB - {img['url']}"
            })

        result["metrics"] = metrics
    except Exception as e:
        result["error"] = str(e)[:200]

    # LCP (Largest Contentful Paint) - PerformanceObserver
    try:
        lcp = page.evaluate("""() => {
            return new Promise(resolve => {
                const observer = new PerformanceObserver(list => {
                    const entries = list.getEntries();
                    resolve(entries.length > 0 ? entries[entries.length - 1].startTime : null);
                });
                observer.observe({type: 'largest-contentful-paint', buffered: true});
                setTimeout(() => resolve(null), 1000);
            });
        }""")
        if lcp and lcp > 2500:
            result["findings"].append({
                "severity": "high", "category": "performance",
                "detail": f"LCP不良: {round(lcp)}ms (閾値2500ms)"
            })
        if lcp:
            result.setdefault("metrics", {})["lcp_ms"] = round(lcp)
    except Exception:
        pass

    # CLS (Cumulative Layout Shift)
    try:
        cls_val = page.evaluate("""() => {
            return new Promise(resolve => {
                let cls = 0;
                const observer = new PerformanceObserver(list => {
                    for (const entry of list.getEntries()) {
                        if (!entry.hadRecentInput) cls += entry.value;
                    }
                });
                observer.observe({type: 'layout-shift', buffered: true});
                setTimeout(() => resolve(Math.round(cls * 1000) / 1000), 1000);
            });
        }""")
        if cls_val and cls_val > 0.1:
            result["findings"].append({
                "severity": "medium", "category": "performance",
                "detail": f"CLS不良: {cls_val} (閾値0.1)"
            })
        if cls_val is not None:
            result.setdefault("metrics", {})["cls"] = cls_val
    except Exception:
        pass

    return result


# ---------------------------------------------------------------------------
# 4. リンク検証 (FCC CUTS VIDS: Structure Tour)
# ---------------------------------------------------------------------------

def check_links(page: Page, url: str) -> dict:
    """リンク切れ + dead-end検出（ボタン・クリッカブル要素含む）"""
    result = {"total": 0, "broken": [], "dead_clicks": []}
    try:
        links = page.evaluate("""() => {
            const anchors = Array.from(document.querySelectorAll('a[href]'))
                .map(a => ({href: a.href, text: (a.textContent || '').trim().slice(0, 50)}))
                .filter(a => a.href.startsWith('http'));
            // href="#" や javascript:void(0) のリンク（dead-end候補）
            const deadEnds = Array.from(document.querySelectorAll('a[href="#"], a[href="javascript:void(0)"], a[href="javascript:;"]'))
                .map(a => ({href: a.getAttribute('href'), text: (a.textContent || '').trim().slice(0, 50)}));
            return {links: anchors.slice(0, 50), dead_ends: deadEnds.slice(0, 20)};
        }""")
        result["total"] = len(links.get("links", []))

        for link in links.get("links", []):
            if not _is_testable_url(link["href"]):
                continue
            try:
                resp = page.request.head(link["href"], timeout=5000)
                if resp.status >= 400:
                    result["broken"].append({
                        "url": link["href"][:200], "text": link["text"],
                        "status": resp.status
                    })
            except Exception:
                pass

        for de in links.get("dead_ends", []):
            result["dead_clicks"].append({
                "href": de["href"], "text": de["text"],
                "issue": "href='#'またはjavascript:void(0) — 機能していない可能性"
            })
    except Exception as e:
        result["error"] = str(e)[:200]
    return result


# ---------------------------------------------------------------------------
# 5. UI/レイアウト整合性 (HTSM: Structure + Hendrickson)
# ---------------------------------------------------------------------------

def check_ui_integrity(page: Page, url: str) -> dict:
    """テキスト溢れ・画像破損・水平スクロール・空コンテナ・重複ID等"""
    result = {"findings": []}
    try:
        ui_issues = page.evaluate("""() => {
            const issues = [];
            // 1. 水平スクロールバー検出
            if (document.body.scrollWidth > window.innerWidth + 5) {
                issues.push({type: 'horizontal_scroll',
                    detail: `body.scrollWidth(${document.body.scrollWidth}) > window.innerWidth(${window.innerWidth})`});
            }
            // 2. テキスト溢れ検出（overflow hidden + text truncated）
            const textEls = document.querySelectorAll('p, span, td, th, div, h1, h2, h3, h4, li, a, label');
            let overflowCount = 0;
            for (const el of textEls) {
                if (el.scrollWidth > el.offsetWidth + 2 && el.offsetWidth > 0) {
                    const style = getComputedStyle(el);
                    if (style.overflow === 'hidden' || style.textOverflow === 'ellipsis') continue;
                    overflowCount++;
                    if (overflowCount <= 5) {
                        issues.push({type: 'text_overflow',
                            detail: `${el.tagName}.${el.className.toString().slice(0,30)}: scrollW=${el.scrollWidth} > offsetW=${el.offsetWidth}`,
                            text: (el.textContent || '').trim().slice(0, 60)});
                    }
                }
            }
            if (overflowCount > 5) {
                issues.push({type: 'text_overflow_summary', detail: `他${overflowCount - 5}件のテキスト溢れ`});
            }
            // 3. 画像破損検出
            const imgs = document.querySelectorAll('img');
            for (const img of imgs) {
                if (img.naturalWidth === 0 && img.src && !img.src.startsWith('data:')) {
                    issues.push({type: 'broken_image', detail: img.src.slice(0, 150),
                        alt: img.alt || '(alt未設定)'});
                }
            }
            // 4. 空のメインコンテナ検出
            const mainContent = document.querySelector('main, [role="main"], #main, .main-content, .content');
            if (mainContent && mainContent.innerText.trim().length === 0) {
                issues.push({type: 'empty_main_content', detail: 'メインコンテンツ領域が空'});
            }
            // 5. 重複ID検出
            const allIds = Array.from(document.querySelectorAll('[id]')).map(e => e.id).filter(id => id);
            const idCounts = {};
            for (const id of allIds) { idCounts[id] = (idCounts[id] || 0) + 1; }
            const dupes = Object.entries(idCounts).filter(([, c]) => c > 1).slice(0, 10);
            for (const [id, count] of dupes) {
                issues.push({type: 'duplicate_id', detail: `id="${id}" が${count}回出現`});
            }
            // 6. 要素の重なり検出（主要なインタラクティブ要素同士）
            const interactives = Array.from(document.querySelectorAll('button, a, input, select, textarea'))
                .filter(el => el.offsetWidth > 0 && el.offsetHeight > 0).slice(0, 30);
            let overlapCount = 0;
            for (let i = 0; i < interactives.length && overlapCount < 3; i++) {
                const r1 = interactives[i].getBoundingClientRect();
                for (let j = i + 1; j < interactives.length && overlapCount < 3; j++) {
                    const r2 = interactives[j].getBoundingClientRect();
                    if (r1.left < r2.right && r1.right > r2.left &&
                        r1.top < r2.bottom && r1.bottom > r2.top) {
                        const overlapArea = Math.max(0, Math.min(r1.right, r2.right) - Math.max(r1.left, r2.left))
                            * Math.max(0, Math.min(r1.bottom, r2.bottom) - Math.max(r1.top, r2.top));
                        const minArea = Math.min(r1.width * r1.height, r2.width * r2.height);
                        if (minArea > 0 && overlapArea / minArea > 0.3) {
                            overlapCount++;
                            issues.push({type: 'element_overlap',
                                detail: `${interactives[i].tagName}(${(interactives[i].textContent||'').trim().slice(0,20)}) と ${interactives[j].tagName}(${(interactives[j].textContent||'').trim().slice(0,20)}) が30%以上重なり`});
                        }
                    }
                }
            }
            return issues;
        }""")
        for issue in ui_issues:
            severity = "medium" if issue["type"] in ("broken_image", "empty_main_content", "horizontal_scroll") else "low"
            result["findings"].append({
                "severity": severity, "category": "ui_integrity", **issue
            })
    except Exception as e:
        result["error"] = str(e)[:200]
    return result


# ---------------------------------------------------------------------------
# 6. フォーム検証 (Hendrickson: Data Type Attacks + SFDIPOT: Data)
# ---------------------------------------------------------------------------

def check_forms(page: Page, url: str) -> dict:
    """空サブミット + 入力フィールド属性検証 + 境界値テスト対象の特定"""
    result = {"total": 0, "issues": [], "input_audit": []}

    try:
        form_info = page.evaluate("""() => {
            const forms = document.querySelectorAll('form');
            const result = {count: forms.length, inputs: []};
            for (const form of forms) {
                const inputs = form.querySelectorAll('input, textarea, select');
                for (const inp of inputs) {
                    if (inp.type === 'hidden' || inp.type === 'submit') continue;
                    result.inputs.push({
                        tag: inp.tagName.toLowerCase(),
                        type: inp.type || 'text',
                        name: inp.name || inp.id || '',
                        required: inp.required,
                        maxlength: inp.maxLength > 0 ? inp.maxLength : null,
                        min: inp.min || null,
                        max: inp.max || null,
                        pattern: inp.pattern || null,
                        placeholder: inp.placeholder || '',
                        autocomplete: inp.autocomplete || '',
                        // 金額系フィールドの特定（TOKIUM固有: 請求金額等）
                        is_amount: /amount|price|cost|金額|合計|税|price/i.test(
                            (inp.name || '') + (inp.id || '') + (inp.placeholder || '') +
                            (inp.getAttribute('aria-label') || '')),
                    });
                }
            }
            return result;
        }""")

        result["total"] = form_info["count"]

        for inp in form_info.get("inputs", []):
            # required属性なしのテキスト系入力
            if inp["type"] in ("text", "email", "tel", "number", "password") and not inp["required"]:
                # 重要そうな名前なのにrequired未設定
                important_names = re.compile(r'email|password|name|amount|金額', re.IGNORECASE)
                if important_names.search(inp["name"]):
                    result["issues"].append({
                        "severity": "low", "type": "missing_required",
                        "detail": f"重要フィールド '{inp['name']}' にrequired属性なし"
                    })

            # maxlength未設定のテキストフィールド
            if inp["type"] in ("text", "textarea") and not inp["maxlength"]:
                result["input_audit"].append({
                    "field": inp["name"], "type": inp["type"],
                    "issue": "maxlength未設定 — 長文入力で問題の可能性"
                })

            # 金額フィールドにmin/max未設定
            if inp["is_amount"] and inp["type"] == "number" and not inp["min"]:
                result["issues"].append({
                    "severity": "medium", "type": "amount_no_min",
                    "detail": f"金額フィールド '{inp['name']}' にmin未設定 — 負数入力可能"
                })

            # パスワードフィールドのautocomplete
            if inp["type"] == "password" and inp["autocomplete"] not in ("off", "new-password", "current-password"):
                result["issues"].append({
                    "severity": "low", "type": "password_autocomplete",
                    "detail": f"パスワードフィールド '{inp['name']}' のautocomplete属性が不適切: '{inp['autocomplete']}'"
                })

    except Exception as e:
        result["error"] = str(e)[:200]

    # ダブルサブミット防止チェック
    try:
        double_submit = page.evaluate("""() => {
            const submits = document.querySelectorAll('button[type="submit"], input[type="submit"]');
            const results = [];
            for (const btn of submits) {
                // disabled属性やdata-disable-withがあるか
                const hasProtection = btn.disabled ||
                    btn.getAttribute('data-disable-with') ||
                    btn.getAttribute('data-loading') ||
                    btn.closest('form')?.getAttribute('data-remote') === 'true';
                if (!hasProtection && btn.offsetWidth > 0) {
                    results.push({
                        text: (btn.textContent || btn.value || '').trim().slice(0, 30),
                        form_action: (btn.closest('form')?.action || '').slice(0, 100),
                    });
                }
            }
            return results;
        }""")
        for btn in double_submit:
            result["issues"].append({
                "severity": "medium", "type": "no_double_submit_protection",
                "detail": f"ボタン '{btn['text']}' にダブルサブミット防止なし (action: {btn['form_action']})"
            })
    except Exception:
        pass

    return result


# ---------------------------------------------------------------------------
# 7. セキュリティ (OWASP Testing Guide)
# ---------------------------------------------------------------------------

def check_security(page: Page, url: str) -> dict:
    """CSRF・Cookie・セキュリティヘッダー・混在コンテンツ・URLパラメータの安全性"""
    result = {"findings": []}

    # 7-1. CSRFトークン存在チェック
    try:
        csrf_check = page.evaluate("""() => {
            const forms = document.querySelectorAll('form[method="post"], form[method="POST"]');
            const missing = [];
            for (const form of forms) {
                const hasToken = form.querySelector(
                    'input[name="authenticity_token"], input[name="_csrf"], input[name="csrf_token"], input[name="_token"]'
                );
                if (!hasToken) {
                    missing.push({action: (form.action || '').slice(0, 100)});
                }
            }
            return missing;
        }""")
        for m in csrf_check:
            result["findings"].append({
                "severity": "high", "category": "security", "type": "missing_csrf",
                "detail": f"POSTフォームにCSRFトークンなし: {m['action']}"
            })
    except Exception:
        pass

    # 7-2. セキュリティヘッダーチェック（現在のページのレスポンスヘッダー）
    try:
        resp = page.request.head(url, timeout=5000)
        headers = resp.headers
        expected_headers = {
            "x-content-type-options": "nosniff",
            "x-frame-options": None,  # 存在すればOK
            "strict-transport-security": None,
        }
        for header, expected_val in expected_headers.items():
            val = headers.get(header)
            if not val:
                result["findings"].append({
                    "severity": "medium", "category": "security", "type": "missing_header",
                    "detail": f"セキュリティヘッダー未設定: {header}"
                })
    except Exception:
        pass

    # 7-3. Cookieフラグチェック
    try:
        context = page.context
        cookies = context.cookies()
        for cookie in cookies:
            issues = []
            if cookie.get("name", "").lower() in ("_session", "_session_id", "session", "sid", "auth_token"):
                if not cookie.get("httpOnly"):
                    issues.append("HttpOnlyなし")
                if not cookie.get("secure"):
                    issues.append("Secureなし")
                if cookie.get("sameSite", "").lower() == "none":
                    issues.append("SameSite=None")
                if issues:
                    result["findings"].append({
                        "severity": "high", "category": "security", "type": "cookie_flag",
                        "detail": f"Cookie '{cookie['name']}': {', '.join(issues)}"
                    })
    except Exception:
        pass

    # 7-4. URLにセンシティブ情報が含まれていないか
    parsed = urlparse(url)
    sensitive_params = re.compile(r'(token|password|secret|key|api_key|auth|session)', re.IGNORECASE)
    if parsed.query and sensitive_params.search(parsed.query):
        result["findings"].append({
            "severity": "high", "category": "security", "type": "sensitive_in_url",
            "detail": f"URLパラメータにセンシティブ情報の可能性: {parsed.query[:100]}"
        })

    # 7-5. 混在コンテンツ検出
    try:
        mixed = page.evaluate("""() => {
            if (location.protocol !== 'https:') return [];
            const resources = performance.getEntriesByType('resource');
            return resources
                .filter(r => r.name.startsWith('http://'))
                .map(r => r.name.slice(0, 150))
                .slice(0, 5);
        }""")
        for res_url in mixed:
            result["findings"].append({
                "severity": "high", "category": "security", "type": "mixed_content",
                "detail": f"HTTPSページでHTTPリソース読み込み: {res_url}"
            })
    except Exception:
        pass

    # 7-6. クリックジャッキング防御（X-Frame-Options or CSP frame-ancestors）
    # → 7-2で X-Frame-Options は既にチェック済み

    return result


# ---------------------------------------------------------------------------
# 8. アクセシビリティ (WCAG 2.1 基本チェック)
# ---------------------------------------------------------------------------

def check_accessibility(page: Page, url: str) -> dict:
    """alt属性・フォームラベル・見出し階層・lang属性・キーボードフォーカス"""
    result = {"findings": []}
    try:
        a11y = page.evaluate("""() => {
            const issues = [];
            // 1. img alt属性
            const imgs = document.querySelectorAll('img');
            let missingAlt = 0;
            for (const img of imgs) {
                if (!img.hasAttribute('alt') && img.offsetWidth > 0) missingAlt++;
            }
            if (missingAlt > 0) {
                issues.push({type: 'missing_alt', severity: 'medium',
                    detail: `${missingAlt}個の<img>にalt属性なし`});
            }
            // 2. フォームラベル
            const inputs = document.querySelectorAll('input:not([type="hidden"]):not([type="submit"]):not([type="button"]), textarea, select');
            let missingLabel = 0;
            for (const inp of inputs) {
                if (inp.offsetWidth === 0) continue;
                const hasLabel = inp.id && document.querySelector(`label[for="${inp.id}"]`);
                const hasAriaLabel = inp.getAttribute('aria-label') || inp.getAttribute('aria-labelledby');
                const wrappedInLabel = inp.closest('label');
                const hasTitle = inp.title;
                if (!hasLabel && !hasAriaLabel && !wrappedInLabel && !hasTitle) missingLabel++;
            }
            if (missingLabel > 0) {
                issues.push({type: 'missing_form_label', severity: 'medium',
                    detail: `${missingLabel}個の入力要素にラベル関連付けなし`});
            }
            // 3. 見出し階層
            const headings = Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6'))
                .map(h => parseInt(h.tagName[1]));
            for (let i = 1; i < headings.length; i++) {
                if (headings[i] - headings[i-1] > 1) {
                    issues.push({type: 'heading_skip', severity: 'low',
                        detail: `見出しレベル飛び: h${headings[i-1]} → h${headings[i]}`});
                    break;
                }
            }
            if (headings.filter(h => h === 1).length > 1) {
                issues.push({type: 'multiple_h1', severity: 'low',
                    detail: `h1が複数存在 (${headings.filter(h => h === 1).length}個)`});
            }
            // 4. lang属性
            const htmlLang = document.documentElement.lang;
            if (!htmlLang) {
                issues.push({type: 'missing_lang', severity: 'medium',
                    detail: '<html>にlang属性なし'});
            }
            // 5. フォーカスインジケータ
            const focusables = document.querySelectorAll('a, button, input, select, textarea, [tabindex]');
            let noOutline = 0;
            for (const el of Array.from(focusables).slice(0, 20)) {
                if (el.offsetWidth === 0) continue;
                const style = getComputedStyle(el);
                if (style.outlineStyle === 'none' && style.outlineWidth === '0px') {
                    // CSSで :focus { outline: none } されている可能性
                    // → ここでは構造チェックのみ（実際のフォーカステストは別途）
                }
            }
            // 6. ボタン/リンクの空テキスト
            const emptyBtns = Array.from(document.querySelectorAll('button, a'))
                .filter(el => el.offsetWidth > 0 &&
                    !(el.textContent || '').trim() &&
                    !el.querySelector('img, svg') &&
                    !el.getAttribute('aria-label') &&
                    !el.title);
            if (emptyBtns.length > 0) {
                issues.push({type: 'empty_interactive', severity: 'medium',
                    detail: `${emptyBtns.length}個のボタン/リンクにテキスト・aria-labelなし`});
            }
            // 7. tabindex > 0（非推奨）
            const badTabindex = document.querySelectorAll('[tabindex]:not([tabindex="0"]):not([tabindex="-1"])');
            if (badTabindex.length > 0) {
                issues.push({type: 'positive_tabindex', severity: 'low',
                    detail: `tabindex>0の要素が${badTabindex.length}個 (タブ順序が不自然になる可能性)`});
            }
            return issues;
        }""")
        result["findings"] = a11y
    except Exception as e:
        result["error"] = str(e)[:200]
    return result


# ---------------------------------------------------------------------------
# 9. 国際化・日本語 (TOKIUM固有: Japanese B2B SaaS)
# ---------------------------------------------------------------------------

def check_i18n(page: Page, url: str) -> dict:
    """文字化け・日付形式・通貨表記・エンコーディングの整合性"""
    result = {"findings": []}
    try:
        i18n_issues = page.evaluate(r"""() => {
            const issues = [];
            // 1. meta charset確認
            const charset = document.characterSet || document.charset;
            if (charset && charset.toUpperCase() !== 'UTF-8') {
                issues.push({type: 'non_utf8', severity: 'high',
                    detail: `文字エンコーディングがUTF-8でない: ${charset}`});
            }
            // 2. 文字化け検出（置換文字 U+FFFD の存在）
            const bodyText = document.body.innerText || '';
            const replacementChars = (bodyText.match(/\uFFFD/g) || []).length;
            if (replacementChars > 0) {
                issues.push({type: 'mojibake', severity: 'high',
                    detail: `文字化け検出: 置換文字(U+FFFD)が${replacementChars}個`});
            }
            // 3. 日付形式の一貫性チェック
            const datePatterns = {
                'YYYY/MM/DD': /\d{4}\/\d{1,2}\/\d{1,2}/g,
                'YYYY-MM-DD': /\d{4}-\d{1,2}-\d{1,2}/g,
                'YYYY年M月D日': /\d{4}年\d{1,2}月\d{1,2}日/g,
                'MM/DD/YYYY': /\d{1,2}\/\d{1,2}\/\d{4}/g,
            };
            const foundFormats = {};
            for (const [name, re] of Object.entries(datePatterns)) {
                const matches = bodyText.match(re);
                if (matches && matches.length > 0) foundFormats[name] = matches.length;
            }
            const formatNames = Object.keys(foundFormats);
            if (formatNames.length > 1) {
                const desc = formatNames.map(n => `${n}(${foundFormats[n]}件)`).join(', ');
                issues.push({type: 'date_format_inconsistent', severity: 'low',
                    detail: `日付表記が混在: ${desc}`});
            }
            // 4. 通貨表記チェック（円記号の一貫性）
            const yenPatterns = {
                '¥記号': /¥[\d,]+/g,
                '円': /[\d,]+円/g,
            };
            const yenFormats = {};
            for (const [name, re] of Object.entries(yenPatterns)) {
                const matches = bodyText.match(re);
                if (matches) yenFormats[name] = matches.length;
            }
            // 5. 全角数字の混入
            const fullwidthNums = bodyText.match(/[０-９]+/g);
            if (fullwidthNums && fullwidthNums.length > 0) {
                issues.push({type: 'fullwidth_number', severity: 'low',
                    detail: `全角数字が${fullwidthNums.length}箇所で検出（意図的でなければ半角に統一推奨）`});
            }
            return issues;
        }""")
        result["findings"] = i18n_issues
    except Exception as e:
        result["error"] = str(e)[:200]
    return result


# ---------------------------------------------------------------------------
# 10. ナビゲーション・状態 (Hendrickson + SBTM + SFDIPOT: Operations)
# ---------------------------------------------------------------------------

def check_navigation(page: Page, url: str) -> dict:
    """ブラウザバック・ディープリンク・セッション・URLハッシュ"""
    result = {"findings": []}

    # 10-1. ブラウザバック後の状態確認
    try:
        current_url = page.url
        page.go_back()
        page.wait_for_timeout(1500)
        page.go_forward()
        page.wait_for_timeout(1500)
        after_url = page.url

        # バック→フォワード後にページ内容が壊れていないか
        content_ok = page.evaluate("""() => {
            return document.body.innerText.trim().length > 0;
        }""")
        if not content_ok:
            result["findings"].append({
                "severity": "high", "type": "back_forward_broken",
                "detail": "ブラウザバック→フォワード後にページ内容が空"
            })
        # 元のURLに戻す
        if page.url != url:
            page.goto(url, wait_until="networkidle", timeout=15000)
    except Exception:
        # ナビゲーション履歴がない場合はスキップ
        try:
            page.goto(url, wait_until="networkidle", timeout=15000)
        except Exception:
            pass

    # 10-2. ページ内の必須要素の存在チェック（ログイン切れ検出）
    try:
        session_check = page.evaluate("""() => {
            // ログインページにリダイレクトされていないか
            if (location.pathname.includes('/sign_in') || location.pathname.includes('/login')) {
                return {redirected_to_login: true, current_path: location.pathname};
            }
            // エラーページ検出
            const title = document.title.toLowerCase();
            if (title.includes('error') || title.includes('404') || title.includes('500') ||
                title.includes('エラー') || title.includes('見つかりません')) {
                return {error_page: true, title: document.title};
            }
            return {ok: true};
        }""")
        if session_check.get("redirected_to_login"):
            result["findings"].append({
                "severity": "high", "type": "session_expired",
                "detail": f"ログインページにリダイレクト: {session_check.get('current_path', '')}"
            })
        elif session_check.get("error_page"):
            result["findings"].append({
                "severity": "high", "type": "error_page",
                "detail": f"エラーページ表示: {session_check.get('title', '')}"
            })
    except Exception:
        pass

    return result


# ---------------------------------------------------------------------------
# メインテスト実行
# ---------------------------------------------------------------------------

# カテゴリ → チェック関数のマッピング
CATEGORY_CHECKERS = {
    "performance": check_performance,
    "links": check_links,
    "ui_integrity": check_ui_integrity,
    "forms": check_forms,
    "security": check_security,
    "accessibility": check_accessibility,
    "i18n": check_i18n,
    "navigation": check_navigation,
}


def test_page(page: Page, url: str, categories: list[str] | None = None,
              timeout_ms: int = 30000) -> dict:
    """1ページに対する探索的テスト実行（全カテゴリ統合）"""
    active_categories = categories or ALL_CATEGORIES

    result = {
        "url": url,
        "timestamp": datetime.now().isoformat(),
        "console_errors": [],
        "network_errors": [],
        "load_time_ms": None,
        "checks": {},
        "findings_count": 0,
        "status": "ok",
    }

    # --- イベントリスナー登録（console + network は常時ON） ---
    console_errors = []
    page.on("console", lambda msg: console_errors.append(
        {"type": msg.type, "text": msg.text[:500]}) if msg.type == "error" else None)

    page_errors = []
    page.on("pageerror", lambda err: page_errors.append(str(err)[:500]))

    network_errors = []
    def on_response(response):
        if response.status >= 400:
            network_errors.append({"url": response.url[:200], "status": response.status})
    page.on("response", on_response)

    request_failures = []
    page.on("requestfailed", lambda req: request_failures.append({
        "url": req.url[:200], "failure": req.failure or "unknown"
    }))

    # --- ページ読み込み + 速度計測 ---
    start = time.time()
    try:
        page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        load_time = (time.time() - start) * 1000
        result["load_time_ms"] = round(load_time, 0)
        if load_time > 5000:
            result["status"] = "slow"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)[:300]
        result["console_errors"] = console_errors + [{"type": "pageerror", "text": t} for t in page_errors]
        result["network_errors"] = network_errors + request_failures
        return result

    result["console_errors"] = console_errors + [{"type": "pageerror", "text": t} for t in page_errors]
    result["network_errors"] = network_errors + request_failures

    # --- 各カテゴリのチェック実行 ---
    total_findings = 0

    for cat_name, checker_fn in CATEGORY_CHECKERS.items():
        if cat_name not in active_categories:
            continue
        try:
            check_result = checker_fn(page, url)
            result["checks"][cat_name] = check_result
            findings = check_result.get("findings", [])
            issues = check_result.get("issues", [])
            broken = check_result.get("broken", [])
            total_findings += len(findings) + len(issues) + len(broken)
        except Exception as e:
            result["checks"][cat_name] = {"error": str(e)[:200]}

    result["findings_count"] = total_findings

    # ステータス判定
    if result["console_errors"] or result["network_errors"] or total_findings > 0:
        high_count = sum(
            1 for cat in result["checks"].values()
            for f in cat.get("findings", []) + cat.get("issues", [])
            if isinstance(f, dict) and f.get("severity") == "high"
        )
        if result["status"] == "ok":
            result["status"] = "critical" if high_count > 0 else "warning"

    return result


# ---------------------------------------------------------------------------
# ログイン
# ---------------------------------------------------------------------------

def do_login(context: BrowserContext) -> Page:
    """TOKIUM IDでログイン"""
    env_path = BASE_DIR / "ログイン" / ".env"
    load_dotenv(env_path)
    email = os.environ.get("TOKIUM_ID_EMAIL", "")
    password = os.environ.get("TOKIUM_ID_PASSWORD", "")
    subdomain = os.environ.get("TOKIUM_ID_SUBDOMAIN", "th-01")

    page = context.new_page()
    page.goto("https://dev.keihi.com/users/sign_in", wait_until="networkidle")

    page.fill('input[name="user[email]"]', email)
    page.fill('input[name="user[password]"]', password)
    page.get_by_role("button", name="ログイン", exact=True).click()
    page.wait_for_load_state("networkidle")

    if "subdomains" in page.url:
        try:
            page.goto("https://dev.keihi.com/subdomains/input", wait_until="networkidle")
            page.fill('input[name="subdomain"]', subdomain)
            page.get_by_role("button", name="送信").click()
            page.wait_for_load_state("networkidle")
        except Exception:
            pass

    return page


# ---------------------------------------------------------------------------
# オーケストレーター
# ---------------------------------------------------------------------------

def run_exploratory_tests(urls: list[dict] | None = None, max_pages: int = 30,
                          categories: list[str] | None = None) -> dict:
    """探索的テストのメイン実行"""
    if urls is None:
        urls = collect_urls_from_json()

    if not urls:
        return {"status": "skip", "reason": "テスト対象URLなし", "results": []}

    active_cats = categories or ALL_CATEGORIES
    urls = urls[:max_pages]
    results = []
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="ja-JP",
        )

        try:
            page = do_login(context)
        except Exception as e:
            browser.close()
            return {"status": "error", "reason": f"ログイン失敗: {e}", "results": []}

        for i, url_info in enumerate(urls):
            url = url_info["url"]
            print(f"  [{i+1}/{len(urls)}] {url[:80]}")
            try:
                result = test_page(page, url, categories=active_cats)
                result["source"] = url_info.get("source", "")
                results.append(result)

                if result["status"] in ("warning", "critical", "error", "slow"):
                    ss_name = f"issue_{i:03d}.png"
                    try:
                        page.screenshot(path=str(SCREENSHOT_DIR / ss_name))
                        result["screenshot"] = ss_name
                    except Exception:
                        pass
            except Exception as e:
                results.append({
                    "url": url, "status": "error", "error": str(e)[:300],
                    "source": url_info.get("source", "")
                })

        browser.close()

    # サマリー生成
    summary = {
        "categories_tested": active_cats,
        "total_pages": len(results),
        "ok": len([r for r in results if r.get("status") == "ok"]),
        "warnings": len([r for r in results if r.get("status") == "warning"]),
        "critical": len([r for r in results if r.get("status") == "critical"]),
        "errors": len([r for r in results if r.get("status") == "error"]),
        "slow": len([r for r in results if r.get("status") == "slow"]),
        "total_console_errors": sum(len(r.get("console_errors", [])) for r in results),
        "total_network_errors": sum(len(r.get("network_errors", [])) for r in results),
        "total_findings": sum(r.get("findings_count", 0) for r in results),
        "total_broken_links": sum(
            len(r.get("checks", {}).get("links", {}).get("broken", []))
            for r in results
        ),
        # カテゴリ別集計
        "by_category": {},
    }

    for cat in active_cats:
        cat_findings = 0
        for r in results:
            checks = r.get("checks", {}).get(cat, {})
            cat_findings += len(checks.get("findings", []))
            cat_findings += len(checks.get("issues", []))
            cat_findings += len(checks.get("broken", []))
        summary["by_category"][cat] = cat_findings

    return {"status": "done", "summary": summary, "results": results}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="探索的テスト実行 v2 (ISTQB/HTSM/OWASP準拠)")
    parser.add_argument("--max-pages", type=int, default=30, help="最大テストページ数")
    parser.add_argument("--url", help="特定URLのみテスト")
    parser.add_argument(
        "--categories", "-c",
        help=f"実行カテゴリ（カンマ区切り）。利用可能: {','.join(ALL_CATEGORIES)}",
    )
    args = parser.parse_args()

    cats = args.categories.split(",") if args.categories else None
    if args.url:
        urls = [{"url": args.url, "source": "cli"}]
    else:
        urls = None

    result = run_exploratory_tests(urls=urls, max_pages=args.max_pages, categories=cats)

    # サマリー表示
    if result.get("summary"):
        s = result["summary"]
        print(f"\n{'='*60}")
        print(f"探索的テスト結果  カテゴリ: {len(s.get('categories_tested', []))}個")
        print(f"{'='*60}")
        print(f"ページ数: {s['total_pages']} (OK:{s['ok']} / Warning:{s['warnings']} / "
              f"Critical:{s.get('critical',0)} / Error:{s['errors']} / Slow:{s['slow']})")
        print(f"検出数: {s['total_findings']}件 (コンソールエラー:{s['total_console_errors']}, "
              f"NWエラー:{s['total_network_errors']}, リンク切れ:{s['total_broken_links']})")
        if s.get("by_category"):
            print("カテゴリ別:")
            for cat, count in s["by_category"].items():
                print(f"  {cat}: {count}件")
        print(f"{'='*60}")

    # JSON出力
    print(json.dumps(result, ensure_ascii=False, indent=2))
