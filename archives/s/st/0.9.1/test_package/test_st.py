#!/usr/bin/env python3
"""st 消费者测试：真的执行打包出来的 st 二进制并校验版本串（R34 非空壳）。

- `st -v` 按上游设计走 x.c 的 die()：打印版本串后 exit(1)（x.c:2075），
  因此断言放在**输出**上，不把非 0 退出码当失败。
- 另外校验 ELF 可执行位与 `st -h` 的 usage 输出，确认二进制真能起来。
"""
import os
import subprocess
import sys

bindir = os.environ.get("ST_BINDIR")
if not bindir:
    print("ST_BINDIR 未设置（conan test() 必须注入）", file=sys.stderr)
    sys.exit(2)
st = os.path.join(bindir, "st")
if not os.path.isfile(st):
    print(f"打包产物缺失: {st}", file=sys.stderr)
    sys.exit(3)
if not os.access(st, os.X_OK):
    print(f"产物不可执行: {st}", file=sys.stderr)
    sys.exit(4)

p = subprocess.run([st, "-v"], capture_output=True, text=True)
out = (p.stdout or "") + (p.stderr or "")
print(f"[st -v] rc={p.returncode} out={out.strip()!r}")
if "0.9.1" not in out:
    print("版本串不含 0.9.1", file=sys.stderr)
    sys.exit(5)

p2 = subprocess.run([st, "-h"], capture_output=True, text=True)
out2 = (p2.stdout or "") + (p2.stderr or "")
print(f"[st -h] rc={p2.returncode} out={out2.strip()[:120]!r}")
if "usage" not in out2.lower():
    print("usage 输出缺失", file=sys.stderr)
    sys.exit(6)

print("PASS: st 0.9.1 消费者测试通过（真实执行二进制 + 版本串 + usage）")
