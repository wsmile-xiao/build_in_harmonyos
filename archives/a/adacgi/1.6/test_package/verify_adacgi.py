#!/usr/bin/env python3
"""Run the signed AdaCGI consumer with deterministic CGI input."""

import os
import subprocess
import sys


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_adacgi.py <test-adacgi-executable>")

    executable = sys.argv[1]
    if not os.path.isfile(executable):
        raise SystemExit("AdaCGI executable was not found: {}".format(executable))

    environment = os.environ.copy()
    environment.update(
        {
            "REQUEST_METHOD": "GET",
            "QUERY_STRING": "name=HarmonyOS&name=Ada%20CGI",
        }
    )
    try:
        completed = subprocess.run(
            [executable],
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise SystemExit("AdaCGI consumer timed out after 30 seconds") from error

    if completed.returncode != 0:
        raise SystemExit(
            "AdaCGI consumer failed with exit code {}:\n{}".format(
                completed.returncode,
                completed.stderr.strip(),
            )
        )
    if completed.stdout.strip() != "adacgi smoke: ok":
        raise SystemExit(
            "unexpected AdaCGI output: {!r}".format(completed.stdout)
        )

    print("ADACGI_LINKAGE=pass assertions=9")


if __name__ == "__main__":
    main()
