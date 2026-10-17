#!/usr/bin/env python3
"""test_package 消费者冒烟测试 — vzlogger 0.8.9

调用安装后的 vzlogger 二进制，断言 --version 输出含版本号 0.8.9、
--help 输出含受支持协议列表头（R34 真实内容断言，非空壳）。
"""
import subprocess
import sys


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("usage: verify_vzlogger.py <vzlogger-binary>")
    vzlogger = sys.argv[1]

    # 冒烟 1：--version 输出必须包含版本号 0.8.9
    version = subprocess.run(
        [vzlogger, "--version"], capture_output=True, text=True, timeout=30
    )
    if version.returncode != 0:
        raise SystemExit(f"vzlogger --version 退出码非 0: {version.returncode}")
    if "0.8.9" not in version.stdout:
        raise SystemExit(f"vzlogger --version 输出缺少版本号 0.8.9: {version.stdout!r}")

    # 冒烟 2：--help 输出必须列出受支持协议的列表头
    help_ = subprocess.run(
        [vzlogger, "--help"], capture_output=True, text=True, timeout=30
    )
    if help_.returncode != 0:
        raise SystemExit(f"vzlogger --help 退出码非 0: {help_.returncode}")
    if "protocol types are supported" not in help_.stdout:
        raise SystemExit(f"vzlogger --help 输出缺少协议列表: {help_.stdout!r}")

    print("verify_vzlogger: OK (version=0.8.9, help 协议列表头)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
