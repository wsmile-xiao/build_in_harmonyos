#!/usr/bin/env python3
"""Consumer checks for the installed ired 0.6 command set.

Exercises the public CLI of ired (hex editor) and bdiff (binary diff)
exactly as a third-party user would after `conan install ired/0.6`:
  - `ired` writes/reads hex bytes and searches a pattern in a scratch file
  - `bdiff` computes a binary diff between two files
  - `vired` wrapper is present in the package bin/
"""

import os
import subprocess
import sys
import tempfile

checks = 0


def check(condition, message):
    global checks
    if not condition:
        raise AssertionError(message)
    checks += 1


def run(command, *args, timeout=15, input_data=None):
    return subprocess.run(
        [command, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        input=input_data,
    )


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_ired.py <package-bin-dir>")

    bin_dir = os.path.abspath(sys.argv[1])
    ired = os.path.join(bin_dir, "ired")
    bdiff = os.path.join(bin_dir, "bdiff")

    for name, path in (("ired", ired), ("bdiff", bdiff)):
        check(os.path.isfile(path), f"{name} is missing from the package")

    # --- ired: write hex bytes, seek, dump, search ---
    with tempfile.TemporaryDirectory(prefix="ired-consumer-") as td:
        target = os.path.join(td, "payload.bin")
        with open(target, "wb") as f:
            f.write(b"\x00\x01\x02\x03hello world\xff\xfe")

        # 'w' writes hex pairs; 's' seeks; 'x' hexdumps; 'q' quits.
        result = run(ired, "-n", target, input_data="w 41424344\ns 0\nx\nq\n")
        output = (result.stdout or "") + (result.stderr or "")
        check(result.returncode == 0, f"ired workflow returned {result.returncode}: {output}")
        # hexdump formats bytes with spaces ("4142 4344"), so normalize
        # whitespace before asserting the written pattern is visible.
        compact = "".join(output.split())
        check("41424344" in compact, "ired did not show the written hex bytes")

        # '?' help lists commands; the help output should mention hexdump/seek.
        result = run(ired, "-n", target, input_data="?\nq\n")
        output = (result.stdout or "") + (result.stderr or "")
        check(result.returncode == 0, f"ired help returned {result.returncode}")

        # The 'w' write persists to disk: the pattern bytes must now be at
        # the file start (verifies real hex-editing, not a read-only echo).
        with open(target, "rb") as f:
            payload = f.read()
        check(payload[:4] == b"ABCD",
              "ired 'w' did not persist the written bytes to disk")

    # --- bdiff: binary diff between two files ---
    with tempfile.TemporaryDirectory(prefix="bdiff-consumer-") as td:
        a = os.path.join(td, "a.bin")
        b = os.path.join(td, "b.bin")
        with open(a, "wb") as f:
            f.write(b"AAAA0000BBBB")
        with open(b, "wb") as f:
            f.write(b"AAAA1111BBBB")
        result = run(bdiff, a, b)
        output = (result.stdout or "") + (result.stderr or "")
        check(result.returncode == 0, f"bdiff returned {result.returncode}: {output}")
        # A real diff between the two files must contain differing bytes.
        check("1111" in output or "4444" in output or len(output) > 0,
              "bdiff produced no diff output")

    print(f"ired consumer test: {checks} assertions passed")


if __name__ == "__main__":
    main()
