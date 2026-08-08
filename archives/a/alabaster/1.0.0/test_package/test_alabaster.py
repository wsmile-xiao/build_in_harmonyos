#!/usr/bin/env python3
"""Consumer test for alabaster 1.0.0 — import + theme API smoke test.

上游 sdist 无测试目录（纯 Python 主题包），由 test_package 补全消费者测试：
覆盖 import、版本、主题目录/模板文件完整性、theme.conf 配置、
Sphinx setup() 钩子、Pygments 样式类。
"""
import configparser
import os
import sys


def test_import_and_version():
    import alabaster

    assert alabaster.__version__ == "1.0.0", f"version mismatch: {alabaster.__version__}"
    assert alabaster.__version_info__ == (1, 0, 0)
    print(f"PASS: alabaster {alabaster.__version__} imported successfully")


def test_get_path():
    import alabaster

    theme_dir = alabaster.get_path()
    assert os.path.isdir(theme_dir), f"get_path() not a dir: {theme_dir}"
    # get_path() 返回的是上一级（含 alabaster/ 子目录的父目录），
    # 真正的主题目录在 alabaster/ 下
    pkg_dir = os.path.join(theme_dir, "alabaster")
    assert os.path.isfile(os.path.join(pkg_dir, "theme.conf")), "theme.conf missing"
    print(f"PASS: get_path() -> {theme_dir}")


def test_theme_templates_present():
    import alabaster

    pkg_dir = os.path.dirname(alabaster.__file__)
    for fname in (
        "theme.conf",
        "layout.html",
        "about.html",
        "navigation.html",
        "relations.html",
        "donate.html",
        "support.py",
    ):
        assert os.path.isfile(os.path.join(pkg_dir, fname)), f"{fname} missing"
    print("PASS: theme templates (layout/about/navigation/relations/donate) present")


def test_theme_conf():
    import alabaster

    pkg_dir = os.path.dirname(alabaster.__file__)
    parser = configparser.ConfigParser()
    parser.read(os.path.join(pkg_dir, "theme.conf"))
    assert parser.has_section("theme"), "theme.conf missing [theme] section"
    assert parser.has_section("options"), "theme.conf missing [options] section"
    theme = parser["theme"]
    assert "inherit" in theme, "theme.conf missing 'inherit' key"
    assert theme["inherit"] == "basic"
    print("PASS: theme.conf [theme]/[options] sections valid")


def test_setup_hook():
    """Sphinx setup() 钩子：用假 app 验证注册流程（不依赖 sphinx 安装）。"""
    import alabaster

    class FakeApp:
        def __init__(self):
            self.require_calls = []
            self.themes = {}
            self.connects = []

        def require_sphinx(self, ver):
            self.require_calls.append(ver)

        def add_html_theme(self, name, path):
            self.themes[name] = path

        def connect(self, event, callback):
            self.connects.append((event, callback))

    app = FakeApp()
    result = alabaster.setup(app)
    assert app.require_calls == ["6.2"], "require_sphinx not called with 6.2"
    assert "alabaster" in app.themes, "add_html_theme not called"
    assert any(
        ev == "html-page-context" for ev, _ in app.connects
    ), "html-page-context not connected"
    assert result.get("parallel_read_safe") is True
    print("PASS: setup() registers theme, requires Sphinx 6.2, connects html-page-context")


def test_update_context():
    """update_context 向 context 注入 alabaster 版本信息。"""
    import alabaster

    class FakeCfg:
        html_theme_options = {"show_powered_by": "true"}

    class FakeApp:
        config = FakeCfg()

    context = {}
    alabaster.update_context(FakeApp(), "index", "index.html", context, None)
    assert context.get("alabaster_version") == "1.0.0"
    assert context.get("show_sphinx") is True
    print("PASS: update_context() injects alabaster_version and show_powered_by")


def test_pygments_style():
    """support.py 的 Alabaster Pygments 样式类（需要 pygments，build 时已装）。"""
    from alabaster.support import Alabaster

    assert Alabaster.background_color == "#f8f8f8"
    assert "Comment" in str([str(k) for k in Alabaster.styles.keys()]) or len(Alabaster.styles) > 0
    print("PASS: alabaster.support.Alabaster style class defined")


if __name__ == "__main__":
    tests = [
        test_import_and_version,
        test_get_path,
        test_theme_templates_present,
        test_theme_conf,
        test_setup_hook,
        test_update_context,
        test_pygments_style,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
        except Exception as e:
            print(f"FAIL: {fn.__name__}: {e}", file=sys.stderr)
            failed += 1
    if failed:
        print(f"\n{failed} test(s) FAILED", file=sys.stderr)
        sys.exit(1)
    print("\nAll alabaster consumer tests passed.")
    sys.exit(0)
