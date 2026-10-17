#!/usr/bin/env python3
"""Consumer-side check for the packaged markupsafe 3.0.3 (R34: real API).

Every assertion exercises the shipped package's public API — no print-only
stub, no import-only check. The final block pins the contract that makes 3.0.3
incompatible with the older Jinja2 2.10.1 pin: ``soft_unicode`` was **removed**
in MarkupSafe 2.1, so asserting its absence is the dividing line between the
Jinja2 2.x (needs markupsafe <= 2.0.1) and Jinja2 3.x (needs >= 2.1.1) eras.

The pure-Python mode is verified by **asserting the C accelerator is absent**
(``markupsafe._speedups`` must not be importable) — see the note on quote
entities below, which do NOT distinguish the two implementations.
"""
import os
import sys

if len(sys.argv) > 1:
    sys.path.insert(0, os.path.abspath(sys.argv[1]))

import markupsafe
from markupsafe import Markup, escape, escape_silent

pkg_root = os.path.abspath(os.path.dirname(markupsafe.__file__))
assert os.path.basename(pkg_root) == "markupsafe", pkg_root

# The imported copy must be the one under test. Without this, a host
# installation earlier/later on sys.path could silently be what gets validated.
if len(sys.argv) > 1:
    expected = os.path.abspath(os.path.join(sys.argv[1], "markupsafe"))
    assert pkg_root == expected, f"imported {pkg_root}, expected {expected}"

# NOTE: ``__version__`` is deliberately NOT asserted here.
#
# In 3.0.3 it is resolved lazily by ``__getattr__`` via
# ``importlib.metadata.version("markupsafe")``, which requires an installed
# ``markupsafe-*.dist-info``. This package ships only the importable
# ``markupsafe/`` directory (source-copy packaging), so on a clean machine the
# attribute raises. Measured in isolation (no site-packages, no .dist-info):
#
#     $ PYTHONPATH=<pkg>/markupsafe python3 -S -c \
#         "import markupsafe; print(markupsafe.__version__)"
#     PackageNotFoundError: No package metadata was found for markupsafe
#
# An earlier revision did assert it and appeared to pass only because the build
# host happened to have markupsafe installed (its .dist-info satisfied the
# lookup). The version contract is therefore pinned by the API assertions
# below. See knowledge/drafts/DRAFT-ohos-source-copy-python-no-dist-info-version-unavailable.

# --- core escaping contract -------------------------------------------------
assert escape("<b>&") == "&lt;b&gt;&amp;"
assert escape(None) == "None"
assert escape_silent(None) == ""
assert Markup("<b>") + escape("&") == "<b>&amp;"
assert Markup("<x>").unescape() == "<x>"
assert Markup.escape("<i>") == "&lt;i&gt;"

# --- pure-Python mode: the C accelerator must NOT be present ---------------
# Direct, unambiguous proof: this package deliberately ships no ``_speedups``
# module, so importing it has to fail. (Resolved inside the packaged
# ``markupsafe`` package, so a host installation cannot satisfy it.)
try:
    import markupsafe._speedups  # noqa: F401
    raise SystemExit(
        "FAIL: markupsafe._speedups is importable — the C accelerator was "
        "shipped, but this package is meant to deliver the pure-Python mode")
except ImportError:
    pass

# The fallback module must be the one carrying the implementation.
import markupsafe._native as _native  # noqa: E402

assert callable(_native._escape_inner), "_native._escape_inner missing"
assert _native._escape_inner("a<b") == "a&lt;b"

# Behaviour of the quote entities (kept as behaviour assertions only).
# NOTE: these do NOT prove which implementation is active — _speedups.c's
# DO_ESCAPE macro emits exactly the same entities (byte-written as
# '&','#','3','4',';' and '&','#','3','9',';'), so both paths yield &#34;/&#39;.
# The explicit _speedups import check above is what proves the pure-Python mode.
assert escape("'") == "&#39;", escape("'")
assert escape('"') == "&#34;", escape('"')

# --- striptags(): unescape first, then strip tags ---------------------------
# 3.0.3 implementation order (src/markupsafe/__init__.py):
#     value = str(self); strip comments; strip tags; unescape; normalise ws
assert Markup("<b>T</b>").striptags() == "T"
assert Markup("Main &raquo;\t<em>About</em>").striptags() == "Main \u00bb About"

# --- 3.x contract vs the older Jinja2 pin ----------------------------------
# `soft_unicode` was REMOVED in 2.1 (measured: 0 occurrences in 3.0.3's
# __init__.py). Its absence is exactly what makes Jinja2 >= 3.1 — and not the
# Jinja2 2.10.1 pin, which imports `soft_unicode` from jinja2/utils.py — the
# compatible consumer. If it ever reappears, the version-coexistence assumption
# in notes.md must be revisited.
assert not hasattr(markupsafe, "soft_unicode"), \
    "soft_unicode unexpectedly present — 3.0.3 should have removed it"

# `soft_str`, by contrast, is STILL PRESENT in 3.0.3 (defined at
# src/markupsafe/__init__.py:64) — it was NOT removed alongside soft_unicode.
# Asserted positively so a future removal is caught rather than assumed.
assert callable(markupsafe.soft_str), "soft_str should still exist in 3.0.3"
assert markupsafe.soft_str(None) == "None"
assert markupsafe.soft_str(123) == "123"

print(f"markupsafe consumer API: PASS ({pkg_root})")
