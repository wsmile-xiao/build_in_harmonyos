#!/usr/bin/env python3
"""Consumer smoke test for the packaged minizign CLI."""

import os
import subprocess
import sys
import tempfile


def run(command, **kwargs):
    return subprocess.run(command, check=True, text=True, **kwargs)


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: test_minizign.py <minizign> <workdir>")

    minizign = sys.argv[1]
    workdir = tempfile.mkdtemp(prefix="minizign-test-", dir=sys.argv[2])

    version = run([minizign, "--version"], capture_output=True)
    if "minizign 0.1.13" not in version.stdout:
        raise AssertionError(f"unexpected minizign version output: {version.stdout!r}")

    message = os.path.join(workdir, "message.txt")
    secret_key = os.path.join(workdir, "minizign.key")
    public_key = os.path.join(workdir, "minizign.pub")
    signature = os.path.join(workdir, "message.txt.minisig")

    with open(message, "w", encoding="utf-8") as file:
        file.write("minizign conan test package\n")

    run([minizign, "-G", "-s", secret_key, "-p", public_key], input="\n")
    if not os.path.exists(secret_key) or not os.path.exists(public_key):
        raise AssertionError("minizign did not generate key files")

    run([minizign, "-S", "-s", secret_key, "-m", message, "-o", signature], input="\n")
    if not os.path.exists(signature):
        raise AssertionError("minizign did not create a signature file")

    run([minizign, "-V", "-p", public_key, "-m", message, "-o", signature])


if __name__ == "__main__":
    main()
