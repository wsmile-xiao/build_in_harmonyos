#!/usr/bin/env python3
"""Functional smoke tests for the packaged aeskeyfind executable."""
import os
import subprocess
import sys
import tempfile


EXPECTED_AES128_KEY = "000102030405060708090a0b0c0d0e0f"

AES128_KEY_SCHEDULE_HEX = """
000102030405060708090a0b0c0d0e0f
d6aa74fdd2af72fadaa678f1d6ab76fe
b692cf0b643dbdf1be9bc5006830b3fe
b6ff744ed2c2c9bf6c590cbf0469bf41
47f7f7bc95353e03f96c32bcfd058dfd
3caaa3e8a99f9deb50f3af57adf622aa
5e390f7df7a69296a7553dc10aa31f6b
14f9701ae35fe28c440adf4d4ea9c026
47438735a41c65b9e016baf4aebf7ad2
549932d1f08557681093ed9cbe2c974e
13111d7fe3944a17f307a78b4d2b30c5
""".replace("\n", "")


def run_command(args):
    return subprocess.run(args, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)


def assert_usage(aeskeyfind):
    result = run_command([aeskeyfind, "-h"])
    output = result.stdout + result.stderr
    if "Usage: aeskeyfind" not in output:
        raise AssertionError("help output did not contain usage text")


def assert_small_image_error(aeskeyfind, workdir):
    path = os.path.join(workdir, "small-memory.bin")
    with open(path, "wb") as handle:
        handle.write(b"too small")
    result = run_command([aeskeyfind, "-q", path])
    if result.returncode == 0:
        raise AssertionError("small memory image unexpectedly succeeded")
    if "memory image too small" not in result.stderr:
        raise AssertionError("small image error message was not reported")


def assert_recovers_known_key(aeskeyfind, workdir):
    path = os.path.join(workdir, "aes128-memory.bin")
    schedule = bytes.fromhex(AES128_KEY_SCHEDULE_HEX)
    suffix = bytes(((i * 37 + 11) & 0xff) for i in range(320))
    with open(path, "wb") as handle:
        handle.write(schedule)
        handle.write(suffix)

    result = run_command([aeskeyfind, "-q", "-t", "1", path])
    if result.returncode != 0:
        raise AssertionError(
            "aeskeyfind failed while scanning generated memory image:\n"
            + result.stderr
        )
    keys = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    if EXPECTED_AES128_KEY not in keys:
        raise AssertionError(
            "expected AES-128 key was not recovered; output was:\n"
            + result.stdout
        )


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_aeskeyfind.py <aeskeyfind-binary>")
    aeskeyfind = sys.argv[1]
    with tempfile.TemporaryDirectory(prefix="aeskeyfind-test-") as workdir:
        assert_usage(aeskeyfind)
        assert_small_image_error(aeskeyfind, workdir)
        assert_recovers_known_key(aeskeyfind, workdir)


if __name__ == "__main__":
    main()
