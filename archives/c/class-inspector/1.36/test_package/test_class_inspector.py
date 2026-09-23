#!/usr/bin/env python3
"""test_class_inspector.py — L0c-visible test source for class-inspector 1.36.

R34：真实消费被测包 API，而非空壳。本脚本驱动 test_class_inspector.pl，
在打包目录 <site> 下用 perl -I<site> 加载 Class::Inspector 与
Class::Inspector::Functions，真实调用其全部公开接口
（installed/loaded/filename/resolved_filename/loaded_filename/functions/
function_refs/function_exists/methods/subclasses 及函数式导出），逐项断言。

Usage: test_class_inspector.py <site-perl-dir>
"""
import os
import shutil
import subprocess
import sys


def find_perl():
    """定位 perl 解释器：优先 OHOS 预装 hnp perl，回退 PATH。

    与配方 build() 保持一致（hnp perl 5.42.0 的 Errno 导出完整；设备 perl
    5.42.2 缺 EWOULDBLOCK/ENOTSUP 别名常量）。
    """
    hnp = "/data/service/hnp/bin/perl"
    if os.path.isfile(hnp):
        return hnp
    return shutil.which("perl")


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_class_inspector.py <site-perl-dir>")
    site = sys.argv[1]

    # 打包完整性：主模块 + 函数接口模块都必须在包内
    required = [
        os.path.join(site, "Class", "Inspector.pm"),
        os.path.join(site, "Class", "Inspector", "Functions.pm"),
    ]
    for path in required:
        if not os.path.isfile(path):
            raise AssertionError(f"missing packaged module: {path}")

    perl = find_perl()
    if not perl:
        raise SystemExit("FAIL: perl interpreter not found")

    script = os.path.join(os.path.dirname(__file__), "test_class_inspector.pl")
    if not os.path.isfile(script):
        raise AssertionError(f"test_class_inspector.pl missing: {script}")

    # 绝对路径 perl —— conanrun 的 PATH 未必把 perl 带进子进程
    r = subprocess.run([perl, f"-I{site}", script],
                       capture_output=True, text=True)
    if r.stdout:
        sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stderr.write(r.stderr or "")
        raise SystemExit(
            f"perl Class::Inspector consumer check failed (rc={r.returncode})")
    # 精确校验 TAP 计划：防止断言被误删后驱动仍打印 OK、与 assertion_count 失同步
    if "not ok" in (r.stdout or ""):
        raise SystemExit("FAIL: consumer test reported failing assertions")
    if "1..30" not in (r.stdout or ""):
        raise SystemExit(
            "FAIL: expected TAP plan 1..30 (see test_package/MANIFEST.yml "
            f"assertion_count); got: {(r.stdout or '').strip().splitlines()[-1:]!r}")
    print("OK: class-inspector 1.36 python-driven consumer check")


if __name__ == "__main__":
    main()
