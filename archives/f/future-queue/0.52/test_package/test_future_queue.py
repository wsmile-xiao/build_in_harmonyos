#!/usr/bin/env python3
"""test_future_queue.py — L0c-visible test source for future-queue 0.52.

R34：真实消费被测包 API，而非空壳。本脚本驱动 perl 消费者测试源：

  `test_future_queue.pl` —— 载入**已打包**的 Future::Queue，真实调用其全部
  公开 API（new/push/shift/shift_atmost/finish，含 max_items 背压语义），
  并用 Future 的 await 驱动真实异步流程；含负例（finish 后 push 必须抛异常）。

为何需要本 .py 驱动（而非只放 .pl）：CI L0c 门禁扫描 test_package/ 下的独立
测试源文件，认可的扩展名不含 .pl —— 故用 .py 作为 L0c 可见入口驱动 perl 测试源
（与 metrics-any 0.10、test-metrics-any 0.01 先例同款）。

Usage: test_future_queue.py <site-perl-dir>
"""
import os
import shutil
import subprocess
import sys


def find_perl():
    """定位 perl：优先 OHOS 预装 hnp perl，回退 PATH（与本包 build() 一致）。"""
    hnp = "/data/service/hnp/bin/perl"
    if os.path.isfile(hnp):
        return hnp
    return shutil.which("perl")


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_future_queue.py <site-perl-dir>")
    site = sys.argv[1]

    # 打包完整性：主模块必须存在
    main_pm = os.path.join(site, "Future", "Queue.pm")
    if not os.path.isfile(main_pm):
        raise AssertionError(f"missing packaged module: {main_pm}")

    perl = find_perl()
    if not perl:
        raise SystemExit("FAIL: perl interpreter not found")

    here = os.path.dirname(__file__)
    script = os.path.join(here, "test_future_queue.pl")
    if not os.path.isfile(script):
        raise AssertionError(f"test_future_queue.pl missing: {script}")

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
        raise SystemExit(f"test_future_queue.pl failed (rc={r.returncode})")
    if "ALL OK" not in r.stdout:
        raise SystemExit("FAIL: perl test output missing ALL OK marker")
    print("OK: future-queue 0.52 python-driven consumer check")


if __name__ == "__main__":
    main()
