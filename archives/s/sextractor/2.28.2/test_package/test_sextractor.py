#!/usr/bin/env python3
"""sextractor consumer test (L0c + R34): standalone test source executed
via self.run from conanfile.py test().

R34: actually invoke the tested CLI — sex on the upstream galaxies.fits
(real source extraction, like upstream make check modelfit.test).

Usage: test_sextractor.py <bindir>
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
    sex = os.path.join(bindir, "sex")
    if not os.path.isfile(sex):
        raise AssertionError(f"sex missing in {bindir}")
    # R34: 用上游 galaxies.fits 做真实源提取（同上游 make check
    # modelfit.test）——输入/输出/工作目录放无空格路径（swarp 同款
    # 教训——工作目录含空格/括号会按空格拆分路径）
    # 测试数据为二进制 FITS 文件，不放 test_package（CI checkout-pr
    # 的 git apply 无法应用二进制 diff——missing binary patch data
    # 实测，同 swarp）——运行时从上游 GitHub raw URL 下载到无空格
    # workdir（galaxies.fits/galaxies.weight.fits/default.psf 二进制，
    # default.param/default.sex/gauss_4.0_7x7.conv 文本）
    workdir = "/data/storage/el2/base/cache/sex-tp-test"
    os.makedirs(workdir, exist_ok=True)
    import urllib.request
    base = "https://raw.githubusercontent.com/astromatic/sextractor/" \
           "2.28.2/tests"
    # CI 下载中断实测（ContentTooShortError——galaxies.fits 只下到
    # 418368/2128320 bytes，raw.githubusercontent 偶发限流）——带重试 +
    # 完整性校验（大小不足则删除重下，最多 5 次）
    for cf in ("galaxies.fits", "galaxies.weight.fits", "default.param",
               "default.sex", "default.psf", "gauss_4.0_7x7.conv"):
        dst = os.path.join(workdir, cf)
        got = False
        for attempt in range(5):
            try:
                if not os.path.isfile(dst) or os.path.getsize(dst) < 100:
                    urllib.request.urlretrieve(f"{base}/{cf}", dst)
                if os.path.getsize(dst) < 100:
                    os.remove(dst)
                    continue
                got = True
                break
            except Exception:
                if os.path.isfile(dst):
                    os.remove(dst)
                continue
        if not got:
            raise AssertionError(f"{cf} download failed (5 attempts)")
    galaxies = os.path.join(workdir, "galaxies.fits")
    weight = os.path.join(workdir, "galaxies.weight.fits")
    r = subprocess.run(
        [sex, galaxies, "-c", "default.sex",
         "-WEIGHT_IMAGE", weight,
         "-CATALOG_NAME", "galaxies.cat", "-CHECKIMAGE_TYPE", "NONE"],
        cwd=workdir, capture_output=True, text=True, timeout=120)
    cat = os.path.join(workdir, "galaxies.cat")
    if r.returncode != 0 or not os.path.isfile(cat):
        raise AssertionError(f"sex extraction failed: {r.stderr[:300]}")
    # 星表非空（提取到源）
    size = os.path.getsize(cat)
    if size == 0:
        raise AssertionError("galaxies.cat empty — no sources extracted")
    print("OK: sextractor 2.28.2 (galaxies.fits extraction ok, "
          f"catalog {size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
