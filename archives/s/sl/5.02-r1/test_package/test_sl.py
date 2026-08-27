#!/usr/bin/env python3
"""test_sl.py — Smoke test for sl (Steam Locomotive) binary.

Verifies the sl binary exists, is executable, and links ncurses correctly.
Since sl requires a terminal, we run it with TERM=dumb which causes a
graceful error exit — proving the binary runs and ncurses is linked.
"""
import os
import sys
import subprocess
import signal


def main():
    # Find sl binary in PATH
    sl_path = None
    for d in os.environ.get("PATH", "").split(":"):
        p = os.path.join(d, "sl")
        if os.path.isfile(p) and os.access(p, os.X_OK):
            sl_path = p
            break

    if not sl_path:
        print("FAIL: sl binary not found in PATH", file=sys.stderr)
        sys.exit(1)

    print(f"Found sl binary: {sl_path}")

    # Run sl with TERM=dumb — it will try initscr() and exit gracefully.
    # A non-zero exit is expected (no terminal), but signals (crashes) are failures.
    env = os.environ.copy()
    env["TERM"] = "dumb"
    result = subprocess.run([sl_path], env=env, timeout=5, capture_output=True)

    # Check for signal termination (crash) — negative returncode means killed by signal
    if result.returncode < 0:
        sig = -result.returncode
        print(f"FAIL: sl terminated by signal {sig} ({signal.Signals(sig).name})", file=sys.stderr)
        sys.exit(1)

    # Check for dynamic load failure (127 = command not found / lib load error)
    if result.returncode == 127:
        print("FAIL: sl failed to load (exit 127 — dynamic library error)", file=sys.stderr)
        sys.exit(1)

    print(f"OK: sl exited with code {result.returncode} (expected non-zero without terminal)")
    sys.exit(0)


if __name__ == "__main__":
    main()
