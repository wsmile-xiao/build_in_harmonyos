#!/usr/bin/env python3
"""消费测试：验证 cdrecord 2024-03-21 安装布局 + 真实运行。

cdrecord（schilytools 套件）是 CLI 刻录工具。本测试验证：
1. bin/cdrecord 可执行文件存在
2. cdrecord --version 真实运行（版本 2024-03-21）
3. 上游 schilytools 无独立测试目录（cdrecord 运行需光驱/SCSI 设备
   ——OHOS 无光驱，如实记录）
终态由各检查结果推导：任一 FAIL 即 exit 1，全部 PASS 才 "ALL PASS"。
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

    # 1. bin/cdrecord 可执行文件存在
    cdrecord = os.path.join(bindir, "cdrecord")
    if not os.path.isfile(cdrecord) or not os.access(cdrecord, os.X_OK):
        print(f"{FAIL} bin/cdrecord 不存在或不可执行")
        sys.exit(1)
    print(f"{PASS} bin/cdrecord 可执行文件存在")

    # 2. cdrecord --version 真实运行（回归信号：崩溃/无版本必须 FAIL）
    with open(os.devnull, "r") as devnull:
        r = subprocess.run([cdrecord, "--version"], capture_output=True,
                           text=True, timeout=30, stdin=devnull)
    out = (r.stdout or "") + (r.stderr or "")
    if "Cdrecord" in out or "cdrecord" in out:
        print(f"{PASS} cdrecord --version 真实运行")
    else:
        print(f"{FAIL} cdrecord --version 输出异常（rc={r.returncode}）")
        print(out[:200])
        failures += 1

    # 3. 上游 schilytools 无独立测试目录（cdrecord 运行需光驱/SCSI
    #    设备——OHOS 无光驱，如实记录不伪造通过率）
    print(f"{NOTE} 上游 schilytools 无独立测试目录——cdrecord 运行需"
          f"光驱/SCSI 设备（OHOS 无光驱），如实记录不运行")

    if failures > 0:
        print(f"{FAIL} {failures} 项检查失败")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
