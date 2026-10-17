#!/usr/bin/env python3
"""Consumer end-to-end use case for the packaged libervia-templates
0.9.0-hg413 (R34 real API — runs the actual page-rendering flow, not
hollow assertions).

This is the **HarmonyOS-specific consumer use case** for the package: it
simulates a real frontend consumer that uses the packaged `sat_templates`
data to generate complete HTML pages through the full Jinja2 template
chain (base/base.html -> error/base.html, app, blog, login, form/field
macros, i18n `trans`, `script`/`icon`/`C` injection, `xmlattr`, block
inheritance), writes each generated page to disk as an artifact, and then
validates the produced artifacts are complete, well-formed pages.

Run with:  python3 test_consumer_e2e.py <site-packages-dir>
"""
import json
import os
import sys
import tempfile

if len(sys.argv) > 1:
    sys.path.insert(0, os.path.abspath(sys.argv[1]))

FAILED = []
PASSED = []


def check(name, fn):
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 — consumer test reports any failure
        FAILED.append(f"{name}: {type(exc).__name__}: {exc}")
    else:
        PASSED.append(name)


import jinja2  # noqa: E402
import sat_templates  # noqa: E402
from jinja2.ext import i18n  # noqa: E402

PKG_ROOT = os.path.abspath(os.path.dirname(sat_templates.__file__))
OUT_DIR = os.path.join(tempfile.gettempdir(), "libervia-templates-e2e")


class _Gidx:
    """Stateful id generator backing the templates' next_gidx/cur_gidx."""

    def __init__(self):
        self._ids = {}

    def next(self, name):
        cur = self._ids.get(name, 0) + 1
        self._ids[name] = cur
        return cur

    def cur(self, name):
        return self._ids.get(name, 1)


_gidx = _Gidx()


def _next_gidx(name):
    return str(_gidx.next(name))


def _cur_gidx(name):
    return str(_gidx.cur(name))


def _date_fmt(value, fmt="short"):
    if value is None:
        return ""
    return "recently" if fmt == "relative" else str(value)


class Script:
    """Libervia 运行时注入模板的 script 对象（消费者侧最小实现）。"""

    def __init__(self):
        self._included = []

    def include(self, name, *args):
        self._included.append(name)
        return ""

    def generate_scripts(self):
        return ""


class C:
    APP_NAME = "Libervia"
    KEY_LANG = "lang"


class S_C:
    PROFILE_AUTH_ERROR = "profile-auth-error"
    XMPP_AUTH_ERROR = "xmpp-auth-error"
    NO_REPLY = "no-reply"


def _icon(name, cls=""):
    return f'<span class="icon {cls}">{name}</span>'


def _icon_defs(*names):
    return '<svg xmlns="http://www.w3.org/2000/svg" style="display:none"></svg>'


class _Locale:
    def __init__(self, code, language_name):
        self.language = code
        self.language_name = language_name


class _Ident:
    def __init__(self, nicknames=(), avatar_basename=""):
        self.nicknames = list(nicknames)
        self.avatar_basename = avatar_basename


class _BlogItem:
    def __init__(self, item_id, title, content, author, author_jid,
                 published, language="en", tags=(), content_xhtml=None,
                 title_xhtml=None, comments_items_list=()):
        self.id = item_id
        self.title = title
        self.title_xhtml = title_xhtml
        self.content = content
        self.content_xhtml = content_xhtml
        self.author = author
        self.author_jid = author_jid
        self.published = published
        self.language = language
        self.tags = list(tags)
        self.comments_items_list = list(comments_items_list)


class _Notif:
    def __init__(self, level, message):
        self.level = level
        self.message = message


