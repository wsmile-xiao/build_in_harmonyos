#!/usr/bin/env python3
"""Deterministic consumer checks for the packaged Pygments API and CLI."""

import os
from pathlib import Path
import subprocess
import sys

import pygments
from pygments import highlight
from pygments.formatters import HtmlFormatter, TerminalFormatter
from pygments.lexers import (
    PythonLexer,
    get_lexer_by_name,
    get_lexer_for_filename,
)
from pygments.styles import get_style_by_name
from pygments.token import Keyword, Name


checks = 0


def check(condition, message):
    global checks
    if not condition:
        raise AssertionError(message)
    checks += 1


source = "def greet(name):\n    return f'Hello {name}'\n"
lexer = get_lexer_by_name("python")
tokens = list(lexer.get_tokens_unprocessed(source))
cli_env = os.environ.copy()
cli_env["PYTHONUTF8"] = "1"

check(pygments.__version__ == "2.20.0", "version mismatch")
check(isinstance(lexer, PythonLexer), "Python lexer lookup failed")
check(lexer.name == "Python", "lexer name mismatch")
check(any(token in Keyword and value == "def" for _, token, value in tokens),
      "def keyword token missing")
check(any(token in Name.Function and value == "greet" for _, token, value in tokens),
      "function token missing")
check("".join(value for _, _, value in tokens) == source, "token round trip failed")

html = highlight(source, lexer, HtmlFormatter(nowrap=True))
check('<span class="k">def</span>' in html, "HTML keyword markup missing")
check('<span class="nf">greet</span>' in html, "HTML function markup missing")
check("<pre>" not in html, "nowrap formatter unexpectedly emitted pre")

terminal = highlight(source, lexer, TerminalFormatter())
check("\x1b[" in terminal, "terminal formatter emitted no ANSI sequence")
check("greet" in terminal, "terminal formatter lost source text")

filename_lexer = get_lexer_for_filename("example.py", source)
check(isinstance(filename_lexer, PythonLexer), "filename lexer lookup failed")
monokai = get_style_by_name("monokai")
check(monokai.name == "monokai", "style lookup failed")

module_run = subprocess.run(
    [sys.executable, "-m", "pygments", "-V"],
    capture_output=True,
    text=True,
    check=False,
    env=cli_env,
)
check(module_run.returncode == 0, "module CLI version failed")
check("Pygments version 2.20.0" in module_run.stdout,
      "module CLI version mismatch")

command = None
for path_entry in os.environ.get("PATH", "").split(os.pathsep):
    candidate = Path(path_entry) / "pygmentize"
    if candidate.is_file():
        command = candidate
        break

check(command is not None, "packaged pygmentize command not found")
entry_version = subprocess.run(
    [sys.executable, str(command), "-V"],
    capture_output=True,
    text=True,
    check=False,
    env=cli_env,
)
check(entry_version.returncode == 0, "packaged CLI version failed")
check("Pygments version 2.20.0" in entry_version.stdout,
      "packaged CLI version mismatch")

entry_highlight = subprocess.run(
    [sys.executable, str(command), "-l", "python", "-f", "html", "-O", "nowrap"],
    input=source,
    capture_output=True,
    text=True,
    check=False,
    env=cli_env,
)
check(entry_highlight.returncode == 0, "packaged CLI highlight failed")
check('<span class="k">def</span>' in entry_highlight.stdout,
      "packaged CLI output mismatch")

expected_checks = 20
if checks != expected_checks:
    raise AssertionError(
        f"consumer assertion count mismatch: expected {expected_checks}, got {checks}"
    )

print(
    "PASS: Pygments packaged API and CLI consumer test "
    f"({checks}/{expected_checks} assertions)"
)
