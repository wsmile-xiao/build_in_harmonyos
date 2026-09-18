#!/usr/bin/env python3
"""test_metrics_any.py — L0c-visible test source for metrics-any 0.10.

R34：真实消费被测包 API，而非空壳。本脚本驱动两个 perl 测试源：

1. `test_metrics_any.pl` —— Test 适配器（counter/gauge/distribution/timer、
   标签传参、strict 模式校验）
2. `test_metrics_any_null.pl` —— Null 适配器（**必须独立进程**：适配器一旦
   确定就不能在同一进程内更换，上游 t/10adapter-null.t 亦为独立 .t 文件）

Usage: test_metrics_any.py <site-perl-dir>
"""
import os
import shutil
import subprocess
import sys


def find_perl():
    """定位 perl 解释器：优先 OHOS 预装 hnp perl，回退 PATH。

    hnp perl 5.42.0 的 Errno 完整（设备 perl 5.42.2 缺 EWOULDBLOCK/ENOTSUP
    别名），与本配方 build() 的选择保持一致。
    """
    hnp = "/data/service/hnp/bin/perl"
    if os.path.isfile(hnp):
        return hnp
    return shutil.which("perl")


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_metrics_any.py <site-perl-dir>")
    site = sys.argv[1]

    # 打包完整性：主模块 + 各子模块都必须在包内
    required = [
        os.path.join(site, "Metrics", "Any.pm"),
        os.path.join(site, "Metrics", "Any", "Adapter.pm"),
        os.path.join(site, "Metrics", "Any", "Collector.pm"),
        os.path.join(site, "Metrics", "Any", "AdapterBase", "Stored.pm"),
        os.path.join(site, "Metrics", "Any", "Adapter", "Null.pm"),
        os.path.join(site, "Metrics", "Any", "Adapter", "File.pm"),
        os.path.join(site, "Metrics", "Any", "Adapter", "Stderr.pm"),
        os.path.join(site, "Metrics", "Any", "Adapter", "Tee.pm"),
        os.path.join(site, "Metrics", "Any", "Adapter", "Test.pm"),
    ]
    for path in required:
        if not os.path.isfile(path):
            raise AssertionError(f"missing packaged module: {path}")

    perl = find_perl()
    if not perl:
        raise SystemExit("FAIL: perl interpreter not found")

    here = os.path.dirname(__file__)
    # 每个测试源一个独立进程（与上游 t/*.t 的运行模型一致）
    for name in ("test_metrics_any.pl", "test_metrics_any_null.pl"):
        script = os.path.join(here, name)
        if not os.path.isfile(script):
            raise AssertionError(f"{name} missing: {script}")
        # 绝对路径 perl —— conanrun 的 PATH 未必把 perl 带进子进程
        r = subprocess.run([perl, f"-I{site}", script],
                           capture_output=True, text=True)
        if r.stdout:
            sys.stdout.write(r.stdout)
        if r.returncode != 0:
            sys.stderr.write(r.stderr or "")
            raise SystemExit(f"{name} failed (rc={r.returncode})")
        if "ALL OK" not in r.stdout:
            raise SystemExit(f"FAIL: {name} output missing ALL OK marker")
    print("OK: metrics-any 0.10 python-driven consumer check")


if __name__ == "__main__":
    main()
