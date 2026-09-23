#!/usr/bin/env python3
"""Verify the HarmonyOS writable-TMPDIR adaptation."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def run(runner, environment):
    return subprocess.run(
        [*runner, "-h"],
        env=environment,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def main():
    runner = sys.argv[1:]
    check(bool(runner), "missing cutmp3 command")

    with tempfile.TemporaryDirectory(
        prefix="cutmp3-ohos-", dir=os.environ.get("TMPDIR")
    ) as directory:
        root = Path(directory)
        writable = root / "writable-tmp"
        writable.mkdir()
        valid_environment = os.environ.copy()
        valid_environment["TMPDIR"] = str(writable)

        valid_result = run(runner, valid_environment)
        check(valid_result.returncode == 0, "private TMPDIR execution failed")
        check("cutmp3  version 4.0" in valid_result.stdout, "help output missing")
        check(not list(writable.iterdir()), "temporary logfile was not cleaned")

        invalid_environment = os.environ.copy()
        invalid_environment["TMPDIR"] = str(root / "missing-tmp")
        invalid_result = run(runner, invalid_environment)
        check(invalid_result.returncode == 11, "invalid TMPDIR was not rejected")
        check(
            "failed writing temporary logfile" in invalid_result.stdout,
            "TMPDIR failure diagnostic missing",
        )

    print("cutmp3 HarmonyOS TMPDIR assertions: 5 passed")


if __name__ == "__main__":
    main()
