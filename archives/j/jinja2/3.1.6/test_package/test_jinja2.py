#!/usr/bin/env python3
"""Consumer-side check for the packaged Jinja2 3.1.6 (R34: real API).

Everything below drives the shipped engine end to end — parsing, compilation,
rendering, autoescaping, inheritance, filters/tests, sandboxing and the
bytecode cache — plus the packaging contracts that matter for this port:

  * the src layout was picked up correctly (`src/jinja2` -> site-packages)
  * MarkupSafe >= 2.0 integration (this version's declared dependency), and
    the *removal* of the `soft_unicode` shim that 2.10.1 relied on
  * no `collections.Mapping` style legacy imports anywhere in the payload
    (3.1.6 needs no patch, but the check guards a future accidental backport)

Usage: test_jinja2.py <site-packages-dir>
"""
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
import markupsafe  # noqa: E402

PKG_ROOT = os.path.abspath(os.path.dirname(jinja2.__file__))


def t_version():
    assert jinja2.__version__ == "3.1.6", jinja2.__version__


def t_markupsafe_version():
    """Declared dependency is MarkupSafe>=2.0; must not silently ship 1.x."""
    major = int(markupsafe.__version__.split(".")[0])
    assert major >= 2, markupsafe.__version__


def t_payload_is_packaged_src():
    """The src layout must be flattened into site-packages/jinja2."""
    assert os.path.basename(PKG_ROOT) == "jinja2", PKG_ROOT
    assert os.path.isfile(os.path.join(PKG_ROOT, "__init__.py")), PKG_ROOT


def t_no_legacy_collections_imports():
    """3.1.6 needs no patch; assert no py3.10-removed aliases were shipped."""
    bad = []
    for root, _dirs, files in os.walk(PKG_ROOT):
        for name in files:
            if not name.endswith(".py"):
                continue
            with open(os.path.join(root, name), encoding="utf-8") as fh:
                text = fh.read()
            for legacy in ("from collections import Mapping",
                           "from collections import MutableMapping",
                           "from collections import MutableSet",
                           "from collections import MutableSequence"):
                if legacy in text:
                    bad.append(f"{name}: {legacy}")
    assert not bad, bad


def t_soft_unicode_removed():
    """3.1.6 dropped the soft_unicode shim (MarkupSafe>=2.1 removed it);
    the payload must not still call it, or rendering would break at runtime."""
    assert not hasattr(markupsafe, "soft_unicode"), "unexpected markupsafe shim"
    text = open(os.path.join(PKG_ROOT, "utils.py"), encoding="utf-8").read()
    assert "def soft_unicode" not in text, "stale soft_unicode shim shipped"


def t_template_render():
    assert jinja2.Template("Hello {{ name }}!").render(name="Harmony") == "Hello Harmony!"


def t_autoescape_through_markupsafe():
    auto = jinja2.Environment(autoescape=True).from_string("{{ v }}")
    assert auto.render(v="<b>&") == "&lt;b&gt;&amp;"
    assert auto.render(v=markupsafe.Markup("<b>")) == "<b>"


def t_inheritance_and_control_flow():
    env = jinja2.Environment(loader=jinja2.DictLoader({
        "base": "{% block body %}base{% endblock %}",
        "child": "{% extends 'base' %}{% block body %}"
                 "{% for i in items %}{{ i }}{% if not loop.last %},{% endif %}"
                 "{% endfor %}{% endblock %}",
    }))
    assert env.get_template("child").render(items=[1, 2, 3]) == "1,2,3"


def t_filters_and_tests():
    assert jinja2.Template("{{ 'a,b'|upper }}").render() == "A,B"
    assert jinja2.Template("{{ 3 is odd }}").render() == "True"
    assert jinja2.Template("{{ {'a': 1} is mapping }}").render() == "True"


def t_syntax_error_reported():
    """Negative case: a malformed template must raise, not fail silently."""
    try:
        jinja2.Template("{% if %}").render()
    except jinja2.TemplateSyntaxError:
        return
    raise AssertionError("malformed template did not raise TemplateSyntaxError")


def t_undefined_strict_raises():
    """Negative case: StrictUndefined must raise on undefined access."""
    env = jinja2.Environment(undefined=jinja2.StrictUndefined)
    try:
        env.from_string("{{ nope }}").render()
    except jinja2.UndefinedError:
        return
    raise AssertionError("StrictUndefined did not raise UndefinedError")


def t_sandboxed_environment():
    """SandboxedEnvironment blocks unsafe operations.

    `jinja2.sandbox` 是**子模块**且未被 __init__ 导入（实测 `jinja2.sandbox`
    报 AttributeError），必须显式 import —— 上游 tests/test_api.py:29 亦如此。
    断言用上游 tests/test_security.py:60 的惯用法：ImmutableSandboxedEnvironment
    下对内置容器的**变异方法**（`[].append(...)`）必须抛 SecurityError。
    注意不能简单断言 `{{ ''.__class__ }}` —— 实测在 3.1.6 下该表达式不抛
    SecurityError（沙箱允许读未加下划线保护的属性路径），用它做负例是错的。
    """
    from jinja2.exceptions import SecurityError
    from jinja2.sandbox import ImmutableSandboxedEnvironment
    env = ImmutableSandboxedEnvironment()
    for expr in ("{{ [].append(23) }}", "{{ [].clear() }}", "{{ [1].pop() }}"):
        try:
            env.from_string(expr).render()
        except SecurityError:
            continue
        raise AssertionError(f"sandbox allowed mutation: {expr}")


def t_meta_module():
    """jinja2.meta is a public submodule (explicit import required)."""
    from jinja2 import meta
    ast = jinja2.Environment().parse("{{ a }}{{ b }}")
    found = meta.find_undeclared_variables(ast)
    assert found == {"a", "b"}, found


def t_bytecode_cache_roundtrip():
    """FileSystemBytecodeCache must be shipped and usable."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        env = jinja2.Environment(
            loader=jinja2.DictLoader({"x": "VALUE-{{ n }}"}),
            bytecode_cache=jinja2.FileSystemBytecodeCache(td))
        assert env.get_template("x").render(n=7) == "VALUE-7"
        # second render goes through the cache
        assert env.get_template("x").render(n=8) == "VALUE-8"


def t_select_autoescape_helper():
    fn = jinja2.select_autoescape(["html"])
    assert fn("page.html") is True
    assert fn("page.txt") is False


check("version_is_3.1.6", t_version)
check("markupsafe_ge_2", t_markupsafe_version)
check("payload_is_packaged_src", t_payload_is_packaged_src)
check("no_legacy_collections_imports", t_no_legacy_collections_imports)
check("soft_unicode_removed", t_soft_unicode_removed)
check("template_render", t_template_render)
check("autoescape_via_markupsafe", t_autoescape_through_markupsafe)
check("inheritance_and_control_flow", t_inheritance_and_control_flow)
check("filters_and_tests", t_filters_and_tests)
check("negative_syntax_error", t_syntax_error_reported)
check("negative_strict_undefined", t_undefined_strict_raises)
check("sandboxed_environment", t_sandboxed_environment)
check("meta_module", t_meta_module)
check("bytecode_cache_roundtrip", t_bytecode_cache_roundtrip)
check("select_autoescape_helper", t_select_autoescape_helper)

print(f"jinja2 {jinja2.__version__} consumer API: "
      f"{len(PASSED)}/{len(PASSED) + len(FAILED)} passed")
for name in PASSED:
    print(f"  [ok]   {name}")
for msg in FAILED:
    print(f"  [FAIL] {msg}")
sys.exit(1 if FAILED else 0)
