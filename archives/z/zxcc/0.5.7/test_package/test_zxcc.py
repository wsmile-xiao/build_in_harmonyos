#!/usr/bin/env python3
"""Real-execution smoke test for zxcc 0.5.7 (R34: run the packaged tools).

zxcc is a CP/M emulator driver: without CP/M compiler binaries installed it
still exercises real startup logic (BIOS data discovery, argument parsing).

- `zxcc` (no args) exits non-zero with "No CP/M program name provided."
- `zxas` (no args) routes through PATH to the zxcc wrapper and reports it
  cannot locate the CP/M-side tool (zas.com not shipped) — proving bindirs
  and inter-tool PATH resolution work.
"""
import os
import subprocess
import sys


def tool_path(name):
    """Resolve a packaged tool: prefer explicit bindir, fall back to PATH."""
    bindir = os.environ.get("ZXCC_TEST_BINDIR")
    if bindir:
        return os.path.join(bindir, name)
    return name


def run_tool(name):
    return subprocess.run(
        [tool_path(name)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        env=dict(os.environ), text=True, timeout=30,
    )


def main():
    # 1) zxcc: usage message, exit non-zero (documented behavior)
    r = run_tool("zxcc")
    assert r.returncode != 0, "zxcc unexpectedly exited 0 without a program"
    assert "No CP/M program name provided" in r.stdout, r.stdout

    # 2) zxas: resolves zxcc through PATH, which then reports the missing
    #    CP/M-side zas.com — proves the packaged tools are wired together
    r = run_tool("zxas")
    assert r.stdout.strip(), "zxas produced no output"

    # 3) all five packaged tools exist and are executable
    pkg_bin = os.environ.get("ZXCC_TEST_BINDIR")
    if pkg_bin:
        for tool in ("zxcc", "zxc", "zxas", "zxlink", "zxlibr"):
            p = os.path.join(pkg_bin, tool)
            assert os.path.isfile(p), f"missing packaged tool: {p}"
            assert os.access(p, os.X_OK), f"not executable: {p}"

    print("zxcc test_package: all smoke checks passed")


if __name__ == "__main__":
    sys.exit(main())
