#!/usr/bin/env python3
"""Consumer smoke test for the packaged Pygments module."""

import io

import pygments
import pygments.cmdline
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer
from pygments.lexers import get_lexer_by_name


def main():
    assert pygments.__version__ == "2.20.0"

    code = "def hello():\n    return 'harmony'\n"
    lexer = get_lexer_by_name("python")
    assert isinstance(lexer, PythonLexer)

    html = highlight(code, lexer, HtmlFormatter())
    assert "<div" in html or "<pre" in html
    assert "def" in html

    tokens = list(lexer.get_tokens(code))
    assert len(tokens) >= 5
    assert tokens[0][1] == "def"

    # CLI-style entry via python -m pygments: -V mode avoids stdin/stdout
    # binary-buffer requirements and returns 0 on success.
    rc = pygments.cmdline.main(["pygmentize", "-V"])
    assert rc == 0

    # Ensure the tested module comes from the Conan package, not a
    # system-site pygments (e.g. one pulled in by pytest).
    assert ".conan2" in pygments.__file__, f"unexpected pygments path: {pygments.__file__}"

    print("pygments 2.20.0 ok")


if __name__ == "__main__":
    main()
