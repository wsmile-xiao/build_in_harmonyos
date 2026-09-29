#!/usr/bin/env python3
"""Consumer-side functional tests for the packaged libervia-templates
0.9.0-hg413 (R34: real API, no hollow test).

上游 hg413 快照**无测试套件**（build() 内已真实检查：无 tests/ 目录、
无 test_*.py、无 tox/pytest 配置），因此这里补充的消费者功能测试就是本
版本的实质测试。内容：

  * import sat_templates 校验 __version__（上游真实值 "0.9.0.dev0"）
  * 校验打包布局：VERSION / templates/default / templates/bulma / i18n .mo
  * 用 jinja2 的 FileSystemLoader 渲染**打包内实际模板**，断言输出：
      - default 主题 error/404.html、error/401.html
        （全链：extends error/base.html -> base/base.html ->
          components/common.html + i18n trans + script 注入 + xmlattr）
      - bulma 主题 error/404.html、error/401.html
        （同上，且含 bulma.min.css 资源引用）
  * 校验运行时依赖 jinja2 版本 = 3.1.6
  * 校验 templates/default/settings.json 为合法 JSON

Usage: test_libervia_templates.py <site-packages-dir>
"""
import json
import os
import sys

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


class Script:
    """Libervia 运行时向模板注入的 script 对象（测试侧的最小等价实现）。"""

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


def _icon(name, cls=""):
    return f'<span class="icon {cls}">{name}</span>'


def _icon_defs(*names):
    return ""


def make_env(templates_dir):
    """构造与 Libervia 前端用法一致的 Jinja2 环境（FileSystemLoader +
    i18n 扩展 + 模板依赖的 script/C/icon/_ 等全局对象）。"""
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(templates_dir),
        extensions=[i18n],
        autoescape=False,
    )
    env.globals.update(
        script=Script(),
        C=C(),
        icon=_icon,
        icon_defs=_icon_defs,
        _=lambda s, **kw: s.format(**kw) if kw else s,
        gettext=lambda s, **kw: s.format(**kw) if kw else s,
        ngettext=lambda s, p, n, **kw: ((p if n != 1 else s).format(**kw)
                                        if kw else (p if n != 1 else s)),
        media_path="/media",
        build_path="/build/",
        css_files=[],
        css_files_noscript=[],
        scripts=[],
        locales=[],
        locale="en",
        main_menu=None,
        body_onload="",
        menu_fixed_top=False,
        current_page="",
    )
    return env


def _render(theme, template_name, error_code):
    """渲染打包内真实模板，返回输出文本；失败抛 AssertionError。"""
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
        return tpl.render(error_code=error_code)
    except Exception as exc:  # noqa: BLE001
        raise AssertionError(
            f"jinja2 failed to render {theme}/{template_name}: "
            f"{type(exc).__name__}: {exc}") from exc


# ── 打包契约 ──────────────────────────────────────────────────────────

def t_version():
    assert sat_templates.__version__ == "0.9.0.dev0", sat_templates.__version__


def t_jinja2_dependency_version():
    """运行时依赖（jinja2/3.1.6）必须被解析，不能静默降级。"""
    assert jinja2.__version__ == "3.1.6", jinja2.__version__


def t_payload_is_packaged_sat_templates():
    assert os.path.basename(PKG_ROOT) == "sat_templates", PKG_ROOT
    assert os.path.isfile(os.path.join(PKG_ROOT, "__init__.py")), PKG_ROOT


def t_version_file_shipped():
    assert os.path.isfile(os.path.join(PKG_ROOT, "VERSION")), "VERSION missing"


def t_both_themes_shipped():
    for theme in ("default", "bulma"):
        base = os.path.join(PKG_ROOT, "templates", theme, "base", "base.html")
        assert os.path.isfile(base), f"missing: {base}"


def t_settings_json_valid():
    path = os.path.join(PKG_ROOT, "templates", "default", "settings.json")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    assert isinstance(data, dict), type(data)


def t_i18n_data_shipped():
    mo = os.path.join(PKG_ROOT, "i18n", "fr", "LC_MESSAGES", "sat.mo")
    assert os.path.isfile(mo), f"missing: {mo}"
    po = os.path.join(PKG_ROOT, "i18n", "sk", "LC_MESSAGES", "sat.po")
    assert os.path.isfile(po), f"missing: {po}"


# ── 真实模板渲染（全链：extends base + i18n + script 注入） ─────────────

def t_render_default_404():
    out = _render("default", "error/404.html", 404)
    assert "<!DOCTYPE html>" in out, out[:200]
    assert "<title>Error 404</title>" in out, out[:400]
    assert "Not Found" in out, out


def t_render_bulma_404():
    out = _render("bulma", "error/404.html", 404)
    assert "<!DOCTYPE html>" in out, out[:200]
    assert "bulma.min.css" in out, out[:400]
    assert "Not Found" in out, out


def t_render_default_401():
    out = _render("default", "error/401.html", 401)
    assert "<title>Error 401</title>" in out, out[:400]
    assert "Unauthorized" in out, out


def t_render_bulma_401():
    out = _render("bulma", "error/401.html", 401)
    assert "<title>Error 401</title>" in out, out[:400]
    assert "Unauthorized" in out, out


# ── 负例：模板缺失必须报错（确保渲染真的走了真实文件） ─────────────────

def t_render_missing_template_raises():
    try:
        _render("default", "error/not_exist.html", 404)
    except AssertionError:
        return
    raise AssertionError("missing template did not raise")


check("version_is_0.9.0.dev0", t_version)
check("jinja2_dependency_is_3.1.6", t_jinja2_dependency_version)
check("payload_is_packaged_sat_templates", t_payload_is_packaged_sat_templates)
check("version_file_shipped", t_version_file_shipped)
check("both_themes_shipped", t_both_themes_shipped)
check("settings_json_valid", t_settings_json_valid)
check("i18n_data_shipped", t_i18n_data_shipped)
check("render_default_404", t_render_default_404)
check("render_bulma_404", t_render_bulma_404)
check("render_default_401", t_render_default_401)
check("render_bulma_401", t_render_bulma_401)
check("negative_missing_template_raises", t_render_missing_template_raises)

print(f"libervia-templates {sat_templates.__version__} consumer tests: "
      f"{len(PASSED)}/{len(PASSED) + len(FAILED)} passed")
for name in PASSED:
    print(f"  [ok]   {name}")
for msg in FAILED:
    print(f"  [FAIL] {msg}")
sys.exit(1 if FAILED else 0)
