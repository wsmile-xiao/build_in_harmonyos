#!/usr/bin/env python3
"""Conan test_package for rich — R34 consumer verification.

HARD: the `rich` package files are present in site-packages and importable
(a real consumer: Console output + Table + Syntax highlight via pygments).
"""
import os
import subprocess
import sys

TEST_SCRIPT = r'''
import sys
sys.path.insert(0, "{site}")
import rich
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax

# 真实调用：Console 输出 + Table 渲染 + Syntax 高亮（pygments）
console = Console(force_terminal=True, width=40, file=open("/dev/null", "w"))
table = Table(title="test")
table.add_column("k")
table.add_row("v")
console.print(table)
syntax = Syntax("print('hi')", "python")
console.print(syntax)
print("OK: import + Console/Table/Syntax work")
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    lib_root = os.path.join(pkg, "lib")
    site = None
    for py in os.listdir(lib_root):
        cand = os.path.join(lib_root, py, "site-packages")
        if os.path.isdir(cand) and os.path.isdir(os.path.join(cand, "rich")):
            site = cand
            break
    if not site:
        print(f"FAIL: rich module not found under {lib_root}", file=sys.stderr)
        return 1

    # 1. HARD: rich 包核心文件存在 + 语法可编译
    rich_dir = os.path.join(site, "rich")
    required = ["__init__.py", "console.py", "table.py", "syntax.py"]
    missing = [f for f in required
               if not os.path.isfile(os.path.join(rich_dir, f))]
    if missing:
        print(f"FAIL: rich files missing: {missing}", file=sys.stderr)
        return 1
    for f in required:
        # 用内置 compile() 做语法检查（不落盘——py_compile 会在源码旁生成
        # __pycache__/*.pyc 污染包目录，review P3）
        with open(os.path.join(rich_dir, f), "r", encoding="utf-8") as fh:
            try:
                compile(fh.read(), f, "exec")
            except SyntaxError as e:
                print(f"FAIL: {f} syntax error: {e}", file=sys.stderr)
                return 1

    # 2. 真实消费调用（import + Console/Table/Syntax）
    r = subprocess.run(
        [sys.executable, "-c", TEST_SCRIPT.replace("{site}", site)],
        capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL: {r.stderr}", file=sys.stderr)
        return 1
    print(r.stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
