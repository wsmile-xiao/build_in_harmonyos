#!/usr/bin/env python3
"""gast consumer test (R34): module importable from the packaged
site-packages + real AST parse/walk/unparse round-trip (not an import-only
smoke test).

The inner script parses real source into gast's version-neutral AST, checks
the node types it actually produces, walks the tree, and unparses back to
source — so a broken or empty package cannot pass.
"""
import os
import subprocess
import sys

SMOKE_PY = r'''
import sys
sys.path[0:0] = __import__("os").environ["PYTHONPATH"].split(":")

import gast

print("gast", gast.__version__)
assert gast.__version__ == "0.7.0", gast.__version__

# ---- 真实解析：源码 -> gast 版本无关 AST ----
tree = gast.parse("x = 1 + 2")
assert isinstance(tree, gast.Module), type(tree)
assigns = [n for n in gast.walk(tree) if isinstance(n, gast.Assign)]
assert len(assigns) == 1, len(assigns)
names = [n.id for n in gast.walk(tree) if isinstance(n, gast.Name)]
assert names == ["x"], names
assert isinstance(assigns[0].value, gast.BinOp), type(assigns[0].value)

# ---- 真实往返：unparse 回源码 ----
back = gast.unparse(tree).strip()
assert back == "x = 1 + 2", repr(back)

# ---- 真实 dump/ast_to_dict ----
dumped = gast.dump(tree)
assert isinstance(dumped, str) and "Assign" in dumped, dumped[:80]

print("OK: gast parsed/walked/unparsed:", back)
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    site = os.path.join(pkg, "lib", "python3.12", "site-packages")
    mod = os.path.join(site, "gast", "__init__.py")
    if not os.path.isfile(mod):
        print(f"FAIL: gast module missing: {mod}", file=sys.stderr)
        return 1
    env = dict(os.environ)
    env["PYTHONPATH"] = site
    py = sys.executable
    r = subprocess.run([py, "-c", SMOKE_PY], capture_output=True,
                       text=True, env=env)
    if r.returncode != 0:
        print(f"FAIL: gast AST API: {r.stderr}", file=sys.stderr)
        return 1
    print(r.stdout.strip())
    print("OK: gast module + real parse/walk/unparse works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
