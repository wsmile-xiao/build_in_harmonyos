#!/usr/bin/env python3
"""HarmonyOS-only target and runtime checks for imx_loader."""

import os
import re
import shutil
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


def command(args):
    result = subprocess.run(
        args,
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
    config_dir = root / "etc" / "imx-loader.d"

    # Query the kernel through Python's uname syscall binding. The CI profile's
    # PATH omits /system/bin, so spawning the uname executable is not reliable.
    kernel = os.uname()
    check(kernel.sysname == "HarmonyOS",
          "test is running on the HarmonyOS kernel")

    check(kernel.machine == "aarch64",
          "device is the expected AArch64 target")

    readelf = shutil.which("readelf") or "/data/service/hnp/bin/readelf"
    code, elf_header = command([readelf, "-h", str(usb)])
    check(code == 0 and re.search(r"Machine:\s+AArch64", elf_header) is not None,
          "imx_usb is an AArch64 ELF executable")

    code, program_headers = command([readelf, "-l", str(usb)])
    check(
        code == 0
        and "/lib/ld-musl-aarch64.so.1" in program_headers,
        "imx_usb uses the HarmonyOS musl dynamic loader",
    )

    # Running -V exercises the OHOS loader and resolves the libusb dependency.
    code, version = command([str(usb), "-V"])
    check(code == 0 and version.startswith("imx_usb "),
          "imx_usb starts on HarmonyOS and resolves its runtime dependencies")

    # Exercise the packaged config through the upstream simulator, never a
    # physical USB device or firmware-transfer operation.
    code, output = command(
        [str(usb), "-c", str(config_dir), "-v", "-S", "0x15a2:0x0061"]
    )
    check(
        code == 0
        and "imx_usb.conf" in output
        and "Simulating with vid=0x15a2 pid=0x0061" in output,
        "packaged configuration runs through the simulator on HarmonyOS",
    )

    print("RESULT: %d passed, %d failed" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: test_ohos_imx_loader.py <package-folder>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
