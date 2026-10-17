#!/usr/bin/env python3
"""Direct consumer assertions used by the Conan test_package."""

import subprocess


def run(command):
    return subprocess.run(command, shell=True, check=True, text=True, capture_output=True)


def main():
    help_output = run("lsb_release -h").stdout
    assert "Usage" in help_output or "usage" in help_output
    distributor = run("lsb_release -i -s").stdout.strip()
    assert distributor
    assert run("python3 -c \"import lsb_release, initdutils\"").returncode == 0
    print("lsb consumer assertions passed")


if __name__ == "__main__":
    main()
