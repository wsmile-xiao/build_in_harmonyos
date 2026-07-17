#!/usr/bin/env python3
"""Runtime checks for the tmux-mem-cpu-load packaged executable."""
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: test_cli.py <tmux-mem-cpu-load>", file=sys.stderr)
        return 2

    binary = sys.argv[1]
    result = subprocess.run(
        [binary, "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    if result.returncode < 0:
        print(f"binary crashed with signal {-result.returncode} on --help", file=sys.stderr)
        print(output, file=sys.stderr)
        return 1
    if "Usage: tmux-mem-cpu-load" not in output:
        print(output, file=sys.stderr)
        return 1

    # Exercise the default path. Upstream may return non-zero outside tmux,
    # but signal termination still indicates a runtime crash.
    default_result = subprocess.run([binary], check=False)
    if default_result.returncode < 0:
        print(f"binary crashed with signal {-default_result.returncode}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
