"""Locator操作の自動記録パッチ"""

import re
from datetime import datetime
from playwright.sync_api import Locator


def _ts():
    return datetime.now().strftime('%H:%M:%S.%f')[:-3]


def _decode_unicode_escapes(s):
    """\\uXXXX や \\\\uXXXX を実際のUnicode文字に変換"""
    return re.sub(r'\\{1,2}u([0-9a-fA-F]{4})',
                  lambda m: chr(int(m.group(1), 16)), s)


def _desc(loc):
    """ロケーターの人間可読な説明"""
    try:
        s = str(loc)
        if "selector='" in s:
            sel = s.split("selector='", 1)[1].rsplit("'", 1)[0]
        elif 'selector="' in s:
            sel = s.split('selector="', 1)[1].rsplit('"', 1)[0]
        else:
            sel = s
        sel = _decode_unicode_escapes(sel)
        sel = re.sub(r'internal:role=(\w+)\[name="([^"]+)"[si]?\]',
                     r'role=\1[name="\2"]', sel)
        sel = re.sub(r'internal:label="([^"]+)"[si]?', r'label="\1"', sel)
        sel = re.sub(r'internal:text="([^"]+)"[si]?', r'text="\1"', sel)
        sel = re.sub(r'internal:has-text="([^"]+)"[si]?', r'has-text="\1"', sel)
        return sel
    except Exception:
        return "(?)"


def install_action_logging(steps_list):
    """Locatorメソッドにパッチを当てて操作を自動記録する。

    steps_list: 操作ログを追記するリスト（参照を保持すること）。
    二重パッチ防止のため _action_logged ガード付き。
    """
    if getattr(Locator, '_action_logged', False):
        return

    _orig_click = Locator.click
    _orig_fill = Locator.fill
    _orig_select = Locator.select_option
    _orig_dispatch = Locator.dispatch_event
    _orig_check = Locator.check
    _orig_uncheck = Locator.uncheck

    def _lc_click(self, **kw):
        extra = " (force=True)" if kw.get("force") else ""
        steps_list.append(f"[{_ts()}] クリック{extra}: {_desc(self)}")
        return _orig_click(self, **kw)

    def _lc_fill(self, value, **kw):
        steps_list.append(f"[{_ts()}] 入力 '{value}': {_desc(self)}")
        return _orig_fill(self, value, **kw)

    def _lc_select(self, value=None, **kw):
        steps_list.append(f"[{_ts()}] 選択 '{value}': {_desc(self)}")
        return _orig_select(self, value, **kw)

    def _lc_dispatch(self, type, event_init=None, **kw):
        steps_list.append(f"[{_ts()}] イベント発火 '{type}': {_desc(self)}")
        return _orig_dispatch(self, type, event_init, **kw)

    def _lc_check(self, **kw):
        steps_list.append(f"[{_ts()}] チェック: {_desc(self)}")
        return _orig_check(self, **kw)

    def _lc_uncheck(self, **kw):
        steps_list.append(f"[{_ts()}] チェック解除: {_desc(self)}")
        return _orig_uncheck(self, **kw)

    Locator.click = _lc_click
    Locator.fill = _lc_fill
    Locator.select_option = _lc_select
    Locator.dispatch_event = _lc_dispatch
    Locator.check = _lc_check
    Locator.uncheck = _lc_uncheck
    Locator._action_logged = True
