#!/usr/bin/env python3
"""beniget consumer test (R34): package importable from the packaged
site-packages + real def-use chain analysis (not an import-only smoke test).

The inner script exercises beniget's core capability for real: it parses
Python source into a gast AST, runs DefUseChains over it, and checks that
the chain for a known local variable was actually built.  This is exactly
what pythran (the downstream consumer) relies on, so an empty or broken
package cannot pass.
"""
import os
import subprocess
import sys

SMOKE_PY = r'''
import os
import sys

# 追加而非覆盖：beniget 运行期要 import gast（由 runenv 注入）
sys.path[0:0] = [p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p]

import gast
import beniget

print("beniget", beniget.__version__, "| gast", gast.__version__)
assert beniget.__version__ == "0.5.0", beniget.__version__

# ---- 真实 def-use 链分析 ----
src = (
    "def f(n):\n"
    "    total = 0\n"
    "    for i in range(n):\n"
    "        total = total + i\n"
    "    return total\n"
    "\n"
    "result = f(3)\n"
)
module = gast.parse(src)

duc = beniget.DefUseChains()
duc.visit(module)

# 收集所有定义名 -> 用名
defs = {}
for node in gast.walk(module):
    if isinstance(node, gast.Name):
        chain = duc.chains.get(node)
        if chain is not None:
            defs.setdefault(chain.name(), set())

used_names = set()
for node in gast.walk(module):
    if isinstance(node, gast.Name):
        ch = duc.chains.get(node)
        if ch is not None and ch.name() in ("total", "i", "n", "f", "result"):
            used_names.add(ch.name())

assert "total" in used_names, "def-use chain for 'total' missing: %s" % used_names
assert "i" in used_names, "def-use chain for 'i' missing: %s" % used_names
assert "f" in used_names, "def-use chain for 'f' missing: %s" % used_names
print("OK: DefUseChains built for", sorted(used_names))

# ---- 真实用途：找出 total 的定义所被使用的次数 ----
total_defs = []
for node in gast.walk(module):
    if isinstance(node, gast.Name) and node.id == "total" and isinstance(node.ctx, gast.Store):
        ch = duc.chains.get(node)
        if ch is not None:
            total_defs.append(len(ch.users()) if hasattr(ch, "users") else None)
assert total_defs, "no Store chain found for 'total'"
print("OK: 'total' has", len(total_defs), "definition(s)")

print("OK: beniget def-use analysis works")
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    site = os.path.join(pkg, "lib", "python3.12", "site-packages")
    mod = os.path.join(site, "beniget", "__init__.py")
    if not os.path.isfile(mod):
        print("FAIL: beniget module missing: %s" % mod, file=sys.stderr)
        return 1
    env = dict(os.environ)
    # 追加而非覆盖：beniget 顶层 import gast，而 gast 的 site-packages 由主配方的
    # runenv_info 挂在 PYTHONPATH 上（conanrun）。此前直接 `= site` 把它冲掉，
    # CI 实测报 `ModuleNotFoundError: No module named 'gast'`。
    env["PYTHONPATH"] = os.pathsep.join(
        [site] + [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p])
    py = sys.executable
    r = subprocess.run([py, "-c", SMOKE_PY], capture_output=True,
                       text=True, env=env)
    if r.returncode != 0:
        print("FAIL: beniget API: %s" % r.stderr, file=sys.stderr)
        return 1
    print(r.stdout.strip())
    print("OK: beniget module + real def-use analysis works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
