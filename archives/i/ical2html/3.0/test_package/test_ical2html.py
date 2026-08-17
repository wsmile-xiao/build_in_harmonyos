#!/usr/bin/env python3

import subprocess
import sys


def main():
    if len(sys.argv) != 3:
        print(
            "usage: test_ical2html.py <ical2html> <sample.ics>",
            file=sys.stderr
        )
        return 2

    executable = sys.argv[1]
    sample = sys.argv[2]

    result = subprocess.run(
        [
            executable,
            "20260101",
            "P31D",
            sample,
        ],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, (
        f"ical2html exited with {result.returncode}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )

    assert "HarmonyOS Test Event" in result.stdout, (
        "expected event was not found in generated HTML"
    )

    assert "<table" in result.stdout.lower(), (
        "generated output does not contain an HTML table"
    )

    print("ical2html functional test passed")
    return 0
if __name__ == "__main__":
    sys.exit(main())
