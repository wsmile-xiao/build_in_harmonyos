#!/usr/bin/env python3
"""test_gputils.py — consumer test source for gputils 1.5.2 (L0c).

REAL API check (R34): assemble a minimal PIC16 asm with the packaged
gpasm and assert the .hex output is produced (gputils core tool).
Usage: test_gputils.py <gpasm-bin-dir>
"""
import os
import subprocess
import sys
import tempfile


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_gputils.py <gpasm-bin-dir>")
    bindir = sys.argv[1]
    gpasm = os.path.join(bindir, "gpasm")
    if not os.path.isfile(gpasm):
        raise AssertionError(f"gpasm binary missing: {gpasm}")
    # 头文件搜索路径：p16f877.inc 等 PIC 处理器定义在包内 header/ 目录
    # （gpasm 汇编 include "p16f877.inc" 需 -I 显式指定，否则找不到头文件）。
    pkg_dir = os.path.dirname(bindir)
    header_dir = os.path.join(pkg_dir, "header")
    # minimal PIC16 asm (blink loop — assembles with gpasm)
    asm = ("    list p=16f877\n"
           "    include \"p16f877.inc\"\n"
           "    org 0\n"
           "start\n"
           "    goto start\n"
           "    end\n")
    with tempfile.TemporaryDirectory() as tmp:
        asm_file = os.path.join(tmp, "t.asm")
        with open(asm_file, "w") as f:
            f.write(asm)
        # 无 -c：直接汇编产出 t.hex（-c 只编译 .o 不产 hex，AI review P1）
        r = subprocess.run([gpasm, "-I", header_dir, asm_file],
                           capture_output=True, text=True)
        if r.returncode != 0:
            sys.stderr.write(r.stderr or "")
            raise AssertionError(f"gpasm failed with rc={r.returncode}")
        hex_file = os.path.join(tmp, "t.hex")
        if not os.path.isfile(hex_file):
            raise AssertionError(f".hex output missing: {hex_file}")
        with open(hex_file, "r") as f:
            content = f.read()
        if ":00000001FF" not in content:
            raise AssertionError(f".hex missing end-of-file record: {content!r}")
    print("OK: gputils 1.5.2 consumer check (gpasm assembled t.hex)")


if __name__ == "__main__":
    main()
