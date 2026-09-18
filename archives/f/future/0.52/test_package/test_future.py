#!/usr/bin/env python3
"""test_future.py — L0c-visible test source for future 0.52.

R34：真实消费被测包 API，而非空壳。本脚本驱动 test_future.pl，
在打包目录 <site> 下用 perl -I<site> 加载 Future、Future::Utils、
Future::Mutex 并真实调用（done/then/wait_all/needs_all/iterate/mutex），
逐项断言结果后返回退出码。

Usage: test_future.py <site-perl-dir>
"""
import os
import shutil
import subprocess
import sys


def find_perl():
    """定位 perl 解释器：优先 OHOS 预装 hnp perl，回退 PATH。"""
    hnp = "/data/service/hnp/bin/perl"
    if os.path.isfile(hnp):
        return hnp
    return shutil.which("perl")


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_future.py <site-perl-dir>")
    site = sys.argv[1]

    # 打包完整性：核心模块 + 子模块 + 测试辅助模块都必须存在
    required = [
        os.path.join(site, "Future.pm"),
        os.path.join(site, "Future", "PP.pm"),
        os.path.join(site, "Future", "Utils.pm"),
        os.path.join(site, "Future", "Mutex.pm"),
        os.path.join(site, "Future", "Exception.pm"),
        os.path.join(site, "Test", "Future.pm"),
    ]
    for path in required:
        if not os.path.isfile(path):
            raise AssertionError(f"missing packaged module: {path}")

    perl = find_perl()
    if not perl:
        raise SystemExit("FAIL: perl interpreter not found")

    script = os.path.join(os.path.dirname(__file__), "test_future.pl")
    if not os.path.isfile(script):
        raise AssertionError(f"test_future.pl missing: {script}")

    # 绝对路径 perl —— conanrun 的 PATH 未必把 perl 带进子进程
    r = subprocess.run([perl, f"-I{site}", script],
                       capture_output=True, text=True)
    if r.stdout:
        sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stderr.write(r.stderr or "")
        raise SystemExit(f"perl Future API check failed (rc={r.returncode})")
    if "ALL OK" not in r.stdout:
        raise SystemExit("FAIL: unexpected output (missing ALL OK marker)")
    print("OK: future 0.52 python-driven consumer check")


if __name__ == "__main__":
    main()
