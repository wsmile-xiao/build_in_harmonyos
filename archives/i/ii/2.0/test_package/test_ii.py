#!/usr/bin/env python3
"""HarmonyOS PC native executable startup smoke test."""

import subprocess
import sys


def main(executable):
    usage = subprocess.run([executable, "-z"], capture_output=True, text=True, timeout=5)
    assert usage.returncode != 0, "ii accepted an unsupported option"
    assert "usage:" in usage.stderr and "-s host" in usage.stderr, usage.stderr
    assert "getpwuid" not in usage.stderr, usage.stderr


if __name__ == "__main__":
    main(sys.argv[1])
    print("HarmonyOS PC 本机测试通过：ii 原生二进制启动、passwd fallback 与 CLI usage")
