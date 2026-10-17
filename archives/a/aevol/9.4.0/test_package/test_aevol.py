#!/usr/bin/env python3
"""Functional smoke test for the packaged aevol binaries.

Runs aevol_create_2b with the bundled example parameter file (creates the
initial population) and verifies the version output. Exercises the real
binary (R34).
"""
import os
import subprocess
import sys
import tempfile


def run(exe, args, cwd=None):
    return subprocess.run([exe] + args, cwd=cwd, capture_output=True,
                          text=True, timeout=120)


def main():
    bin_dir = sys.argv[1] if len(sys.argv) > 1 else "bin"
    param = sys.argv[2] if len(sys.argv) > 2 else "param.in"
    create = os.path.join(bin_dir, "aevol_create_2b")
    if not os.path.isfile(create):
        print(f"FAIL: binary not found: {create}")
        return 1

    passed = 0

    # 1. version output
    r = run(create, ["--version"])
    assert r.returncode == 0, f"aevol_create_2b --version rc={r.returncode}: {r.stderr}"
    assert "9.4.0" in r.stdout, f"version mismatch: {r.stdout!r}"
    passed += 1

    # 2. create an initial population from the bundled param file
    with tempfile.TemporaryDirectory() as td:
        r = run(create, [param], cwd=td)
        assert r.returncode == 0, f"aevol_create_2b param rc={r.returncode}: {r.stderr}"
        # aevol_create writes the initial population as a "checkpoints" dir
        # plus a "last_gener.txt" file in the working directory.
        produced = (
            os.path.isdir(os.path.join(td, "checkpoints"))
            or os.path.isfile(os.path.join(td, "last_gener.txt"))
        )
        assert produced, f"aevol_create produced no population files in {td}"
        passed += 1

    print(f"aevol smoke test: {passed}/2 assertions passed")
    return 0 if passed >= 2 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}")
        sys.exit(1)
