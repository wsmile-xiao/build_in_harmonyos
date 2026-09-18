#!/usr/bin/env python3
"""test_file_sharedir_install.py — L0c-visible test source for file-sharedir-install 0.14.

R34：真实消费被测包 API，而非空壳。本模块的消费者语义是「让 Makefile.PL 声明并
安装共享数据文件」，因此本脚本驱动 test_file_sharedir_install.pl，后者会在独立
临时目录内：登记 dist/module 共享目录 → 生成真实 Makefile → 执行 make →
校验共享文件确实被复制进 blib（含含空格文件名与隐藏文件的默认排除行为）。

Usage: test_file_sharedir_install.py <site-perl-dir>
"""
import os
import shutil
import subprocess
import sys


def find_perl():
    """定位 perl 解释器：优先 OHOS 预装 hnp perl，回退 PATH。

    与配方 build() 保持一致（hnp perl 5.42.0 的 Errno 导出完整，设备 perl
    5.42.2 缺别名常量）。
    """
    hnp = "/data/service/hnp/bin/perl"
    if os.path.isfile(hnp):
        return hnp
    return shutil.which("perl")


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_file_sharedir_install.py <site-perl-dir>")
    site = sys.argv[1]

    # 打包完整性：主模块必须在包内
    module = os.path.join(site, "File", "ShareDir", "Install.pm")
    if not os.path.isfile(module):
        raise AssertionError(f"missing packaged module: {module}")

    perl = find_perl()
    if not perl:
        raise SystemExit("FAIL: perl interpreter not found")

    script = os.path.join(os.path.dirname(__file__), "test_file_sharedir_install.pl")
    if not os.path.isfile(script):
        raise AssertionError(f"test_file_sharedir_install.pl missing: {script}")

    # 绝对路径 perl —— conanrun 的 PATH 未必把 perl 带进子进程
    r = subprocess.run([perl, f"-I{site}", script, site],
                       capture_output=True, text=True)
    if r.stdout:
        sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stderr.write(r.stderr or "")
        raise SystemExit(
            f"perl File::ShareDir::Install consumer check failed (rc={r.returncode})")
    # 必须真的跑完（TAP 计划存在）且无失败
    if "not ok" in (r.stdout or ""):
        raise SystemExit("FAIL: consumer test reported failing assertions")
    # 精确校验 TAP 计划数：防止脚本里断言被误删后本驱动仍打印 OK，
    # 与 MANIFEST.yml 的 assertion_count 静默失同步（W4 审计 P3）。
    if "1..13" not in (r.stdout or ""):
        raise SystemExit(
            "FAIL: expected TAP plan 1..13 (see test_package/MANIFEST.yml "
            f"assertion_count); got: {(r.stdout or '').strip().splitlines()[-1:]!r}")
    print("OK: file-sharedir-install 0.14 python-driven consumer check")


if __name__ == "__main__":
    main()
