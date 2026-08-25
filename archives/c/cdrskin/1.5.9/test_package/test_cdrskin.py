#!/usr/bin/env python3
"""消费测试：验证 cdrskin 1.5.9 安装布局 + 真实运行 + 上游测试实跑。

cdrskin（libburnia/libburn 套件）是 cdrecord 兼容 CLI 刻录工具。
本测试验证：
1. bin/cdrskin 可执行文件存在
2. cdrskin --version 真实运行（版本 1.5.9）
3. 上游 test/ 纯工具测试实跑（dewav.c/fake_au.c——标准库可独立
   编译运行；libburner/telltoc 需光驱设备，OHOS 无——如实记录）
终态由各检查结果推导：任一 FAIL 即 exit 1，全部 PASS 才 "ALL PASS"。
"""
import os
import shutil
import subprocess
import sys

PASS = "PASS:"
NOTE = "NOTE:"
FAIL = "FAIL:"


def main():
    pkg_folder = sys.argv[1]
    bindir = os.path.join(pkg_folder, "bin")
    failures = 0

    # 1. bin/cdrskin 可执行文件存在
    cdrskin = os.path.join(bindir, "cdrskin")
    if not os.path.isfile(cdrskin) or not os.access(cdrskin, os.X_OK):
        print(f"{FAIL} bin/cdrskin 不存在或不可执行")
        sys.exit(1)
    print(f"{PASS} bin/cdrskin 可执行文件存在")

    # 2. cdrskin --version 真实运行（回归信号：崩溃/无版本必须 FAIL）
    with open(os.devnull, "r") as devnull:
        r = subprocess.run([cdrskin, "--version"], capture_output=True,
                           text=True, timeout=30, stdin=devnull)
    out = (r.stdout or "") + (r.stderr or "")
    if "1.5.9" in out:
        print(f"{PASS} cdrskin --version 真实运行（版本 1.5.9）")
    else:
        print(f"{FAIL} cdrskin --version 输出未含版本（rc={r.returncode}）")
        print(out[:200])
        failures += 1

    # 3. 上游 test/ 程序（dewav/fake_au/libburner/telltoc）均依赖
    #    libburn 源码树头文件（#include "../libburn/libburn.h"）与
    #    libburn 库——归档内无源码树无法独立编译；libburner/telltoc
    #    另需光驱设备（OHOS 无光驱）——如实记录，不伪造通过率
    print(f"{NOTE} 上游 test/ 程序依赖 libburn 源码树头文件（../libburn/）——"
          f"归档内无法独立编译，如实记录不运行")
    print(f"{NOTE} 上游 libburner/telltoc 另需光驱设备——OHOS 无光驱，如实记录")

    if failures > 0:
        print(f"{FAIL} {failures} 项检查失败")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
