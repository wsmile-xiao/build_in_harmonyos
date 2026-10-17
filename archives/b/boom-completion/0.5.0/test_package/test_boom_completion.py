#!/usr/bin/env python3
"""boom-completion test_package 校验：断言 bash/zsh 补全产物存在且含关键内容。

用 Python 而非 shell（OHOS /system/bin/sh 对脚本语法兼容性差，
self.run("/bin/sh script") 曾报 "syntax error: unexpected '('"）。
"""
import os
import sys


def main():
    if len(sys.argv) < 2:
        print("FAIL: no package dir provided", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    bash = os.path.join(pkg, "share", "bash-completion", "completions", "boom")
    zsh = os.path.join(pkg, "share", "zsh", "site-functions", "_boom")

    if not os.path.isfile(bash):
        print(f"FAIL: bash completion missing: {bash}", file=sys.stderr)
        return 1
    if not os.path.isfile(zsh):
        print(f"FAIL: zsh completion missing: {zsh}", file=sys.stderr)
        return 1

    with open(bash, encoding="utf-8") as f:
        bdata = f.read()
    with open(zsh, encoding="utf-8") as f:
        zdata = f.read()
    if "_boom_complete" not in bdata:
        print("FAIL: bash completion lacks _boom_complete", file=sys.stderr)
        return 1
    if "#compdef boom" not in zdata:
        print("FAIL: zsh completion lacks #compdef boom", file=sys.stderr)
        return 1

    print("OK: boom-completion bash/zsh completion artifacts verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
