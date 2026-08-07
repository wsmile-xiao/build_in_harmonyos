#!/usr/bin/env python3
"""Create/inspect and negative-path tests for packaged abootimg."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile


def run(command: list[str], cwd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=20,
        check=False,
    )


def main() -> int:
    executable = os.path.abspath(sys.argv[1])
    with tempfile.TemporaryDirectory(prefix="abootimg-conan-") as work:
        kernel = os.path.join(work, "kernel.bin")
        ramdisk = os.path.join(work, "ramdisk.bin")
        image = os.path.join(work, "boot.img")
        invalid = os.path.join(work, "invalid.img")
        with open(kernel, "wb") as stream:
            stream.write(b"OHOS-KERNEL-TEST\n")
        with open(ramdisk, "wb") as stream:
            stream.write(b"OHOS-RAMDISK-TEST\n")
        with open(invalid, "wb") as stream:
            stream.write(b"not an android boot image")

        created = run([executable, "--create", image, "-k", kernel, "-r", ramdisk], work)
        assert created.returncode == 0, created.stdout
        assert os.path.getsize(image) > os.path.getsize(kernel) + os.path.getsize(ramdisk)

        info = run([executable, "-i", image], work)
        assert info.returncode == 0, info.stdout
        assert "Android Boot Image Info" in info.stdout, info.stdout

        rejected = run([executable, "-i", invalid], work)
        assert rejected.returncode != 0, rejected.stdout

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
