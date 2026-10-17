#!/usr/bin/env python3
"""消费测试：验证 cdda2wav 2024-03-21 安装布局 + 真实运行。

cdda2wav（schilytools 套件）是 CLI CD 音频抓取工具。本测试验证：
1. bin/cdda2wav 可执行文件存在
2. cdda2wav --version 真实运行（版本 2024-03-21）
3. 上游 schilytools 无独立测试目录（cdda2wav 运行需光驱/SCSI 设备
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

    # 1. bin/cdda2wav 可执行文件存在
    cdda2wav = os.path.join(bindir, "cdda2wav")
    if not os.path.isfile(cdda2wav) or not os.access(cdda2wav, os.X_OK):
        print(f"{FAIL} bin/cdda2wav 不存在或不可执行")
        sys.exit(1)
    print(f"{PASS} bin/cdda2wav 可执行文件存在")

    # 2. cdda2wav --version 真实运行（回归信号：崩溃/无版本必须 FAIL；
    #    returncode 必须为 0——仅输出含程序名但非零退出（usage/设备错误）
    #    不得误判 PASS，避免坏二进制假通过）
    with open(os.devnull, "r") as devnull:
        r = subprocess.run([cdda2wav, "--version"], capture_output=True,
                           text=True, timeout=30, stdin=devnull)
    out = (r.stdout or "") + (r.stderr or "")
    if (r.returncode == 0 and
            ("Cdda2wav" in out or "cdda2wav" in out or "Cdrecord" in out)
            and ("3.02" in out or "2024/03/18" in out or "2024/03/1" in out)):
        print(f"{PASS} cdda2wav --version 真实运行")
    else:
        print(f"{FAIL} cdda2wav --version 输出异常（rc={r.returncode}）")
        print(out[:200])
        failures += 1

    # 3. 上游 schilytools 无独立测试目录（cdda2wav 运行需光驱/SCSI
    #    设备——OHOS 无光驱，如实记录不伪造通过率）
    print(f"{NOTE} 上游 schilytools 无独立测试目录——cdda2wav 运行需"
          f"光驱/SCSI 设备（OHOS 无光驱），如实记录不运行")

    if failures > 0:
        print(f"{FAIL} {failures} 项检查失败")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
