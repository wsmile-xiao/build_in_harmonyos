#!/usr/bin/env python3
"""Smoke test for the packaged nextvi executable."""
import os
import subprocess
import sys


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_nextvi.py <path-to-vi>")
    vi = sys.argv[1]
    if not os.path.isfile(vi):
        raise SystemExit(f"missing nextvi executable: {vi}")

    completed = subprocess.run(
        [vi, "-s"],
        input="q\n",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(
            "nextvi smoke failed with rc={}\nstdout:\n{}\nstderr:\n{}".format(
                completed.returncode,
                completed.stdout,
                completed.stderr,
            )
        )


if __name__ == "__main__":
    main()
