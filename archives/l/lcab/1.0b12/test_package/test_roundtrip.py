#!/usr/bin/env python3
"""End-to-end consumer use case for lcab on HarmonyOS PC.

Scenario: a user on HarmonyOS PC packs a project directory that lives in the
app sandbox ($TMPDIR, HMDFS on device) into a .cab for Windows delivery.
The directory holds a UTF-8 (Chinese) file name, nested folders and a binary
file that spans several 32 KiB CFDATA blocks and contains NUL bytes.

The test runs the installed `lcab -r`, then reads the cabinet back with an
independent MS-CAB parser (uncompressed folders), recomputes every CFDATA
checksum, extracts each file and compares it byte for byte with the original.
Finally it corrupts one data byte and requires the parser to reject the copy,
so the verification itself is shown not to be vacuous.

usage: test_roundtrip.py <path-to-lcab>
"""
import hashlib
import os
import random
import shutil
import struct
import subprocess
import sys
import tempfile

BLOCK = 32768


def fail(msg):
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def cab_checksum(data, seed=0):
    """MS-CAB CFDATA checksum (same algorithm as lcab checksum.c)."""
    csum = seed
    n4 = len(data) // 4
    for i in range(n4):
        csum ^= struct.unpack_from("<I", data, i * 4)[0]
    tail = data[n4 * 4:]
    temp = 0
    if len(tail) == 3:
        temp = (tail[0] << 16) | (tail[1] << 8) | tail[2]
    elif len(tail) == 2:
        temp = (tail[0] << 8) | tail[1]
    elif len(tail) == 1:
        temp = tail[0]
    return (csum ^ temp) & 0xFFFFFFFF


def read_cab(blob):
    """Parse an uncompressed single-cabinet MS-CAB; return {name: bytes}."""
    if blob[:4] != b"MSCF":
        raise ValueError("signature is not MSCF")
    (cb_cabinet, coff_files, ver_min, ver_maj, n_folders, n_files,
     flags) = struct.unpack_from("<4xIxxxxI4xBBHHH", blob, 4)
    if cb_cabinet != len(blob):
        raise ValueError(f"header size {cb_cabinet} != file size {len(blob)}")
    if (ver_maj, ver_min) != (1, 3):
        raise ValueError(f"unexpected format version {ver_maj}.{ver_min}")
    if flags != 0:
        raise ValueError(f"unexpected header flags 0x{flags:x}")

    folders = []
    off = 36
    for _ in range(n_folders):
        coff_start, n_data, type_comp = struct.unpack_from("<IHH", blob, off)
        if type_comp != 0:
            raise ValueError(f"folder compression {type_comp}, expected none")
        folders.append((coff_start, n_data))
        off += 8

    streams = []
    for coff_start, n_data in folders:
        pos, parts = coff_start, []
        for _ in range(n_data):
            csum, cb_data, cb_uncomp = struct.unpack_from("<IHH", blob, pos)
            payload = blob[pos + 8:pos + 8 + cb_data]
            if len(payload) != cb_data or cb_data != cb_uncomp or cb_data > BLOCK:
                raise ValueError(f"bad CFDATA block at {pos}")
            want = cab_checksum(struct.pack("<HH", cb_data, cb_uncomp),
                                cab_checksum(payload))
            if csum != want:
                raise ValueError(f"CFDATA checksum mismatch at {pos}")
            parts.append(payload)
            pos += 8 + cb_data
        streams.append(b"".join(parts))

    files = {}
    off = coff_files
    for _ in range(n_files):
        cb_file, uoff, i_folder = struct.unpack_from("<IIH", blob, off)
        end = blob.index(b"\0", off + 16)
        name = blob[off + 16:end].decode("utf-8")
        data = streams[i_folder][uoff:uoff + cb_file]
        if len(data) != cb_file:
            raise ValueError(f"{name}: data out of folder range")
        files[name] = data
        off = end + 1
    return files


def main():
    if len(sys.argv) != 2:
        fail("usage: test_roundtrip.py <path-to-lcab>")
    lcab = sys.argv[1]

    base = os.environ.get("TMPDIR") or os.path.join(os.path.expanduser("~"), "tmp")
    os.makedirs(base, exist_ok=True)
    work = tempfile.mkdtemp(prefix="lcab-roundtrip-", dir=base)
    try:
        os.chdir(work)
        rng = random.Random(20260924)
        tree = {
            "project/README.txt": b"HarmonyOS PC delivery bundle\n",
            "project/docs/\u8bf4\u660e.txt": "\u9e3f\u8499 PC \u6253\u5305\u8bf4\u660e\n".encode("utf-8"),
            "project/bin/payload.dat": bytes(rng.getrandbits(8) for _ in range(3 * BLOCK + 1234)),
            "project/bin/zeros.bin": b"\0" * 4096 + b"tail-after-nul",
        }
        for rel, data in tree.items():
            os.makedirs(os.path.dirname(rel), exist_ok=True)
            with open(rel, "wb") as fh:
                fh.write(data)

        proc = subprocess.run([lcab, "-r", "-q", "project", "bundle.cab"],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if proc.returncode != 0:
            fail(f"lcab -r returned {proc.returncode}: {proc.stdout.decode(errors='replace')}")
        with open("bundle.cab", "rb") as fh:
            blob = fh.read()
        print(f"OK: lcab -r packed {len(tree)} files into {len(blob)} bytes")

        try:
            got = read_cab(blob)
        except ValueError as exc:
            fail(f"cabinet does not parse: {exc}")
        n_blocks = struct.unpack_from("<H", blob, 36 + 4)[0]
        print(f"OK: MSCF header, 1 folder, {n_blocks} CFDATA blocks, all checksums valid")

        expected = {rel.replace("/", "\\"): data for rel, data in tree.items()}
        if set(got) != set(expected):
            fail(f"stored names {sorted(got)} != expected {sorted(expected)}")
        for name, data in expected.items():
            if hashlib.sha256(got[name]).digest() != hashlib.sha256(data).digest():
                fail(f"{name}: extracted bytes differ from original")
        print("OK: every file extracted byte-for-byte (UTF-8 name, NUL data, multi-block file)")

        corrupt = bytearray(blob)
        corrupt[-100] ^= 0xFF
        try:
            read_cab(bytes(corrupt))
        except ValueError:
            print("OK: single-byte corruption rejected by checksum")
        else:
            fail("corrupted cabinet was accepted")
    finally:
        os.chdir(base)
        shutil.rmtree(work, ignore_errors=True)
    print("LCAB ROUNDTRIP CONSUMER TEST PASSED")


if __name__ == "__main__":
    main()
