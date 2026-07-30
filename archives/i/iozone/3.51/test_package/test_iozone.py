#!/usr/bin/env python3
"""test_iozone.py — iozone 3.51 安装后验证脚本。

由 test_package/conanfile.py test() 调用。
直接执行被测二进制，非零退出码表示失败。

测试内容：
  1. iozone -v 验证版本输出
  2. benchmark -i 0..7 验证 8 类文件系统 IO 场景
  工作目录使用 $TMPDIR 或可写 fallback（不依赖只读 /tmp, E002）
"""
import os
import subprocess
import sys
import tempfile


def main():
    iozone_cmd = sys.argv[1] if len(sys.argv) > 1 else "iozone"

    # 可写临时目录（避开只读 /tmp, E002）
    tmpdir = os.environ.get("TMPDIR")
    if not tmpdir:
        tmpdir = os.path.join(os.environ.get("HOME", "/storage"), "tmp")
    os.makedirs(tmpdir, exist_ok=True)
    workdir = tempfile.mkdtemp(prefix="iozone-test-", dir=tmpdir)
    testfile = os.path.join(workdir, "iozone_combined.tmp")

    try:
        # Test 1: version
        print("=== Test 1: iozone -v ===")
        r = subprocess.run([iozone_cmd, "-v"], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"FAIL: iozone -v returned {r.returncode}", file=sys.stderr)
            sys.exit(1)
        if "Version $Revision: 3.51" not in r.stdout:
            print("FAIL: version string mismatch", file=sys.stderr)
            sys.exit(1)
        print("PASS: version check")

        # Test 2: benchmark -i 0..7
        print("=== Test 2: benchmark -i 0 1 2 3 4 5 6 7 ===")
        r = subprocess.run(
            [iozone_cmd, "-i0", "-i1", "-i2", "-i3", "-i4", "-i5", "-i6", "-i7",
             "-s64k", "-r4k", "-c", "-e", "-f", testfile],
            capture_output=True, text=True
        )
        if r.returncode != 0:
            print(f"FAIL: benchmark returned {r.returncode}", file=sys.stderr)
            print(r.stderr, file=sys.stderr)
            sys.exit(1)
        if "iozone test complete" not in r.stdout:
            print("FAIL: benchmark did not complete", file=sys.stderr)
            sys.exit(1)
        print("PASS: benchmark -i 0..7")

        print("\nAll tests PASSED")
        sys.exit(0)

    finally:
        # Cleanup
        import shutil
        if os.path.isdir(workdir):
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
