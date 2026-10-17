#!/usr/bin/env python3
"""Black-box behavioral tests for xva-img 1.5."""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


MASK64 = (1 << 64) - 1
P1 = 11400714785074694791
P2 = 14029467366897019727
P3 = 1609587929392839161
P4 = 9650029242287828579
P5 = 2870177450012600261
CHUNK_SIZE = 1024 * 1024


def _rotl(value, count):
    return ((value << count) | (value >> (64 - count))) & MASK64


def _round(acc, lane):
    acc = (acc + lane * P2) & MASK64
    acc = _rotl(acc, 31)
    return (acc * P1) & MASK64


def _merge_round(acc, value):
    acc ^= _round(0, value)
    return (acc * P1 + P4) & MASK64


def xxhash64(data):
    """Small independent XXH64 reference used only to produce fixture files."""
    length = len(data)
    offset = 0
    if length >= 32:
        v1 = (P1 + P2) & MASK64
        v2 = P2
        v3 = 0
        v4 = (-P1) & MASK64
        limit = length - 32
        while offset <= limit:
            v1 = _round(v1, int.from_bytes(data[offset : offset + 8], "little"))
            v2 = _round(v2, int.from_bytes(data[offset + 8 : offset + 16], "little"))
            v3 = _round(v3, int.from_bytes(data[offset + 16 : offset + 24], "little"))
            v4 = _round(v4, int.from_bytes(data[offset + 24 : offset + 32], "little"))
            offset += 32
        result = (
            _rotl(v1, 1) + _rotl(v2, 7) + _rotl(v3, 12) + _rotl(v4, 18)
        ) & MASK64
        result = _merge_round(result, v1)
        result = _merge_round(result, v2)
        result = _merge_round(result, v3)
        result = _merge_round(result, v4)
    else:
        result = P5

    result = (result + length) & MASK64
    while offset + 8 <= length:
        lane = _round(0, int.from_bytes(data[offset : offset + 8], "little"))
        result ^= lane
        result = (_rotl(result, 27) * P1 + P4) & MASK64
        offset += 8
    if offset + 4 <= length:
        lane = int.from_bytes(data[offset : offset + 4], "little")
        result ^= (lane * P1) & MASK64
        result = (_rotl(result, 23) * P2 + P3) & MASK64
        offset += 4
    while offset < length:
        result ^= (data[offset] * P5) & MASK64
        result = (_rotl(result, 11) * P1) & MASK64
        offset += 1

    result ^= result >> 33
    result = (result * P2) & MASK64
    result ^= result >> 29
    result = (result * P3) & MASK64
    result ^= result >> 32
    return "{:016X}".format(result)


class Checks:
    def __init__(self):
        self.count = 0

    def expect(self, condition, message):
        self.count += 1
        if not condition:
            raise RuntimeError("assertion {} failed: {}".format(self.count, message))


def run(binary, args, cwd, expected, checks, label):
    result = subprocess.run(
        [binary] + args,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    checks.expect(
        result.returncode == expected,
        "{}: exit {} (expected {}), stdout={!r}, stderr={!r}".format(
            label, result.returncode, expected, result.stdout, result.stderr
        ),
    )
    return result


def harmonyos_checks(binary, checks):
    system = platform.uname().system
    machine = platform.machine().lower()
    checks.expect(system == "HarmonyOS", "uname system must identify HarmonyOS, got {!r}".format(system))
    checks.expect(machine in ("aarch64", "arm64"), "runtime machine must be aarch64, got {!r}".format(machine))

    readelf = shutil.which("readelf") or "/data/service/hnp/bin/readelf"
    result = subprocess.run(
        [readelf, "-h", binary], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    checks.expect(
        result.returncode == 0 and "AArch64" in result.stdout,
        "readelf must identify an AArch64 ELF: {}".format(result.stderr),
    )


def main():
    if len(sys.argv) not in (3, 4):
        raise SystemExit("usage: test_xva_img.py <binary> <work-dir> [--harmonyos]")
    binary = str(Path(sys.argv[1]).resolve())
    workdir = Path(sys.argv[2]).resolve()
    harmonyos = len(sys.argv) == 4 and sys.argv[3] == "--harmonyos"
    checks = Checks()

    if workdir.exists():
        shutil.rmtree(str(workdir))
    workdir.mkdir(parents=True)

    version = run(binary, ["--version"], workdir, 0, checks, "version")
    checks.expect("1.5.0" in version.stdout, "version output must contain 1.5.0")

    raw = bytes((index * 17 + 3) & 0xFF for index in range(CHUNK_SIZE * 2))
    raw_path = workdir / "disk.raw"
    raw_path.write_bytes(raw)
    sha_dir = workdir / "sha1-disk"
    sha_dir.mkdir()
    run(binary, ["disk-import", str(sha_dir), str(raw_path)], workdir, 0, checks, "disk-import")
    chunks = sorted(path.name for path in sha_dir.iterdir() if path.name[:8].isdigit() and len(path.name) >= 8)
    checks.expect(chunks == ["00000000", "00000000.checksum", "00000001", "00000001.checksum"], "disk-import must write two chunks and SHA1 sidecars")
    exported = workdir / "disk-export.raw"
    run(binary, ["disk-export", str(sha_dir), str(exported)], workdir, 0, checks, "disk-export SHA1")
    checks.expect(exported.read_bytes() == raw, "SHA1 import/export must round-trip exact bytes")

    checksum_path = sha_dir / "00000000.checksum"
    original_checksum = checksum_path.read_bytes()
    checksum_path.write_text("invalid-checksum", encoding="ascii")
    run(binary, ["disk-export", str(sha_dir), str(workdir / "bad.raw")], workdir, 1, checks, "reject invalid SHA1")
    ignored = run(binary, ["--ignore-checksum", "disk-export", str(sha_dir), str(workdir / "ignored.raw")], workdir, 0, checks, "ignore invalid SHA1")
    checks.expect((workdir / "ignored.raw").read_bytes() == raw, "ignore-checksum must still export the original bytes")
    checks.expect("invalid sha1 checksum" in ignored.stderr, "ignore-checksum must warn about the invalid digest")
    checksum_path.write_bytes(original_checksum)

    vector = xxhash64(b"")
    checks.expect(vector == "EF46DB3751D8E999", "independent XXH64 helper must pass the empty-input known vector")
    xxh_chunk = raw[:CHUNK_SIZE]
    xxh_dir = workdir / "xxhash-disk"
    xxh_dir.mkdir()
    (xxh_dir / "00000000").write_bytes(xxh_chunk)
    (xxh_dir / "00000000.xxhash").write_text(xxhash64(xxh_chunk), encoding="ascii")
    xxh_export = workdir / "xxhash-export.raw"
    run(binary, ["disk-export", str(xxh_dir), str(xxh_export)], workdir, 0, checks, "disk-export XXH64")
    checks.expect(xxh_export.read_bytes() == xxh_chunk, "valid XXH64 fixture must export exact bytes")

    if harmonyos:
        harmonyos_checks(binary, checks)

    print("xva-img consumer tests passed: {} assertions".format(checks.count))


if __name__ == "__main__":
    main()
