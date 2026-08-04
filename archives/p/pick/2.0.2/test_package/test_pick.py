#!/usr/bin/env python3
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: test_pick.py <pick-executable>", file=sys.stderr)
        return 2

    exe = sys.argv[1]
    result = subprocess.run(
        [exe, "-v"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output = result.stdout.strip()
    if result.returncode != 0:
        print(output)
        print(f"pick -v failed with rc={result.returncode}", file=sys.stderr)
        return 1
    if output != "2.0.2":
        print(output)
        print("unexpected pick version output", file=sys.stderr)
        return 1

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