def make_env(templates_dir):
    """构造与真实 Libervia 前端一致的 Jinja2 环境（FileSystemLoader +
    i18n 扩展 + 模板依赖的 filters/globals）。"""
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(templates_dir),
        extensions=[i18n],
        autoescape=False,
    )
    env.filters.update(date_fmt=_date_fmt, next_gidx=_next_gidx,
                       cur_gidx=_cur_gidx)
    env.globals.update(
        script=Script(), C=C(), S_C=S_C(), icon=_icon, icon_defs=_icon_defs,
        _=lambda s, **kw: s.format(**kw) if kw else s,
        gettext=lambda s, **kw: s.format(**kw) if kw else s,
        ngettext=lambda s, p, n, **kw: ((p if n != 1 else s).format(**kw)
                                        if kw else (p if n != 1 else s)),
        media_path="/media", build_path="/build/", body_onload="",
        menu_fixed_top=False, current_page="", profile=False, login="",
        empty_password_allowed=False, csrf_token="test-csrf-token",
    )
    return env


def _render_to_file(theme, template_name, ctx, out_file):
    """渲染打包内真实模板 → 写入产物文件；任一步失败抛 AssertionError。"""
    tdir = os.path.join(PKG_ROOT, "templates", theme)
    if not os.path.isdir(tdir):
        raise AssertionError(f"theme templates dir missing: {tdir}")
    try:
        tpl = make_env(tdir).get_template(template_name)
    except Exception as exc:  # noqa: BLE001
        raise AssertionError(
            f"jinja2 failed to load {theme}/{template_name}: "
            f"{type(exc).__name__}: {exc}") from exc
    try:
        html = tpl.render(**ctx)
    except Exception as exc:  # noqa: BLE001
        raise AssertionError(
            f"jinja2 failed to render {theme}/{template_name}: "
            f"{type(exc).__name__}: {exc}") from exc
    with open(out_file, "w", encoding="utf-8") as fh:
        fh.write(html)
    return html


def _assert_complete_page(html, expected_title_fragment, expected_body_fragment,
                          check_footer=True):
    """校验生成的产物是完整页面（doctype/html/head/body/footer + 内容）。

    check_footer=False 用于 error/base.html 这类有意置空 footer 的页面
    （`{% block footer %}{% endblock %}`），其余完整页必须含 i18n footer。
    """
    assert html.lstrip().startswith("<!DOCTYPE html>"), "no doctype"
    assert "<html" in html and "</html>" in html, "html element incomplete"
    assert "<head>" in html and "</head>" in html, "head section missing"
    assert "<body" in html and "</body>" in html, "body section missing"
    assert "<title>" in html and "</title>" in html, "title missing"
    if expected_title_fragment:
        assert expected_title_fragment in html, "title fragment missing"
    if expected_body_fragment:
        assert expected_body_fragment in html, "body fragment missing"
    if check_footer:
        assert "Powered by Libervia" in html, "i18n footer missing"


# ── 端到端用例：完整页面渲染 + 产物落盘 + 产物校验 ───────────────────

def t_e2e_blog_page_default_theme():
    """default 主题：blog/articles.html 全链渲染（extends base/base.html +
    blog/item.html + avatar + 导航 + i18n + script 注入），写出产物并校验。"""
    out = os.path.join(OUT_DIR, "default-blog.html")
    item = _BlogItem(
        "urn:test:blog:1", "Hello Libervia", "This is the article body.",
        "alice@example.org", "alice@example.org", "2026-09-26",
        tags=("ohos",), content_xhtml="")
    ctx = {
        "blog_items": {"items": [item]},
        "main_menu": [("login", "/login"), ("blog", "/blog"),
                      ("chat", "/chat")],
        "locales": [_Locale("en", "English"), _Locale("fr", "Français")],
        "locale": _Locale("en", "English"),
        "identities": {"alice@example.org": _Ident(["Alice"], "")},
        "items_http_uri": {"urn:test:blog:1": "/blog/1"},
        "css_files": ["/media/libervia/default.css"],
        "css_files_noscript": [], "scripts": [],
        "notifications": [_Notif("info", "Welcome back!")],
    }
    html = _render_to_file("default", "blog/articles.html", ctx, out)
    assert os.path.isfile(out) and os.path.getsize(out) > 0, "artifact missing"
    _assert_complete_page(html, "Hello Libervia", "This is the article body.")
    assert "Powered by Libervia" in html
    assert 'class="menu main_menu"' in html, "main menu not rendered"


