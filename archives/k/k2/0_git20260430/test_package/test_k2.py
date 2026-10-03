#!/usr/bin/env python3
"""Consumer-level UCI protocol tests for the packaged k2 binary.

k2 has no CLI flags; it speaks the UCI protocol on stdin/stdout. Each case
feeds a UCI command file into the packaged binary and asserts that the
protocol answer appears on stdout (the binary's own exit status is not part
of the assertion: k2 terminates via an uncaught exception after stdin EOF,
which is upstream behaviour on every platform — see notes.md).

Usage: test_k2.py <path-to-k2-binary>
"""
import os
import subprocess
import sys

CASES = [
    ("uci.txt", "uciok", "UCI handshake"),
    ("isready.txt", "readyok", "readiness check"),
    ("search.txt", "bestmove", "search from the start position"),
]

TIMEOUT = 300


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {os.path.basename(sys.argv[0])} <k2-binary>", file=sys.stderr)
        return 2
    binary = sys.argv[1]
    if not os.path.isfile(binary):
        print(f"FAIL: packaged binary not found: {binary}", file=sys.stderr)
        return 1

    here = os.path.dirname(os.path.abspath(__file__))
    failures = []
    for input_name, expect, label in CASES:
        with open(os.path.join(here, input_name), "rb") as fin:
            proc = subprocess.run(
                [binary],
                stdin=fin,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=TIMEOUT,
            )
        if expect.encode() not in proc.stdout:
            failures.append(f"  - {label}: expected '{expect}' in stdout, got "
                            f"{proc.stdout[:200]!r}")
        else:
            print(f"ok: {label} answered '{expect}'")

    if failures:
        print("k2 UCI tests failed:", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"k2 UCI tests: {len(CASES)}/{len(CASES)} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
