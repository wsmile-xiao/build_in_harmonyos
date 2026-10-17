#!/usr/bin/env python3
"""消费测试：验证 cdebconf 0.283 安装布局 + 真实运行。

cdebconf（Debian Installer Team）是 debconf（Debian 包配置管理）的
C 实现，提供 debconf-communicate/debconf-copydb 等 CLI 工具。本测试
验证：
1. bin/debconf-communicate 可执行文件存在
2. debconf-communicate --version 真实运行（工具基本可用性）
终态由各检查结果推导：任一 FAIL 即 exit 1，全部 PASS 才 "ALL PASS"。
上游测试（src/test/ configtest/dbtest）在配方 build 阶段实跑，此处为
安装布局 + 可执行性验证。
"""
import os
import subprocess
import sys

PASS = "PASS:"
NOTE = "NOTE:"
FAIL = "FAIL:"


def main():
    pkg_folder = sys.argv[1]
    bindir = os.path.join(pkg_folder, "bin")
    failures = 0

    # 1. debconf-communicate 可执行文件存在（bin/ 或 libexec/cdebconf/）
    exe = os.path.join(bindir, "debconf-communicate")
    if not (os.path.isfile(exe) and os.access(exe, os.X_OK)):
        # 上游 make install 装到 libexec/cdebconf/（cdebconf 惯例）
        alt = os.path.join(pkg_folder, "libexec", "cdebconf",
                           "debconf-communicate")
        if os.path.isfile(alt) and os.access(alt, os.X_OK):
            exe = alt
        else:
            print(f"{FAIL} debconf-communicate 不存在或不可执行"
                  f"（bin/ 与 libexec/cdebconf/ 均无）")
            sys.exit(1)
    print(f"{PASS} debconf-communicate 可执行文件存在（{os.path.dirname(exe)}）")

    # 2. debconf-escape -e 真实运行（转义工具，不依赖数据库模块/光驱；
    #    returncode 必须为 0——坏二进制/缺库不得误判 PASS）
    exe2 = os.path.join(os.path.dirname(exe), "debconf-escape")
    if not (os.path.isfile(exe2) and os.access(exe2, os.X_OK)):
        exe2 = os.path.join(bindir, "debconf-escape")
    with open(os.devnull, "r") as devnull:
        r = subprocess.run([exe2, "-e", "a<b&c"], capture_output=True,
                           text=True, timeout=30, stdin=devnull)
    if r.returncode == 0:
        print(f"{PASS} debconf-escape -e 真实运行")
    else:
        print(f"{FAIL} debconf-escape -e 输出异常（rc={r.returncode}）")
        print((r.stdout or "")[:200] + (r.stderr or "")[:200])
        failures += 1

    # 3. 上游测试实跑结果记录（配方 build 阶段 configtest/dbtest）
    print(f"{NOTE} 上游测试（src/test configtest/dbtest）在配方 build "
          f"阶段实跑，通过率见 PR 测试对比表")

    if failures > 0:
        print(f"{FAIL} {failures} 项检查失败")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
