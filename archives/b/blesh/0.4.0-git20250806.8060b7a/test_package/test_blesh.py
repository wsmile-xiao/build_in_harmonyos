#!/usr/bin/env python3
"""Conan test_package for blesh — 验证 ble.sh 真实加载 + 版本输出。"""
import os
import subprocess
import sys


def main():
    pkg_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    ble_sh = os.path.join(pkg_dir, "ble.sh")
    if not os.path.isfile(ble_sh):
        print(f"FAIL: {ble_sh} 不存在")
        return 1
    print(f"PASS: ble.sh 存在 ({os.path.getsize(ble_sh)} bytes)")

    # bash ble.sh --version——真实加载 ble.sh（BLE_VERSION 宏）
    r = subprocess.run(["/data/service/hnp/bin/bash", ble_sh, "--version"],
                       capture_output=True, text=True, timeout=120)
    out = (r.stdout or "") + (r.stderr or "")
    print(out.strip())
    if "Bash Line Editor" not in out:
        print("FAIL: ble.sh --version 未输出版本信息")
        return 1

    # 非交互加载验证：bash ble.sh --test main（上游 ble/test 框架 main 节）
    r2 = subprocess.run(["/data/service/hnp/bin/bash", ble_sh, "--test", "main"],
                        capture_output=True, text=True, timeout=180,
                        env={**os.environ, "PATH": "/system/bin:/data/service/hnp/bin:" + os.environ.get("PATH", "")})
    out2 = (r2.stdout or "") + (r2.stderr or "")
    if "29/29" not in out2:
        print("FAIL: ble.sh --test main 未通过")
        print(out2[-500:])
        return 1
    print("PASS: ble.sh --test main 29/29 通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
