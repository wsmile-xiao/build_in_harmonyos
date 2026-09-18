#!/usr/bin/env python3
"""Consumer-side check for the packaged Jinja2 2.10.1 (R34: real API).

Everything below drives the shipped engine end to end — template parsing,
compilation, rendering, autoescaping and inheritance — plus the two
platform-specific contracts that make this pin work on Python 3.12:
the collections.abc patch and the MarkupSafe 1.1.1 soft_unicode import.
"""
import os
import sys

if len(sys.argv) > 1:
    sys.path.insert(0, os.path.abspath(sys.argv[1]))

import jinja2
import markupsafe

assert jinja2.__version__ == "2.10.1", jinja2.__version__
assert markupsafe.__version__ == "1.1.1", markupsafe.__version__

# --- the collections.abc patch is what makes the import above possible ------
# jinja2 2.10.1 shipped `from collections import Mapping` etc., removed in
# py3.10; assert the legacy names are no longer referenced anywhere we ship.
pkg_root = os.path.abspath(os.path.dirname(jinja2.__file__))
for root, _dirs, files in os.walk(pkg_root):
    for name in files:
        if not name.endswith(".py"):
            continue
        with open(os.path.join(root, name), encoding="utf-8") as fh:
            text = fh.read()
        assert "from collections import Mapping" not in text, name
        assert "from collections import MutableMapping" not in text, name
        assert "from collections import MutableSet" not in text, name

# --- core rendering ---------------------------------------------------------
tpl = jinja2.Template("Hello {{ name }}!")
assert tpl.render(name="Harmony") == "Hello Harmony!"

# autoescaping is on by default for Template? No — opt in explicitly and check
# escaping goes through markupsafe (this is the markupsafe integration point).
auto = jinja2.Environment(autoescape=True).from_string("{{ v }}")
assert auto.render(v="<b>&") == "&lt;b&gt;&amp;"
assert auto.render(v=markupsafe.Markup("<b>")) == "<b>"

# --- template inheritance + control flow ------------------------------------
env = jinja2.Environment(loader=jinja2.DictLoader({
    "base": "{% block body %}base{% endblock %}",
    "child": "{% extends 'base' %}{% block body %}"
             "{% for i in items %}{{ i }}{% if not loop.last %},{% endif %}"
             "{% endfor %}{% endblock %}",
}))
assert env.get_template("child").render(items=[1, 2, 3]) == "1,2,3"

# --- filters & tests --------------------------------------------------------
assert jinja2.Template("{{ 'a,b'|upper }}").render() == "A,B"
assert jinja2.Template("{{ 3 is odd }}").render() == "True"
assert jinja2.Template("{{ {'a': 1} is mapping }}").render() == "True"

# --- jinja2.utils import chain that needs markupsafe.soft_unicode -----------
from jinja2.utils import soft_unicode  # noqa: F401  (import-time contract)
assert jinja2.utils.soft_unicode(5) == "5"

print(f"jinja2 {jinja2.__version__} + markupsafe {markupsafe.__version__} "
      f"consumer API: PASS ({pkg_root})")
