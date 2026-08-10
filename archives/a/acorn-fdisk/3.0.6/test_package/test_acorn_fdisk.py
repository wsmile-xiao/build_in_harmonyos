#!/usr/bin/env python3
"""Real consumer tests for the packaged acorn-fdisk binary.

The upstream project ships no test suite (the Makefiles define only
all/clean/tar targets). These tests exercise the packaged binary the way
a user would: query the version and usage output, and check the failure
path on a nonexistent device.
"""

from __future__ import annotations

import os
import subprocess
import sys


def run(command: list[str], cwd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=20,
        check=False,
    )


def main() -> int:
    executable = os.path.abspath(sys.argv[1])
    work = os.path.dirname(executable)

    # --version 输出上游版本标识 "arm-fdisk v3.0.6"
    version = run([executable, "--version"], work)
    assert version.returncode == 0, version.stdout
    assert "arm-fdisk v3.0.6" in version.stdout, version.stdout

    # --help 输出 Usage 用法
    help_out = run([executable, "--help"], work)
    assert help_out.returncode == 0, help_out.stdout
    assert "Usage:" in help_out.stdout, help_out.stdout

    # 列表模式 (-l) 下不存在的设备应报错并以非零退出；
    # 裸设备参数会进入交互式分区编辑循环（上游行为），不在非交互测试中调用
    bad = run([executable, "-l", "/dev/nonexistent-acorn-fdisk-test"], work)
    assert bad.returncode != 0, bad.stdout

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
