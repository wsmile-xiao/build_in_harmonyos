#!/usr/bin/env python3
"""test_test_metrics_any.py — L0c-visible test source for test-metrics-any 0.01.

R34：真实消费被测包 API，而非空壳。本脚本驱动 perl 消费者测试源：

  `test_test_metrics_any.pl` —— 载入**已打包**的 Test::Metrics::Any，真实调用
  其导出 API（is_metrics / is_metrics_from）与谓词助手（positive / at_least /
  greater_than），并以 Test::Builder::Tester 做**负例**（证明断言会失败，
  不是恒真空壳）。

为何需要本 .py 驱动（而非只放 .pl）：CI L0c 门禁扫描 test_package/ 下的
独立测试源文件，认可的扩展名不含 .pl —— 故用 .py 作为 L0c 可见入口来驱动
perl 测试源（与 metrics-any 0.10 先例同款）。

Usage: test_test_metrics_any.py <site-perl-dir>
"""
import os
import shutil
import subprocess
import sys


def find_perl():
    """定位 perl 解释器：优先 OHOS 预装 hnp perl，回退 PATH。

    与本配方 build() 的选择保持一致（统一用 hnp perl，避免设备 perl 与
    hnp perl 的 Errno 实现差异带来的同族问题）。
    """
    hnp = "/data/service/hnp/bin/perl"
    if os.path.isfile(hnp):
        return hnp
    return shutil.which("perl")


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_test_metrics_any.py <site-perl-dir>")
    site = sys.argv[1]

    # 打包完整性：本包主模块必须存在
    main_pm = os.path.join(site, "Test", "Metrics", "Any.pm")
    if not os.path.isfile(main_pm):
        raise AssertionError(f"missing packaged module: {main_pm}")

    perl = find_perl()
    if not perl:
        raise SystemExit("FAIL: perl interpreter not found")

    here = os.path.dirname(__file__)
    script = os.path.join(here, "test_test_metrics_any.pl")
    if not os.path.isfile(script):
        raise AssertionError(f"test_test_metrics_any.pl missing: {script}")

    # 绝对路径 perl（conanrun 的 PATH 未必把 perl 带进子进程）。
    # -I<site>：本包模块；依赖 metrics-any 的模块由 conanrun 的 PERL5LIB 提供
    # （本包 package_info 用 runenv_info.prepend_path 声明，与依赖的声明叠加）。
    env = dict(os.environ)
    sep = os.pathsep
    env["PERL5LIB"] = sep.join(
        [site] + ([env["PERL5LIB"]] if env.get("PERL5LIB") else []))

    r = subprocess.run([perl, f"-I{site}", script],
                       capture_output=True, text=True, env=env)
    if r.stdout:
        sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stderr.write(r.stderr or "")
        raise SystemExit(f"test_test_metrics_any.pl failed (rc={r.returncode})")
    if "ALL OK" not in r.stdout:
        raise SystemExit("FAIL: perl test output missing ALL OK marker")
    print("OK: test-metrics-any 0.01 python-driven consumer check")


if __name__ == "__main__":
    main()
