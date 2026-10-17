#!/usr/bin/env python3
"""commoncpp2 consumer test (R34): headers + library present, and a real
C++ link/run smoke test using a commoncpp2 class (per review-memory 一.1)."""
import os
import subprocess
import sys
import tempfile


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    inc = os.path.join(pkg, "usr", "include")
    lib = os.path.join(pkg, "usr", "lib")
    if not os.path.isdir(os.path.join(inc, "cc++")):
        print(f"FAIL: cc++ headers missing: {inc}", file=sys.stderr)
        return 1
    # 真实编译+运行一个使用 commoncpp2 类的 smoke test（调用 API）
    src = os.path.join(os.path.dirname(__file__), "smoke.cpp")
    # 编译产物写入临时目录——不落 test_package 源码目录（避免污染/误提交
    # 二进制，review-memory R19；只读文件系统也不产生假阴性）
    tmpdir = tempfile.mkdtemp(prefix="ccxx-smoke-")
    binp = os.path.join(tmpdir, "smoke")
    try:
        r = subprocess.run(
            ["/data/service/hnp/bin/clang++", src, "-o", binp,
             f"-I{inc}", f"-L{lib}", "-lccgnu2", "-lpthread",
             "-Wno-deprecated-declarations"],
            capture_output=True, text=True)
        if r.returncode != 0:
            print(f"FAIL: compile smoke: {r.stderr}", file=sys.stderr)
            return 1
        r = subprocess.run([binp], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"FAIL: run smoke: {r.stderr}", file=sys.stderr)
            return 1
    finally:
        # 清理临时目录（含编译产物）
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
    print("OK: commoncpp2 headers + lib present + smoke C++ link/run works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
