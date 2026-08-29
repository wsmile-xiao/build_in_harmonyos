#!/usr/bin/env python3
"""消费测试：验证 calceph 5.0.0 安装布局 + 库可用。

calceph（IMCCE）是天体历表读取库（library 包）。本测试验证：
1. lib/libcalceph.a 库文件存在
2. include/calceph.h 头文件存在
3. 编译链接并运行最小 consumer（调用 calceph_getmaxsupportedorder）——
   证明库可被实际链接和调用，避免空壳测试（R34）
终态由各检查结果推导：任一 FAIL 即 exit 1，全部 PASS 才 "ALL PASS"。
上游测试（tests/ 114 个 C 测试）在配方 build 阶段 ctest 实跑，此处为消费验证。
"""
import os
import shutil
import subprocess
import sys
import tempfile

PASS = "PASS:"
NOTE = "NOTE:"
FAIL = "FAIL:"


def main():
    pkg_folder = sys.argv[1]
    failures = 0

    # 1. lib/libcalceph 库文件存在
    libdir = os.path.join(pkg_folder, "lib")
    lib = None
    for cand in ("libcalceph.a", "libcalceph.so"):
        if os.path.isfile(os.path.join(libdir, cand)):
            lib = os.path.join(libdir, cand)
            break
    if lib:
        print(f"{PASS} libcalceph 库文件存在（{os.path.basename(lib)}）")
    else:
        print(f"{FAIL} libcalceph 库文件缺失")
        failures += 1

    # 2. include/calceph.h 头文件存在
    hdr = os.path.join(pkg_folder, "include", "calceph.h")
    if os.path.isfile(hdr):
        print(f"{PASS} include/calceph.h 头文件存在")
    else:
        print(f"{FAIL} calceph.h 头文件缺失")
        failures += 1

    # 3. 编译链接并运行 consumer.c（调用 calceph_getmaxsupportedorder）——
    #    证明 libcalceph 可被实际链接和调用（R34 非空壳）。编译或运行
    #    任一失败即 FAIL，避免"坏包放行"的假阳性门禁。
    test_dir = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(test_dir, "consumer.c")
    out_bin = os.path.join(tempfile.gettempdir(), "calceph_consumer.out")
    cc = ""
    for cand in ("/data/service/hnp/bin/clang",
                 "/storage/Users/currentUser/usr/local/bin/clang",
                 os.environ.get("CC") or "",
                 shutil.which("clang") or ""):
        if cand and os.path.isfile(cand):
            cc = cand
            break
    if not cc:
        print(f"{FAIL} clang 不在 PATH——consumer 编译跳过，核心链接检查未执行")
        failures += 1
    else:
        r = subprocess.run(
            [cc, src, "-o", out_bin,
             "-I", os.path.join(pkg_folder, "include"),
             "-L", libdir, "-lcalceph"],
            capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            print(f"{FAIL} consumer 编译链接失败（rc={r.returncode}）")
            print((r.stderr or "")[:300])
            failures += 1
        else:
            run = subprocess.run([out_bin], capture_output=True, text=True,
                                 timeout=30)
            if run.returncode == 0:
                print(f"{PASS} consumer 编译链接并运行成功"
                      f"（{run.stdout.strip() or ''}）")
            else:
                print(f"{FAIL} consumer 运行失败（rc={run.returncode}）")
                print((run.stdout or "")[:200] + (run.stderr or "")[:200])
                failures += 1

    # 上游测试（tests/ 114 个 C 测试）在配方 build 阶段 ctest 实跑，
    # 通过率见 PR 测试对比表——此处为消费验证，不再重复 NOTE

    if failures > 0:
        print(f"{FAIL} {failures} 项检查失败")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()