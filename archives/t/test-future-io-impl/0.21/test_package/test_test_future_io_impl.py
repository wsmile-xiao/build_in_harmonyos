#!/usr/bin/env python3
"""test_test_future_io_impl.py — L0c-visible test source for test-future-io-impl 0.21.

R34：真实消费被测包 API，而非空壳。本模块的唯一公开 API 是
`run_tests @suitenames`（给 Future::IO 实现方做验收），因此消费者验证 =
提供一份 Future::IO 桩实现，让 run_tests **真正驱动**一个验收套件并断言行为
（脚本内选 `sleep` 套件：自包含、不需要 socket/pipe/fork）。

Usage: test_test_future_io_impl.py <site-perl-dir>
"""
import os
import shutil
import subprocess
import sys


def find_perl():
    """定位 perl 解释器：优先 OHOS 预装 hnp perl，回退 PATH。

    与配方 build() 保持一致（hnp perl 5.42.0 的 Errno 导出完整；设备 perl
    5.42.2 缺 EWOULDBLOCK/ENOTSUP 别名，本模块直接依赖 Errno 常量）。
    """
    hnp = "/data/service/hnp/bin/perl"
    if os.path.isfile(hnp):
        return hnp
    return shutil.which("perl")


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_test_future_io_impl.py <site-perl-dir>")
    site = sys.argv[1]

    # 打包完整性：主模块必须在包内
    module = os.path.join(site, "Test", "Future", "IO", "Impl.pm")
    if not os.path.isfile(module):
        raise AssertionError(f"missing packaged module: {module}")

    perl = find_perl()
    if not perl:
        raise SystemExit("FAIL: perl interpreter not found")

    script = os.path.join(os.path.dirname(__file__), "test_test_future_io_impl.pl")
    if not os.path.isfile(script):
        raise AssertionError(f"test_test_future_io_impl.pl missing: {script}")

    # 绝对路径 perl —— conanrun 的 PATH 未必把 perl 带进子进程
    r = subprocess.run([perl, f"-I{site}", script, site],
                       capture_output=True, text=True)
    if r.stdout:
        sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stderr.write(r.stderr or "")
        raise SystemExit(
            f"perl Test::Future::IO::Impl consumer check failed (rc={r.returncode})")
    if "not ok" in (r.stdout or ""):
        raise SystemExit("FAIL: consumer test reported failing assertions")
    # 精确校验 TAP 计划：5 项本脚本断言 + sleep 套件 6 项 = 1..11
    if "1..11" not in (r.stdout or ""):
        raise SystemExit(
            "FAIL: expected TAP plan 1..11 (5 own + 6 from the sleep suite); got "
            f"{(r.stdout or '').strip().splitlines()[-1:]!r}")
    print("OK: test-future-io-impl 0.21 python-driven consumer check")


if __name__ == "__main__":
    main()
