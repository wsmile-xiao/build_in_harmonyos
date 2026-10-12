#!/usr/bin/env python3
"""Verify the installed signed AArch64 optimizer executes from OHOS HMDFS.

This is a signed-image execution check, not signature cryptographic verification,
an unsigned-image rejection test, or evidence for Android runtime execution.
"""
import hashlib
import os
import pathlib
import re
import struct
import subprocess
import sys


def codesign_size(data):
    if len(data) < 64 or data[:6] != b"\x7fELF\x02\x01":
        raise ValueError("expected a little-endian ELF64 executable")
    header = struct.unpack_from("<HHIQQQIHHHHHH", data, 16)
    if header[1] != 183 or header[0] not in (2, 3):
        raise ValueError("expected an AArch64 executable or PIE")
    offset, width, count, names_index = header[5], header[10], header[11], header[12]
    if width != 64 or not count or not 0 < names_index < count:
        raise ValueError("invalid ELF section table")
    if offset + width * count > len(data):
        raise ValueError("truncated ELF section table")
    sections = [struct.unpack_from("<IIQQQQIIQQ", data, offset + i * width) for i in range(count)]
    names = sections[names_index]
    if names[4] + names[5] > len(data):
        raise ValueError("invalid section-name table")
    strings = data[names[4]:names[4] + names[5]]
    signed = []
    for section in sections:
        pos = section[0]
        if pos >= len(strings) or b"\0" not in strings[pos:]:
            raise ValueError("invalid section name")
        if strings[pos:].split(b"\0", 1)[0] == b".codesign":
            if section[1] == 8 or not section[5] or section[4] + section[5] > len(data):
                raise ValueError("missing/truncated codesign payload")
            signed.append(section[5])
    if len(signed) != 1:
        raise ValueError("expected exactly one populated .codesign section")
    return signed[0]


def main():
    if os.uname().sysname not in ("HarmonyOS", "OpenHarmony", "OHOS"):
        raise RuntimeError("this test requires the actual HarmonyOS PC runtime")
    binary = pathlib.Path(sys.argv[1])
    if binary.is_symlink() or not binary.is_file():
        raise RuntimeError("expected a regular installed package executable")
    binary = binary.resolve(strict=True)
    if not str(binary).startswith("/storage/Users/currentUser/"):
        raise RuntimeError("this test requires an installed binary in the HMDFS user view")
    before = binary.read_bytes()
    signature_bytes = codesign_size(before)
    result = subprocess.run([str(binary), "--show-passes"], capture_output=True, text=True, timeout=60)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    match = re.search(r"Registered passes:\s*(\d+)", result.stdout)
    if result.returncode != 0 or not match or int(match[1]) <= 0:
        raise RuntimeError(f"signed HMDFS optimizer execution failed: RC={result.returncode}")
    if hashlib.sha256(before).digest() != hashlib.sha256(binary.read_bytes()).digest():
        raise RuntimeError("installed executable changed during the check")
    print(f"HARMONY_SIGNED_ELF_SHA256={hashlib.sha256(before).hexdigest()}")
    print(f"HARMONY_CODESIGN_BYTES={signature_bytes}")
    print("HARMONY_TEST_PASS=1/1")


if __name__ == "__main__":
    main()
