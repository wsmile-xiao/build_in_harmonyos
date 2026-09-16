#!/usr/bin/env python3
"""Prepare a signed Alpine GNAT seed for the OHOS XPM loader."""

import os
import shutil
import stat
import struct
import sys
from pathlib import Path

REPLACEMENTS = {
    "libisl.so.15": "i",
    "libmpc.so.3": "c",
    "libmpfr.so.6": "r",
    "libgmp.so.10": "g",
    "libz.so.1": "z",
}


def patch_elf(path, interpreter):
    data = bytearray(path.read_bytes())
    if data[:6] != b"\x7fELF\x02\x01":
        return False

    phoff = struct.unpack_from("<Q", data, 32)[0]
    phentsize, phnum = struct.unpack_from("<HH", data, 54)
    loads = []
    dynamic = None
    interp = None
    for index in range(phnum):
        offset = phoff + index * phentsize
        p_type, _, p_offset, p_vaddr, _, p_filesz, _, _ = struct.unpack_from(
            "<IIQQQQQQ", data, offset
        )
        if p_type == 1:
            loads.append((p_vaddr, p_vaddr + p_filesz, p_offset))
        elif p_type == 2:
            dynamic = (p_offset, p_filesz)
        elif p_type == 3:
            interp = (p_offset, p_filesz)

    changed = False
    if interp is not None:
        offset, size = interp
        replacement = interpreter.encode("ascii") + b"\0"
        if len(replacement) > size:
            raise RuntimeError("PT_INTERP is too short: {}".format(path))
        data[offset : offset + size] = replacement + b"\0" * (
            size - len(replacement)
        )
        changed = True

    if dynamic is not None:
        dynamic_offset, dynamic_size = dynamic
        strtab = None
        needed = []
        for offset in range(dynamic_offset, dynamic_offset + dynamic_size, 16):
            tag, value = struct.unpack_from("<QQ", data, offset)
            if tag == 0:
                break
            if tag == 1:
                needed.append(value)
            elif tag == 5:
                strtab = value
        if strtab is not None:
            strtab_offset = None
            for start, end, file_offset in loads:
                if start <= strtab < end:
                    strtab_offset = file_offset + strtab - start
                    break
            if strtab_offset is not None:
                for string_offset in needed:
                    offset = strtab_offset + string_offset
                    end = data.find(b"\0", offset)
                    if end < 0:
                        raise RuntimeError(
                            "unterminated dependency string: {}".format(path)
                        )
                    original = data[offset:end].decode("ascii")
                    replacement = REPLACEMENTS.get(original)
                    if replacement is None:
                        continue
                    encoded = replacement.encode("ascii") + b"\0"
                    data[offset : end + 1] = b"\0" * (end - offset + 1)
                    data[offset : offset + len(encoded)] = encoded
                    changed = True

    if changed:
        mode = stat.S_IMODE(path.stat().st_mode)
        path.write_bytes(data)
        path.chmod(mode)
    return interp is not None


def main():
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: prepare_ohos_bootstrap.py <seed> <bootstrap> <loader>"
        )
    seed = Path(sys.argv[1])
    bootstrap = Path(sys.argv[2])
    loader = Path(sys.argv[3])
    if not seed.is_dir() or not loader.is_file():
        raise SystemExit("bootstrap input is missing")

    if bootstrap.exists():
        shutil.rmtree(bootstrap)
    short_dir = bootstrap / "lib"
    short_dir.mkdir(parents=True)
    for short_name, relative in {
        "i": Path("usr/lib/libisl.so.15"),
        "c": Path("usr/lib/libmpc.so.3"),
        "r": Path("usr/lib/libmpfr.so.6"),
        "g": Path("usr/lib/libgmp.so.10"),
        "z": Path("lib/libz.so.1"),
    }.items():
        source = seed / relative
        if not source.is_file():
            raise SystemExit("missing dependency: {}".format(source))
        shutil.copy2(source, short_dir / short_name)
    shutil.copy2(loader, bootstrap / "ld-musl-aarch64.so.1")
    (bootstrap / "ld-musl-aarch64.so.1").chmod(0o755)
    shutil.copy2(loader, short_dir / "libc.musl-aarch64.so.1")
    (short_dir / "libc.musl-aarch64.so.1").chmod(0o755)

    candidates = [
        path
        for root in (seed, bootstrap)
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    ]
    interpreters = sum(
        patch_elf(path, "/proc/self/fd/9") for path in candidates
    )
    if interpreters < 3:
        raise SystemExit(
            "too few patched seed interpreters: {}".format(interpreters)
        )
    print("patched_seed_interpreters={}".format(interpreters))


if __name__ == "__main__":
    main()
