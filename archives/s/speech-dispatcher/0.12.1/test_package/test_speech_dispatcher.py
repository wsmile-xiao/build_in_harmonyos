#!/usr/bin/env python3
"""Conan test_package for speech-dispatcher — R34 real artifact verification.

speech-dispatcher ships the libspeechd client library (libspeechd.so) plus the
public header libspeechd.h. The daemon/TTS backends need a running speech
synthesizer + audio device (OHOS lacks), so the verifiable artifacts here are:
- lib/libspeechd.so — valid aarch64 ELF shared object (ET_DYN);
- include/libspeechd.h — the public client API header.
ELF type is checked via magic bytes (no external `file`/`readelf` in the
OHOS sandbox).
"""
import os
import struct
import sys


ELF_MAGIC = b"\x7fELF"


def _is_elf_shared_object(path):
    with open(path, "rb") as f:
        ident = f.read(16)
    if len(ident) < 16 or ident[:4] != ELF_MAGIC:
        return False
    with open(path, "rb") as f:
        f.seek(16)
        raw = f.read(2)
    if len(raw) < 2:
        return False
    e_type = struct.unpack("<H", raw)[0]
    return e_type == 3  # ET_DYN


def main():
    pkg = sys.argv[1]
    # 1) libspeechd shared object present + valid ELF
    so = os.path.join(pkg, "lib", "libspeechd.so")
    if not os.path.isfile(so):
        print(f"FAIL: libspeechd.so not found: {so}", file=sys.stderr)
        return 1
    if not _is_elf_shared_object(so):
        print(f"FAIL: {so} is not an ELF shared object", file=sys.stderr)
        return 1
    # 2) public header present (安装到 include/speech-dispatcher/ 子目录)
    hdr = os.path.join(pkg, "include", "speech-dispatcher", "libspeechd.h")
    if not os.path.isfile(hdr):
        print(f"FAIL: libspeechd.h not found: {hdr}", file=sys.stderr)
        return 1

    print("OK: speech-dispatcher libspeechd.so present + ELF shared object, "
          "libspeechd.h present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
