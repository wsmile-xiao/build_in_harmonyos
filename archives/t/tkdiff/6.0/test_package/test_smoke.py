#!/usr/bin/env python3
"""Consumer smoke test for the packaged tkdiff script."""
import os
import shutil
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: test_smoke.py <package_folder>", file=sys.stderr)
        return 2

    package_folder = sys.argv[1]
    script = os.path.join(package_folder, "bin", "tkdiff")
    assert os.path.isfile(script), f"missing tkdiff script: {script}"

    with open(script, "r", encoding="utf-8", errors="replace") as handle:
        content = handle.read()
    assert content.startswith("#!/usr/bin/env sh"), "tkdiff shebang was not adapted for HarmonyOS"
    assert "package require Tk" in content, "tkdiff Tcl/Tk entry point missing"
    assert "^--help" in content and "^-h" in content, "tkdiff help switch handling missing"

    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        wish = shutil.which("wish")
        if wish:
            subprocess.run([wish, script, "--help"], check=True)
    else:
        print("No display server detected; static package validation completed")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
