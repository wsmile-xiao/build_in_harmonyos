#!/usr/bin/env python3
"""Consumer-side check for the packaged pycparser 3.0 (R34: real API).

Every assertion exercises the shipped package's public API — parsing real C
source, walking the resulting AST, and regenerating C from it. No print-only
stub, no import-only check.

Two upstream quirks are pinned deliberately:

* ``pycparser.__version__`` is the string ``"3.00"`` while the distribution
  version is ``3.0`` — asserting the real value documents the mismatch instead
  of leaving it to chance.
* ``parse()`` returns a ``FileAST`` whose ``ext`` list holds the top-level
  declarations; ``CParser`` is re-exported at package top level.
"""
import os
import sys

if len(sys.argv) > 1:
    sys.path.insert(0, os.path.abspath(sys.argv[1]))

import pycparser
from pycparser import c_ast, c_generator, c_parser

pkg_root = os.path.abspath(os.path.dirname(pycparser.__file__))
assert os.path.basename(pkg_root) == "pycparser", pkg_root

# Upstream reports "3.00" (three chars) although the distribution is 3.0.
assert pycparser.__version__ == "3.00", pycparser.__version__
assert pycparser.__all__ == ["c_lexer", "c_parser", "c_ast"], pycparser.__all__

# --- CParser is re-exported at package level --------------------------------
assert pycparser.CParser is c_parser.CParser

# --- parse a real translation unit ------------------------------------------
parser = c_parser.CParser()
src = """
typedef unsigned long size_t;

static int add(int a, int b) {
    return a + b;
}

int main(void) {
    int x = add(1, 2);
    return x;
}
"""
ast = parser.parse(src)
assert isinstance(ast, c_ast.FileAST), type(ast).__name__

# Two top-level declarations: the typedef and the static function + main
# (main and add are both FuncDef in ext).
kinds = [type(n).__name__ for n in ast.ext]
assert "Typedef" in kinds, kinds
assert kinds.count("FuncDef") == 2, kinds

funcs = {n.decl.name: n for n in ast.ext if isinstance(n, c_ast.FuncDef)}
assert set(funcs) == {"add", "main"}, set(funcs)
assert funcs["add"].decl.type.args is not None
# `static int` -> the storage class is recorded on the declarator type
assert funcs["add"].decl.storage == ["static"], funcs["add"].decl.storage

# --- AST node types reachable from the parsed body --------------------------
body = funcs["add"].body
assert isinstance(body, c_ast.Compound), type(body).__name__
assert len(body.block_items) == 1
assert isinstance(body.block_items[0], c_ast.Return)
assert isinstance(body.block_items[0].expr, c_ast.BinaryOp)
assert body.block_items[0].expr.op == "+"

# --- CGenerator round-trip --------------------------------------------------
gen = c_generator.CGenerator()
out = gen.visit(ast)
assert "int add(int a, int b)" in out, out
assert "return a + b;" in out, out
assert "int main(void)" in out, out

# --- ParseError on malformed input ------------------------------------------
try:
    parser.parse("int main( { return 0; }")
    raise SystemExit("FAIL: ParseError not raised for malformed C source")
except Exception as e:
    # pycparser raises its own ParseError; accept any parse failure but make
    # sure it is the parser's, not something unrelated (e.g. a missing module).
    assert type(e).__name__ == "ParseError", f"{type(e).__name__}: {e}"

print(f"pycparser {pycparser.__version__} consumer API: PASS ({pkg_root})")
