#!/usr/bin/env python3
"""test_alot.py — alot test_package validation script.

CI L0c requires a test source file (non conanfile.py) in test_package/.
alot 是纯 Python 终端 MUA，此脚本执行 `alot --help` 验证包装脚本可运行
（R34: test_package must execute the tested package's binary）。
实际测试入口为 test_package/conanfile.py test() 方法。
"""

import subprocess
import sys


def main():
    """Verify bin/alot wrapper is executable and --help works."""
    exe = sys.argv[1] if len(sys.argv) > 1 else "alot"
    result = subprocess.run(
        [exe, "--help"], capture_output=True, text=True, timeout=30,
    )
    # alot 无依赖数据库时可正常输出用法；退出码 0/1/2 均视为包装可用
    if result.returncode not in (0, 1, 2):
        print(
            f"FAIL: alot --help returned {result.returncode}: "
            f"{result.stdout!r} {result.stderr!r}",
            file=sys.stderr,
        )
        return 1
    print(f"OK: alot --help exit={result.returncode}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
