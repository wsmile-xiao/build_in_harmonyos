#!/usr/bin/env python3
"""test_package for lzip — consumer CLI roundtrip + ELF checks.

断言真实压缩行为（R34）：压缩 → 完整性校验 → 解压 → 字节级一致 → 损坏数据
报错退出，全部以退出码与文件内容为据，不做任何只打印的空壳检查。
"""
import hashlib
import os
import struct
import subprocess
import sys
import tempfile

BIN = "lzip"

NEEDED_ALLOW = (
    "libc.so",
    "libc++_shared.so",
    "ld-musl-aarch64.so.1",
)


def check_elf(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:4] != b"\x7fELF":
        raise RuntimeError(f"{path}: not an ELF file")
    if data[4] != 2 or data[18:20] != b"\xb7\x00":
        raise RuntimeError(f"{path}: not ELF64 AArch64 (e_machine={data[18:20]!r})")
    e_type = struct.unpack_from("<H", data, 16)[0]
    if e_type != 3:
        raise RuntimeError(f"{path}: e_type={e_type}, expected 3 (PIE)")
    needed = []
    for chunk in data.split(b"\x00"):
        if chunk.startswith(b"lib") and b".so" in chunk:
            needed.append(chunk.decode("ascii", "replace"))
    unexpected = [n for n in needed if n not in NEEDED_ALLOW]
    if unexpected:
        raise RuntimeError(f"{path}: unexpected NEEDED entries {unexpected}")
    return needed


def run(argv, timeout=60):
    return subprocess.run(argv, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, timeout=timeout)


def main():
    bindir = sys.argv[1]
    lzip = os.path.join(bindir, BIN)
    if not os.path.isfile(lzip):
        raise RuntimeError(f"{lzip}: binary not installed")

    needed = check_elf(lzip)
    print(f"[elf] {BIN}: PIE AArch64 OK, NEEDED={needed}")

    # 1) 版本输出
    r = run([lzip, "--version"])
    if r.returncode != 0 or "1.24.1" not in r.stdout:
        raise RuntimeError(f"--version failed rc={r.returncode}: {r.stdout[:200]}")
    print("[1] --version OK")

    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "payload.bin")
        payload = (b"GNU lzip roundtrip test for OpenHarmony PC. " * 4096) + os.urandom(4096)
        with open(src, "wb") as fh:
            fh.write(payload)
        sha_src = hashlib.sha256(payload).hexdigest()

        # 2) 压缩（保留原文件）
        r = run([lzip, "-k", "-f", "-9", src])
        lz = src + ".lz"
        if r.returncode != 0 or not os.path.isfile(lz):
            raise RuntimeError(f"compress failed rc={r.returncode}: {r.stdout[:300]}")
        if os.path.getsize(lz) >= os.path.getsize(src):
            # 高重复载荷 -9 必须产生压缩收益
            raise RuntimeError("compressed size >= source size on compressible payload")
        print(f"[2] compress OK ({os.path.getsize(src)} -> {os.path.getsize(lz)} bytes)")

        # 3) 完整性校验
        r = run([lzip, "-t", lz])
        if r.returncode != 0:
            raise RuntimeError(f"-t failed rc={r.returncode}: {r.stdout[:300]}")
        print("[3] integrity test OK")

        # 4) 解压并字节级比对
        r = run([lzip, "-d", "-k", "-f", lz])
        out = src  # -k -f 解回原名
        if r.returncode != 0 or not os.path.isfile(out):
            raise RuntimeError(f"decompress failed rc={r.returncode}: {r.stdout[:300]}")
        with open(out, "rb") as fh:
            sha_out = hashlib.sha256(fh.read()).hexdigest()
        if sha_out != sha_src:
            raise RuntimeError("roundtrip mismatch: sha256 differs")
        print("[4] roundtrip byte-identical OK")

        # 5) 损坏数据必须非零退出（截断 .lz 尾部）
        with open(lz, "r+b") as fh:
            fh.truncate(max(1, os.path.getsize(lz) - 8))
        r = run([lzip, "-t", lz])
        if r.returncode == 0:
            raise RuntimeError("corrupted .lz accepted by -t (must fail)")
        print(f"[5] corrupted-stream rejection OK (rc={r.returncode})")

    print("test_package: PASS")


if __name__ == "__main__":
    main()
