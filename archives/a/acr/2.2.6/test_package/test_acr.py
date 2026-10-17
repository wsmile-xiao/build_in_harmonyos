#!/usr/bin/env python3
"""Runtime and fault-injection checks for packaged ACR."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile


def run(command: list[str], cwd: str | None = None) -> subprocess.CompletedProcess[str]:
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

    version = run([executable, "-v"])
    assert version.returncode == 0, version.stdout
    assert "2.2.6" in version.stdout, version.stdout

    with tempfile.TemporaryDirectory(prefix="acr-conan-") as work:
        config = os.path.join(work, "configure.acr")
        with open(config, "w", encoding="utf-8") as stream:
            stream.write("PKGNAME sample\nVERSION 1.0\n")
        generated = run([executable], cwd=work)
        assert generated.returncode == 0, generated.stdout
        configure = os.path.join(work, "configure")
        assert os.path.isfile(configure), "acr did not generate configure"
        configured = run(["sh", configure], cwd=work)
        assert configured.returncode == 0, configured.stdout

        missing = run([executable, "does-not-exist.acr"], cwd=work)
        assert missing.returncode != 0, "missing input must fail"

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
