#!/usr/bin/env python3
"""bacula-client consumer test (L0c + R34: standalone test source executed
via self.run from conanfile.py test()).

bacula-client is the Bacula client toolset: bconsole (interactive console)
+ 9 management/test tools (bsmtp drivetype fstype testfind testls bregex
bwild bregtest bjoblist). bconsole connects to a Bacula Director at runtime
(absent on OHOS — environment limitation, honest). Static check + execution
attempt: verify each binary's presence/executable/ELF, and that it loads its
bundled shared libs (libbac/libbaccfg/libbacfind in <pkg>/lib, per RUNPATH)
and runs without a fatal error (R34). Each tool prints usage and exits 0-2
without a Director; 127 = missing shared lib (libs not bundled), 139/134 =
crash.

Usage: test_bacula_client.py <package-folder>
"""
import os
import subprocess
import sys

# 127=缺共享库 139=segv 134=abort 136=bus 137=core（shell 包装 $? 约定值）
# 列表参数直 exec 时信号终止 returncode 为负信号值（如 SIGSEGV→-11）
_FATAL = {127, 139, 134, 136, 137}
_TOOLS = ["bconsole", "bsmtp", "drivetype", "fstype", "testfind",
          "testls", "bregex", "bwild", "bregtest", "bjoblist"]


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <package-folder>", file=sys.stderr)
        return 2
    pkg = sys.argv[1]

    # R34 静态检查：10 个二进制存在 / 可执行 / ELF
    for t in _TOOLS:
        exe = os.path.join(pkg, "bin", t)
        if not os.path.isfile(exe):
            raise AssertionError(f"{t} binary missing: {exe}")
        if not os.access(exe, os.X_OK):
            raise AssertionError(f"{t} not executable: {exe}")
        with open(exe, "rb") as f:
            if f.read(4) != b"\x7fELF":
                raise AssertionError(f"{t} is not an ELF binary: {exe}")

    # R34 真实执行尝试：每个工具加载其共享库并运行（无 Director 时打印
    # usage / 退出 0-2）。stdin=DEVNULL 避免 bconsole 交互挂起。
    for t in _TOOLS:
        exe = os.path.join(pkg, "bin", t)
        try:
            r = subprocess.run([exe], stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, timeout=15)
        except subprocess.TimeoutExpired:
            raise AssertionError(f"{t} timed out (hang waiting for input)")
        if r.returncode < 0 or r.returncode in _FATAL:
            raise AssertionError(
                f"{t} fatal exit {r.returncode} (missing lib/crash): "
                f"{r.stderr[:120]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
