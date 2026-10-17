#!/usr/bin/env python3
"""Consumer-side check for the packaged pathspec 0.6.0 (R34: real API).

Drives the shipped matcher end to end: gitwildmatch / gitignore semantics,
negation patterns, the PathSpec entry points and the GitWildMatchPattern
class. Also pins the py3.12 compatibility contract of pathspec/compat.py.

API notes for 0.6.0 (verified against the real package — the modern
``Pattern.compile`` helper does not exist in this release):
  * ``PathSpec.from_lines(pattern_factory, lines)`` → PathSpec
  * ``PathSpec.match_file(path)`` → bool
  * ``GitWildMatchPattern(pattern, include=None)`` with ``.include`` and
    ``.match(files)`` (a generator, not a bool)
"""
import os
import sys

if len(sys.argv) > 1:
    sys.path.insert(0, os.path.abspath(sys.argv[1]))

import pathspec
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

assert pathspec.__version__ == "0.6.0", pathspec.__version__

# --- gitwildmatch basics ----------------------------------------------------
spec = PathSpec.from_lines("gitwildmatch", ["*.py", "!test_*.py", "build/"])
assert spec.match_file("a.py") is True
assert spec.match_file("test_a.py") is False, "negation must win"
assert spec.match_file("build/x.txt") is True
assert spec.match_file("readme.md") is False

# --- gitignore semantics ----------------------------------------------------
gitignore = PathSpec.from_lines("gitignore", ["*.log", "/root-only.txt"])
assert gitignore.match_file("x.log") is True
assert gitignore.match_file("root-only.txt") is True
assert gitignore.match_file("sub/root-only.txt") is False  # anchored pattern

# --- match_files (bulk API) -------------------------------------------------
assert list(spec.match_files(["a.py", "readme.md"])) == ["a.py"]

# --- pattern class ----------------------------------------------------------
pat = GitWildMatchPattern("*.txt")
assert pat.include is True
assert list(pat.match(["notes.txt"])) == ["notes.txt"]
assert list(pat.match(["notes.md"])) == []

neg = GitWildMatchPattern("!test_*.py")
assert neg.include is False

# PathSpec keeps the compiled pattern objects and their include flag
assert isinstance(spec.patterns[0], GitWildMatchPattern)
assert spec.patterns[0].include is True

# --- py3.12 compatibility contract -----------------------------------------
# pathspec/compat.py must have resolved the ABC from collections.abc (the
# legacy collections.Container alias is a py<3.6 fallback only).
from pathspec import compat
assert compat.collection_type is not None
assert isinstance([], compat.collection_type)

print(f"pathspec {pathspec.__version__} consumer API: PASS")
