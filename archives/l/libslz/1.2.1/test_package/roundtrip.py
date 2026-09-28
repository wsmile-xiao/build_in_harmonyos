#!/usr/bin/env python3
"""libslz 1.2.1 test_package — 独立解码器 round-trip 断言（每条一行 ASSERT_OK/ASSERT_FAIL）。

用法: roundtrip.py <工作目录>
输入: <dir>/rt-input.bin（test_slz 生成的原始数据）
      <dir>/slz-*.out（test.c 通过 libslz C API 编码）
      <dir>/zenc-*.out（test.c 之外由已打包 zenc 二进制编码）
解码使用 python 标准库 zlib（独立实现，与 libslz 互为对照）；
另用已打包 zdec 二进制对 gzip 流做位流级 dump 校验。
"""
import os
import shutil
import subprocess
import sys
import zlib

fails = 0


def check(cond, name):
    global fails
    if cond:
        print("ASSERT_OK %s" % name)
    else:
        print("ASSERT_FAIL %s" % name)
        fails += 1


def load(path):
    with open(path, "rb") as fh:
        return fh.read()


def main():
    work = sys.argv[1] if len(sys.argv) > 1 else "."
    original = load(os.path.join(work, "rt-input.bin"))

    cases = [
        ("slz-gzip.out", 31, "rt_gzip_from_lib"),
        ("slz-zlib.out", 15, "rt_zlib_from_lib"),
        ("slz-deflate.out", -15, "rt_deflate_from_lib"),
        ("zenc-gzip.out", 31, "rt_gzip_from_zenc_l1"),
        ("zenc-zlib.out", 15, "rt_zlib_from_zenc_l1"),
        ("zenc-deflate.out", -15, "rt_deflate_from_zenc_l1"),
        ("zenc-gzip-l0.out", 31, "rt_gzip_from_zenc_l0"),
        ("zenc-zlib-l0.out", 15, "rt_zlib_from_zenc_l0"),
        ("zenc-deflate-l0.out", -15, "rt_deflate_from_zenc_l0"),
    ]
    for fname, wbits, name in cases:
        path = os.path.join(work, fname)
        try:
            decoded = zlib.decompress(load(path), wbits)
            check(decoded == original, name)
        except Exception as exc:  # noqa: BLE001 — 断言失败必须可见
            check(False, "%s (%s)" % (name, exc))

    # 已打包 zdec 二进制：对 gzip 位流做 dump，须正常结束并走到 BFINAL/EOB
    zdec = shutil.which("zdec")
    if not zdec:
        check(False, "zdec_bin_on_path")
    else:
        try:
            proc = subprocess.run(
                [zdec],
                input=load(os.path.join(work, "slz-gzip.out")),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=120,
            )
            out = proc.stdout.decode("utf-8", "replace")
            check(proc.returncode == 0 and "BFINAL = 1" in out and "=> EOB" in out,
                  "zdec_bin_dumps_gzip_stream")
        except Exception as exc:  # noqa: BLE001
            check(False, "zdec_bin_dumps_gzip_stream (%s)" % exc)

    print("ASSERT_SUMMARY fails=%d" % fails)
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
