#!/usr/bin/env python3
"""Deterministic consumer smoke checks for the packaged xsane binary.

xsane 0.999 is a GUI application with no upstream test suite.  Its argument
handling runs *after* GTK initialisation, so on a headless target
`xsane --version` fails with "cannot open display" — reaching that point
already proves the dynamic-linking chain (libc++/gtk-x11/gdk/sane ...) loads
and xsane enters GTK display init.  Full GUI verification needs an X server
(R40 human-confirmation boundary).
"""

import re
import subprocess
import sys

checks = 0


def check(condition, message):
    global checks
    if not condition:
        raise AssertionError(message)
    checks += 1


def main():
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <path-to-xsane>", file=sys.stderr)
        return 2

    xsane_bin = sys.argv[1]
    check(len(xsane_bin) > 0, "xsane binary path argument is empty")

    completed = subprocess.run(
        [xsane_bin, "--version"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    output = (completed.stdout or "") + (completed.stderr or "")
    with_display = "cannot open display" in output or "cannot open display" in output.lower()
    if completed.returncode == 0:
        check("xsane" in output.lower(), f"version output does not mention xsane: {output!r}")
        check(
            re.search(r"\d+\.\d+", output) is not None,
            f"version output has no numeric version: {output!r}",
        )
    else:
        # Headless target: the binary loaded every shared library and reached
        # GTK display initialisation before failing on the missing X server.
        check(with_display, f"xsane --version failed without reaching display init: {output!r}")
        check(
            "xsane" in output.lower(),
            f"headless run output does not identify the binary: {output!r}",
        )

    print(f"xsane consumer smoke: {checks}/{checks} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
