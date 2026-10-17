"""Exercise xplot's argument parser without requiring an X11 display."""

import os
import subprocess
import sys


def main():
    executable = sys.argv[1]
    environment = os.environ.copy()
    environment.pop("DISPLAY", None)

    result = subprocess.run(
        [executable, "-format"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        env=environment,
    )
    output = result.stdout + result.stderr

    assert "DISPLAY" not in environment, "the test must run with DISPLAY unset"
    assert result.returncode == 1, f"expected parser exit 1, got {result.returncode}: {output}"
    assert "missing format string after -format flag" in output, (
        f"xplot did not report the expected parser diagnostic: {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
