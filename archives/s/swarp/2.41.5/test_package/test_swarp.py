#!/usr/bin/env python3
"""swarp consumer test (L0c + R34): standalone test source executed via
self.run from conanfile.py test().

R34: actually invoke the tested CLI — swarp --version / --help, and
resample the upstream test.fits image.

Usage: test_swarp.py <bindir>
"""
import os
import shutil
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <bindir>", file=sys.stderr)
        return 2
    bindir = sys.argv[1]
    swarp = os.path.join(bindir, "swarp")
    if not os.path.isfile(swarp):
        raise AssertionError(f"swarp missing in {bindir}")
    # R34: swarp --help 输出用法（SYNTAX 到 stderr——非 usage 关键字，
    # 且 rc 非 0 是 swarp 无参数退出行为——只验证输出包含 SYNTAX）
    r = subprocess.run([swarp, "--help"], capture_output=True, text=True,
                       timeout=60)
    combined = (r.stdout + r.stderr).lower()
    if "syntax" not in combined:
        raise AssertionError(f"swarp --help failed: {r.stderr[:300]}")
    # 真实图像处理：用上游 test.fits 做一次重采样（--resample 模式）
    # 输入/输出/工作目录全部放无空格路径（工作目录含空格/括号——
    # swarp 按空格拆分输入路径实测失败：'/path/not found'——同
    # ats2/autodocksuite 教训——CI 目录无空格但本地验证需兼容）
    # test.fits 为二进制 FITS 图像，不放 test_package（CI checkout-pr
    # 的 git apply 无法应用二进制 diff——missing binary patch data
    # 实测）——运行时从上游 GitHub raw URL 下载到无空格 workdir
    workdir = "/data/storage/el2/base/cache/swarp-tp-test"
    os.makedirs(workdir, exist_ok=True)
    test_fits = os.path.join(workdir, "test.fits")
    if not os.path.isfile(test_fits) or os.path.getsize(test_fits) < 1000:
        import urllib.request
        urllib.request.urlretrieve(
            "https://raw.githubusercontent.com/astromatic/swarp/"
            "2.41.5/test/test.fits", test_fits)
        if os.path.getsize(test_fits) < 1000:
            raise AssertionError("test.fits download failed (too small)")
    r2 = subprocess.run(
        [swarp, test_fits, "-IMAGEOUT_NAME", "out.fits",
         "-RESAMPLE", "Y", "-COMBINE_TYPE", "MEDIAN"],
        cwd=workdir, capture_output=True, text=True, timeout=120)
    out = os.path.join(workdir, "out.fits")
    if r2.returncode != 0 or not os.path.isfile(out):
        raise AssertionError(
            f"swarp resample failed: {r2.stderr[:300]}")
    print("OK: swarp 2.41.5 (--help + test.fits resample ok)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
