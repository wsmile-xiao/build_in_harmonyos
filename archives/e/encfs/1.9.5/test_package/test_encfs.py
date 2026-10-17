#!/usr/bin/env python3
"""消费测试：验证 encfs 1.9.5 安装布局 + 真实运行。

encfs（FUSE 加密文件系统）是 CLI 工具。本测试验证：
1. bin/encfs 可执行文件存在
2. encfs --version 真实运行（版本 1.9.5）
3. 上游 test/（Cipher_test 等用 gtest + 依赖 encfs 内部头文件，
   需源码树内编译）——归档内无法独立编译，如实记录
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

    # 1. bin/encfs 可执行文件存在
    encfs = os.path.join(bindir, "encfs")
    if not os.path.isfile(encfs) or not os.access(encfs, os.X_OK):
        print(f"{FAIL} bin/encfs 不存在或不可执行")
        sys.exit(1)
    print(f"{PASS} bin/encfs 可执行文件存在")

    # 2. encfs --version 真实运行（回归信号：崩溃/无版本必须 FAIL）
    with open(os.devnull, "r") as devnull:
        r = subprocess.run([encfs, "--version"], capture_output=True,
                           text=True, timeout=30, stdin=devnull)
    out = (r.stdout or "") + (r.stderr or "")
    if "1.9.5" in out:
        print(f"{PASS} encfs --version 真实运行（版本 1.9.5）")
    else:
        print(f"{FAIL} encfs --version 输出未含版本（rc={r.returncode}）")
        print(out[:200])
        failures += 1

    # 3. 上游 test/（Cipher_test/MemoryPool_test 用 gtest + 依赖 encfs
    #    内部头文件 encfs/BlockNameIO.h 等，需源码树内编译）——归档内
    #    无源码树无法独立编译，如实记录不伪造通过率
    print(f"{NOTE} 上游 test/ 用 gtest + 依赖 encfs 内部头文件——"
          f"归档内无法独立编译，如实记录不运行")

    if failures > 0:
        print(f"{FAIL} {failures} 项检查失败")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
