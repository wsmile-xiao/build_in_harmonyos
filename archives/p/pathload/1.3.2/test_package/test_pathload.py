#!/usr/bin/env python3
"""Runtime smoke tests for the packaged pathload tools."""

import os
import subprocess
import sys


def run_checked(command, expected_returncode=None):
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
    )
    output = result.stdout + result.stderr
    if expected_returncode is not None and result.returncode != expected_returncode:
        raise AssertionError(
            f"{command[0]} returned {result.returncode}, expected {expected_returncode}\n{output}"
        )
    return result.returncode, output


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    snd, rcv = sys.argv[1], sys.argv[2]

    require(os.path.isfile(snd), "pathload_snd executable is missing")
    require(os.path.isfile(rcv), "pathload_rcv executable is missing")

    _, snd_help = run_checked([snd, "-h"], expected_returncode=0)
    require("usage: pathload_snd" in snd_help, "pathload_snd -h did not print usage")

    _, rcv_help = run_checked([rcv, "-h"], expected_returncode=0)
    require("usage: pathload_rcv" in rcv_help, "pathload_rcv -h did not print usage")
    require("-s <sender>" in rcv_help, "pathload_rcv help omits sender option")

    _, invalid_output = run_checked([rcv], expected_returncode=0)
    require("usage: pathload_rcv" in invalid_output, "pathload_rcv without sender did not show usage")


if __name__ == "__main__":
    main()
