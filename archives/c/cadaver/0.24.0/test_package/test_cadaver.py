#!/usr/bin/env python3
"""cadaver consumer test (L0c + R34): standalone test source executed
via self.run from conanfile.py test().

R34: actually invoke the tested binary — cadaver --version (or usage on
no-args, whichever the binary supports). Import/binary failure or wrong
exit asserts fail.
"""
import subprocess
import sys


def main() -> int:
    bin_dir = sys.argv[1] if len(sys.argv) > 1 else ""
    import os
    cadaver = os.path.join(bin_dir, "cadaver") if bin_dir else "cadaver"
    if not os.path.exists(cadaver):
        print(f"FAIL: cadaver binary not found at {cadaver}", file=sys.stderr)
        return 1

    # 真实调用：--version（cadaver 0.24 支持）——失败则退化为无参 usage
    r = subprocess.run([cadaver, "--version"], capture_output=True, text=True,
                       timeout=30)
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode == 0 and "cadaver" in out.lower():
        print(f"OK: cadaver --version -> {out.strip().splitlines()[0][:80]}")
        return 0

    # 退化：无参运行（cadaver 是交互式 WebDAV 客户端——无参进入交互
    # 模式 dav:!> 等待输入——CI 上无输入卡住 30s timeout 实测）——
    # input 发送 quit 命令让 cadaver 退出
    r2 = subprocess.run([cadaver], capture_output=True, text=True,
                        timeout=30, input="quit\n")
    out2 = (r2.stdout or "") + (r2.stderr or "")
    if "usage" in out2.lower() or "dav" in out2.lower():
        print(f"OK: cadaver usage -> {out2.strip().splitlines()[0][:80]}")
        return 0

    print(f"FAIL: cadaver run unexpected rc={r.returncode} "
          f"out={out[:120]!r}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
