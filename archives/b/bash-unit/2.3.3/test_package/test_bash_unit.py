#!/usr/bin/env python3
"""Conan test_package for bash-unit — 验证 bash_unit 真实可执行（跑一个内联测试）。"""
import os
import subprocess
import sys


def main():
    pkg_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    bu = os.path.join(pkg_dir, "bin", "bash_unit")
    if not os.path.isfile(bu):
        print(f"FAIL: {bu} 不存在")
        return 1
    print(f"PASS: bin/bash_unit 存在 ({os.path.getsize(bu)} bytes)")

    # 内联测试：bash_unit 跑一个 test_ok 断言（真实执行，非 stub）
    smoke = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smoke_test.sh")
    with open(smoke, "w") as f:
        f.write('test_ok() { assert_equals 1 1; }\n')
    r = subprocess.run([bu, smoke], capture_output=True, text=True, timeout=60)
    out = (r.stdout or "") + (r.stderr or "")
    print(out.strip())
    if "Overall result: SUCCESS" not in out:
        print("FAIL: bash_unit 内联测试未通过")
        return 1
    print("PASS: bash_unit 内联测试 SUCCESS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
