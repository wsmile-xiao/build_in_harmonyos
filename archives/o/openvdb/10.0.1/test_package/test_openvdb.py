#!/usr/bin/env python3
"""消费测试：验证 openvdb 10.0.1 安装布局 + 库链接 + 头文件可用。

openvdb（稀疏体积库）是 library 包。本测试验证：
1. lib/libopenvdb 库文件存在（.a 或 .so）
2. include/openvdb/openvdb.h 头文件存在
3. 编译一个最小 consumer（openvdb 头 + 创建 FloatGrid）真实链接
终态由各检查结果推导：任一 FAIL 即 exit 1，全部 PASS 才 "ALL PASS"。
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

    # 1. lib/libopenvdb 库文件存在
    libdir = os.path.join(pkg_folder, "lib")
    lib = None
    for cand in ("libopenvdb.a", "libopenvdb.so"):
        if os.path.isfile(os.path.join(libdir, cand)):
            lib = os.path.join(libdir, cand)
            break
    if lib:
        print(f"{PASS} libopenvdb 库文件存在（{os.path.basename(lib)}）")
    else:
        print(f"{FAIL} libopenvdb 库文件缺失")
        failures += 1

    # 2. include/openvdb/openvdb.h 头文件存在
    hdr = os.path.join(pkg_folder, "include", "openvdb", "openvdb.h")
    if os.path.isfile(hdr):
        print(f"{PASS} include/openvdb/openvdb.h 头文件存在")
    else:
        print(f"{FAIL} openvdb.h 头文件缺失")
        failures += 1

    # 3. 编译最小 consumer 真实链接（openvdb 头 + 创建 FloatGrid）
    #    openvdb 头依赖 tbb/boost/zlib——额外 include 路径由
    #    test_package/conanfile.py 从依赖收集传入（sys.argv[2:]）
    test_dir = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(test_dir, "consumer.cpp")
    # consumer.out 写临时目录（P3：不污染源码目录/归档）
    out_bin = os.path.join(tempfile.gettempdir(), "openvdb_consumer.out")
    extra_includes = []
    for arg in sys.argv[2:]:
        if arg.startswith("-I") or arg.startswith("-L") or arg.startswith("-l"):
            extra_includes.append(arg)
        elif arg.startswith("--include="):
            extra_includes.append("-I" + arg[len("--include="):])
    cc = ""
    for cand in ("/data/service/hnp/bin/clang++",
                 "/storage/Users/currentUser/usr/local/bin/clang++",
                 os.environ.get("CXX") or "",
                 shutil.which("clang++") or ""):
        if cand and os.path.isfile(cand):
            cc = cand
            break
    if not cc:
        # P2：找不到编译器时核心链接检查未执行——必须计失败，
        # 否则假通过（R9 跳过测试/伪造通过冲突）
        print(f"{FAIL} clang++ 不在 PATH——consumer 编译跳过，"
              f"核心链接检查未执行")
        failures += 1
    else:
        r = subprocess.run(
            [cc, "-std=c++17", src, "-o", out_bin,
             "-I", os.path.join(pkg_folder, "include"),
             "-L", libdir, "-lopenvdb"] + extra_includes,
            capture_output=True, text=True, timeout=180)
        if r.returncode == 0:
            print(f"{PASS} consumer 编译链接成功（libopenvdb 可用）")
        else:
            print(f"{FAIL} consumer 编译链接失败（rc={r.returncode}）")
            print((r.stderr or "")[:300])
            failures += 1

    if failures > 0:
        print(f"{FAIL} {failures} 项检查失败")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
