#!/usr/bin/env python3
"""test_badread.py — badread test_package 验证脚本.

CI L0c 要求 test_package/ 中必须有测试源文件（非 conanfile.py）。
badread 是纯 Python 命令行工具，本脚本真实执行 badread --version
验证包可运行（R34：test_package 必须执行被测包二进制）。
实际测试入口在 test_package/conanfile.py 的 test() 方法中。
"""

import subprocess
import sys


def main():
    """验证 badread 可执行且 --version 输出正确."""
    result = subprocess.run(
        [sys.executable, "-m", "badread", "--version"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0 or "Badread v" not in result.stdout:
        print(f"FAIL: badread --version returned {result.returncode}: {result.stdout!r}",
              file=sys.stderr)
        return 1
    print(f"OK: {result.stdout.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
