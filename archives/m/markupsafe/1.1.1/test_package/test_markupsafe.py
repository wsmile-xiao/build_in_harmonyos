#!/usr/bin/env python3
"""Consumer-side check for the packaged markupsafe 1.1.1 (R34: real API).

Every assertion below exercises the shipped package's public API — no
print-only stub. The final block pins the contract that makes 1.1.1 the
required version for Jinja2 2.10.1: ``soft_unicode`` must be importable.
"""
import os
import sys

if len(sys.argv) > 1:
    sys.path.insert(0, os.path.abspath(sys.argv[1]))

import markupsafe
from markupsafe import Markup, escape, escape_silent, soft_unicode

pkg_root = os.path.abspath(os.path.dirname(markupsafe.__file__))
assert os.path.basename(pkg_root) == "markupsafe", pkg_root
assert markupsafe.__version__ == "1.1.1", markupsafe.__version__

# --- core escaping contract -------------------------------------------------
assert escape("<b>&") == "&lt;b&gt;&amp;"
assert escape(None) == "None"
assert escape_silent(None) == ""
assert Markup("<b>") + escape("&") == "<b>&amp;"
assert Markup("<x>").unescape() == "<x>"
assert Markup.escape("<i>") == "&lt;i&gt;"

# striptags() removes tags and then *unescapes* the remainder, so escaped
# input round-trips back to the raw markup text. Traced against the shipped
# 1.1.1 implementation (src/markupsafe/__init__.py):
#
#     def striptags(self):
#         stripped = u" ".join(_striptags_re.sub("", self).split())
#         return Markup(stripped).unescape()      # <-- unescape is the last step
#
# escape("<b>T</b>")            -> Markup('&lt;b&gt;T&lt;/b&gt;')
#   .sub(_striptags_re, "")     -> '&lt;b&gt;T&lt;/b&gt;'  (no literal tags left)
#   .split() / join             -> '&lt;b&gt;T&lt;/b&gt;'
#   Markup(...).unescape()      -> '<b>T</b>'              <-- expected below
#
# Hence the expectation is the RAW text, not the entity-escaped form.
# (A "escape-then-strip" implementation would instead yield '&lt;b&gt;T&lt;/b&gt;'.)
assert escape("<b>T</b>").striptags() == "<b>T</b>"
# ...whereas stripping raw markup does drop the tags:
assert Markup("<b>T</b>").striptags() == "T"

# --- Jinja2 2.10.1 contract -------------------------------------------------
# jinja2/utils.py:647 (`from markupsafe import Markup, escape, soft_unicode`).
# soft_unicode was removed in MarkupSafe 2.1 — its presence is the reason
# this pin exists, so assert it explicitly.
assert callable(soft_unicode)
assert soft_unicode(123) == "123"
assert soft_unicode(None) == "None"

print(f"markupsafe {markupsafe.__version__} consumer API: PASS ({pkg_root})")
