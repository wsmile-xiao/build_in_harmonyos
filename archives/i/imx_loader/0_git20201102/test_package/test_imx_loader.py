#!/usr/bin/env python3
"""Consumer smoke tests for the packaged imx_usb and imx_uart commands."""

import os
import subprocess
import sys
from pathlib import Path


passed = 0
failed = 0


def check(condition, message):
    global passed, failed
    if condition:
        passed += 1
        print("PASS: " + message)
    else:
        failed += 1
        print("FAIL: " + message)


def run(binary, *args):
    result = subprocess.run(
        [str(binary), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        check=False,
    )
    return result.returncode, result.stdout


def main(package_folder):
    root = Path(package_folder)
    usb = root / "bin" / "imx_usb"
    uart = root / "bin" / "imx_uart"
    config_dir = root / "etc" / "imx-loader.d"
    config = config_dir / "imx_usb.conf"

    missing = [str(path) for path in (usb, uart, config) if not path.is_file()]
    if missing:
        for path in missing:
            check(False, "packaged file exists: " + path)
        print("RESULT: %d passed, %d failed" % (passed, failed))
        return 1

    check(os.access(usb, os.X_OK) and os.access(uart, os.X_OK),
          "both packaged commands are executable")

    code, output = run(usb, "--help")
    check(code == 0 and "Usage: imx_usb" in output,
          "imx_usb --help prints its usage and exits successfully")

    code, output = run(usb, "-V")
    check(code == 0 and output.startswith("imx_usb "),
          "imx_usb -V reports the executable version")

    code, output = run(uart, "--help")
    check(code == 0 and "Usage: imx_uart" in output,
          "imx_uart --help prints its usage and exits successfully")

    # -S selects the upstream software simulator, so this exercises the
    # installed configuration without requiring an i.MX board or USB access.
    code, output = run(
        usb, "-c", str(config_dir), "-v", "-S", "0x15a2:0x0061"
    )
    check(
        code == 0
        and "imx_usb.conf" in output
        and "Simulating with vid=0x15a2 pid=0x0061" in output,
        "imx_usb uses the packaged config in simulator mode",
    )

    print("RESULT: %d passed, %d failed" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: test_imx_loader.py <package-folder>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
