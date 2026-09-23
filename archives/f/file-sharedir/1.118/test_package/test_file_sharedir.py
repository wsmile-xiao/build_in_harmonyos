#!/usr/bin/env python3
"""test_file_sharedir.py — L0c-visible test source for file-sharedir 1.118.

R34：真实消费被测包 API，而非空壳。本脚本驱动 perl 消费者测试源：

  `test_file_sharedir.pl` —— 载入**已打包**的 File::ShareDir，真实调用
  dist_dir / dist_file / module_dir / module_file，校验安装包的数据文件确实
  随包发布，并含负例（未知发行版 / 缺失文件必须报错）。

为何需要本 .py 驱动（而非只放 .pl）：CI L0c 门禁扫描 test_package/ 下的独立
测试源文件，认可的扩展名不含 .pl —— 故用 .py 作为 L0c 可见入口驱动 perl 测试源
（与 file-sharedir-install 0.14、metrics-any 0.10 先例同款）。

Usage: test_file_sharedir.py <site-perl-dir>
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
        raise SystemExit("usage: test_file_sharedir.py <site-perl-dir>")
    site = sys.argv[1]

    # 打包完整性：主模块 + 数据文件目录缺一不可
    main_pm = os.path.join(site, "File", "ShareDir.pm")
    if not os.path.isfile(main_pm):
        raise AssertionError(f"missing packaged module: {main_pm}")
    share_root = os.path.join(site, "auto", "share")
    if not os.path.isdir(share_root):
        raise AssertionError(
            f"missing shared data files: {share_root} "
            "(dist_dir/module_dir cannot work without them)")

    perl = find_perl()
    if not perl:
        raise SystemExit("FAIL: perl interpreter not found")

    here = os.path.dirname(__file__)
    script = os.path.join(here, "test_file_sharedir.pl")
    if not os.path.isfile(script):
        raise AssertionError(f"test_file_sharedir.pl missing: {script}")

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
        raise SystemExit(f"test_file_sharedir.pl failed (rc={r.returncode})")
    if "ALL OK" not in r.stdout:
        raise SystemExit("FAIL: perl test output missing ALL OK marker")
    print("OK: file-sharedir 1.118 python-driven consumer check")


if __name__ == "__main__":
    main()
