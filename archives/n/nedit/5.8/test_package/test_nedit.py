#!/usr/bin/env python3
"""Consumer checks for the installed nedit 5.8 command set.

Every process is started by absolute path from the Conan package cache.  The
``DISPLAY`` variable is removed for each run, because NEdit answers ``-V`` /
``-version`` before it opens a display: that makes the whole test runnable on a
worker with no X server, while still proving that the packaged binaries are
executable, correctly linked against the Conan ``libXm.so.4``, and really are X
clients.

usage: test_nedit.py <package-bin-dir> <app-defaults-file>
"""

import os
import struct
import subprocess
import sys

EM_AARCH64 = 183
ET_DYN = 3

checks = 0


def check(condition, message):
    global checks
    if not condition:
        raise AssertionError(message)
    checks += 1


def run(command, *args):
    """Run a packaged binary with DISPLAY removed; return the completed process."""
    env = dict(os.environ)
    env.pop("DISPLAY", None)
    return subprocess.run(
        [command, *args],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=120,
        env=env,
    )


def output_of(result):
    return (result.stdout or "") + (result.stderr or "")


def check_ohos_elf(path, label):
    with open(path, "rb") as handle:
        header = handle.read(64)
    check(header[:4] == b"\x7fELF", f"{label} is not an ELF file")
    check(header[4] == 2, f"{label} is not a 64-bit ELF")
    check(header[5] == 1, f"{label} is not little-endian")
    machine = struct.unpack_from("<H", header, 18)[0]
    e_type = struct.unpack_from("<H", header, 16)[0]
    check(machine == EM_AARCH64, f"{label} is not an AArch64 ELF (e_machine={machine})")
    check(e_type == ET_DYN, f"{label} is not a PIE executable (e_type={e_type})")


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: test_nedit.py <package-bin-dir> <app-defaults-file>")

    bin_dir = os.path.abspath(sys.argv[1])
    app_defaults = os.path.abspath(sys.argv[2])

    nedit = os.path.join(bin_dir, "nedit")
    nedit_nc = os.path.join(bin_dir, "nedit-nc")

    # --- installed layout -------------------------------------------------
    check(os.path.isfile(nedit), "nedit is missing from the package")
    check(os.access(nedit, os.X_OK), "nedit is not executable")
    check(os.path.isfile(nedit_nc), "nedit-nc is missing from the package")
    check(os.access(nedit_nc, os.X_OK), "nedit-nc is not executable")

    # --- the binaries are real OHOS AArch64 PIE executables ---------------
    check_ohos_elf(nedit, "nedit")
    check_ohos_elf(nedit_nc, "nedit-nc")

    # --- X resource defaults ---------------------------------------------
    check(os.path.isfile(app_defaults), "the NEdit app-defaults file is missing")
    check(os.path.getsize(app_defaults) > 0, "the NEdit app-defaults file is empty")

    # --- nedit -V / -version, headless ------------------------------------
    for option in ("-V", "-version"):
        result = run(nedit, option)
        text = output_of(result)
        check(result.returncode == 0, f"nedit {option} exited {result.returncode}: {text}")
        check("NEdit 5.8" in text, f"nedit {option} did not report version 5.8: {text}")

    version_text = output_of(run(nedit, "-V"))
    check(
        "With Motif:" in version_text,
        f"nedit -V did not report the Motif headers it was built against: {version_text}",
    )
    # "Running Motif:" prints xmUseVersion, a variable the Motif library itself
    # provides: seeing the line means the packaged libXm.so.4 was really loaded.
    check(
        "Running Motif:" in version_text,
        f"nedit -V did not report the loaded Motif library: {version_text}",
    )

    # --- nedit really is an X client --------------------------------------
    result = run(nedit)
    check(result.returncode != 0, "nedit started without a display")
    check(
        "Can't open display" in output_of(result),
        f"nedit without DISPLAY did not report the missing display: {output_of(result)}",
    )

    # --- nedit-nc -V / -version, headless ---------------------------------
    for option in ("-V", "-version"):
        result = run(nedit_nc, option)
        text = output_of(result)
        check(result.returncode == 0, f"nedit-nc {option} exited {result.returncode}: {text}")
        check("Version 5.8" in text, f"nedit-nc {option} did not report version 5.8: {text}")

    nc_text = output_of(run(nedit_nc, "-V"))
    check(
        "Built on:" in nc_text,
        f"nedit-nc -V is missing its build line: {nc_text}",
    )

    # --- nedit-nc really is an X client -----------------------------------
    result = run(nedit_nc)
    check(result.returncode != 0, "nedit-nc started without a display")
    check(
        "Can't open display" in output_of(result),
        f"nedit-nc without DISPLAY did not report the missing display: {output_of(result)}",
    )

    print(f"nedit 5.8 consumer checks passed: {checks}/{checks}")


if __name__ == "__main__":
    main()
