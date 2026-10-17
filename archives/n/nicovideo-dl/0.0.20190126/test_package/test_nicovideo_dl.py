#!/usr/bin/env python3
"""Offline consumer checks for the installed nicovideo-dl package."""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def run_tool(tool, *args):
    return subprocess.run(
        [sys.executable, str(tool), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


if len(sys.argv) != 2:
    raise SystemExit("usage: test_nicovideo_dl.py <package-folder>")

package_folder = Path(sys.argv[1])
tool = package_folder / "bin" / "nicovideo-dl"
assert tool.is_file(), f"packaged command is missing: {tool}"

if os.name != "nt":
    discovered = shutil.which("nicovideo-dl")
    assert discovered is not None, "package bin directory is missing from PATH"
    assert Path(discovered).resolve() == tool.resolve(), (
        f"PATH resolved to {discovered}, expected {tool}"
    )

version = run_tool(tool, "--version")
assert version.returncode == 0, version.stderr
assert version.stdout.strip() == "2011.02.08", version.stdout

help_result = run_tool(tool, "--help")
assert help_result.returncode == 0, help_result.stderr
assert "Usage: nicovideo-dl [options] video_url" in help_result.stdout
assert "-g, --get-url" in help_result.stdout

invalid = run_tool(
    tool,
    "--quiet",
    "--get-url",
    "https://www.nicovideo.jp/watch/sm9",
)
assert invalid.returncode != 0, invalid.stdout
assert "cannot be quiet and print final URL at the same time" in invalid.stderr

print("nicovideo-dl consumer checks passed")
