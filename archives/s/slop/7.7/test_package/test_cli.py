#!/usr/bin/env python3
"""Behavior checks for the packaged slop executable."""

import os
import subprocess
import sys


def run(command, env=None):
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    runner = sys.argv[1:-1]
    binary = sys.argv[-1]

    version = run(runner + [binary, "--version"])
    require(version.returncode == 0, f"--version rc={version.returncode}")
    require(version.stdout.strip() == "v7.7", version.stdout + version.stderr)

    help_result = run(runner + [binary, "--help"])
    require(help_result.returncode == 0, f"--help rc={help_result.returncode}")
    require("Usage: slop [options]" in help_result.stdout, help_result.stdout)
    require("--noopengl" in help_result.stdout, help_result.stdout)

    clean_env = dict(os.environ)
    clean_env.pop("DISPLAY", None)
    clean_env.pop("XAUTHORITY", None)
    clean_env.pop("HOME", None)
    clean_env.pop("XDG_CONFIG_HOME", None)
    no_display = run(runner + [binary], env=clean_env)
    require(no_display.returncode == 1, f"no-display rc={no_display.returncode}")
    require(
        "Error: Failed to open X display: :0" in no_display.stderr,
        no_display.stdout + no_display.stderr,
    )

    print("slop CLI behavior: PASS")


if __name__ == "__main__":
    main()