def t_e2e_login_page_default_theme():
    """default 主题：login/login.html 全链渲染（extends base/base.html +
    input/form.html + input/field.html + next_gidx 状态 id + i18n）。"""
    out = os.path.join(OUT_DIR, "default-login.html")
    ctx = {
        "login": "alice",
        "main_menu": [("login", "/login")],
        "locales": [_Locale("en", "English")],
        "locale": _Locale("en", "English"),
        "css_files": ["/media/libervia/default.css"],
        "css_files_noscript": [], "scripts": [],
    }
    html = _render_to_file("default", "login/login.html", ctx, out)
    assert os.path.isfile(out) and os.path.getsize(out) > 0, "artifact missing"
    _assert_complete_page(html, "Libervia login", None)
    assert "name=\"login\"" in html, "login field missing"
    assert "type=\"password\"" in html, "password field missing"
    assert "type=\"submit\"" in html, "submit button missing"


def t_e2e_error_pages_both_themes():
    """两套主题 error/404.html + error/401.html 全链渲染为完整页面。"""
    for theme in ("default", "bulma"):
        for code in (404, 401):
            out = os.path.join(OUT_DIR, f"{theme}-error-{code}.html")
            html = _render_to_file(theme, f"error/{code}.html",
                                   {"error_code": code}, out)
            assert os.path.isfile(out) and os.path.getsize(out) > 0, \
                "artifact missing"
            _assert_complete_page(html, f"Error {code}", None,
                                  check_footer=False)
            if theme == "bulma":
                assert "bulma.min.css" in html, "bulma css missing"


def t_e2e_app_page_default_theme():
    """default 主题：app/app.html（extends base/base.html 的最小完整页）。"""
    out = os.path.join(OUT_DIR, "default-app.html")
    ctx = {
        "css_files": ["/media/libervia/default.css"],
        "css_files_noscript": [], "scripts": [],
        "locales": [], "locale": _Locale("en", "English"),
    }
    html = _render_to_file("default", "app/app.html", ctx, out)
    assert os.path.isfile(out) and os.path.getsize(out) > 0, "artifact missing"
    _assert_complete_page(html, "Libervia", "web application")


# ── 负例：产物契约（settings.json 合法 + 模板缺失必须报错） ───────────

def t_settings_json_valid():
    path = os.path.join(PKG_ROOT, "templates", "default", "settings.json")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    assert isinstance(data, dict), type(data)


def t_missing_template_raises():
    try:
        _render_to_file("default", "error/not_exist.html", {"error_code": 404},
                        os.path.join(OUT_DIR, "should-not-exist.html"))
    except AssertionError:
        return
    raise AssertionError("missing template did not raise")


def t_i18n_data_shipped():
    mo = os.path.join(PKG_ROOT, "i18n", "fr", "LC_MESSAGES", "sat.mo")
    assert os.path.isfile(mo), f"missing: {mo}"
    po = os.path.join(PKG_ROOT, "i18n", "sk", "LC_MESSAGES", "sat.po")
    assert os.path.isfile(po), f"missing: {po}"


os.makedirs(OUT_DIR, exist_ok=True)

check("e2e_blog_page_default_theme", t_e2e_blog_page_default_theme)
check("e2e_login_page_default_theme", t_e2e_login_page_default_theme)
check("e2e_error_pages_both_themes", t_e2e_error_pages_both_themes)
check("e2e_app_page_default_theme", t_e2e_app_page_default_theme)
check("settings_json_valid", t_settings_json_valid)
check("negative_missing_template_raises", t_missing_template_raises)
check("i18n_data_shipped", t_i18n_data_shipped)

print(f"libervia-templates {sat_templates.__version__} consumer E2E: "
      f"{len(PASSED)}/{len(PASSED) + len(FAILED)} passed")
for name in PASSED:
    print(f"  [ok]   {name}")
for msg in FAILED:
    print(f"  [FAIL] {msg}")
sys.exit(1 if FAILED else 0)
