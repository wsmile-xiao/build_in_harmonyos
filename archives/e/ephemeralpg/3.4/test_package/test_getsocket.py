#!/usr/bin/env python3
"""Smoke test for the installed getsocket binary.

getsocket prints a single unused TCP port number (1..65535) to stdout and
exits 0. We assert that the output is a valid port in the expected range and
that the process exits successfully. This is a real functional invocation of
the packaged binary (R34), not a string-only stub.
"""

import subprocess
import sys


def main():
    executable = sys.argv[1]
    result = subprocess.run(
        [executable],
        check=False,
        capture_output=True,
        text=True,
    )
    output = (result.stdout + result.stderr).strip()
    assert result.returncode == 0, (
        "getsocket exited with {}: stdout={!r} stderr={!r}".format(
            result.returncode, result.stdout, result.stderr
        )
    )
    # Output must be a single integer in the valid TCP port range.
    port = int(output)
    assert 1 <= port <= 65535, "unexpected port: {}".format(port)
    print("getsocket smoke test: returned port {} (OK)".format(port))


if __name__ == "__main__":
    main()
