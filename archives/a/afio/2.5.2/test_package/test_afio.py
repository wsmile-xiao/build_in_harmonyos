#!/usr/bin/env python3
"""Round-trip and corrupt-input checks for packaged afio."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile


def run(command: list[str], cwd: str, input_text: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        input=input_text,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=30,
        check=False,
    )


def main() -> int:
    executable = os.path.abspath(sys.argv[1])
    with tempfile.TemporaryDirectory(prefix="afio-conan-") as work:
        source_dir = os.path.join(work, "source")
        extract_dir = os.path.join(work, "extract")
        os.mkdir(source_dir)
        os.mkdir(extract_dir)
        payload = "HarmonyOS afio deterministic payload\n"
        with open(os.path.join(source_dir, "payload.txt"), "w", encoding="utf-8") as stream:
            stream.write(payload)
        archive = os.path.join(work, "archive.af")

        created = run([executable, "-o", archive], source_dir, "payload.txt\n")
        assert created.returncode == 0, created.stdout
        assert os.path.getsize(archive) > 0

        extracted = run([executable, "-i", archive], extract_dir)
        assert extracted.returncode == 0, extracted.stdout
        with open(os.path.join(extract_dir, "payload.txt"), encoding="utf-8") as stream:
            assert stream.read() == payload

        corrupt = os.path.join(work, "corrupt.af")
        with open(corrupt, "wb") as stream:
            stream.write(b"corrupt archive")
        rejected = run([executable, "-i", corrupt], extract_dir)
        assert rejected.returncode != 0, rejected.stdout

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
