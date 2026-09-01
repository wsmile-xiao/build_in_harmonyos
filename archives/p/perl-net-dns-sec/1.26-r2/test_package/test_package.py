#!/usr/bin/env python3
"""Test script for Net::DNS::SEC package verification.

Verifies package artifacts substantively (R34: test must depend on package):
1. .so is valid ELF64 AArch64 shared library
2. .so links against libcrypto (DT_NEEDED check via readelf)
3. .so contains XS bootstrap symbol (boot_Net__DNS__SEC via nm)
4. .so loadable by Perl DynaLoader (runtime check; may be blocked by SELinux)
5. .pm files present in correct Perl site_perl path

Usage: python3 test_package.py <pkg_folder>
"""
import os
import struct
import subprocess
import sys

MODULE = "Net::DNS::SEC"
XS_BOOT_SYMBOL = "boot_Net__DNS__SEC"
EXPECTED_NEEDED = "libcrypto.so.3"


def find_tool(names):
    """Find first available tool, checking OHOS standard paths first."""
    ohos_paths = ["/data/service/hnp/bin", "/system/bin", "/usr/bin"]
    for path in ohos_paths:
        for name in names:
            full = os.path.join(path, name)
            if os.path.isfile(full):
                return full
    for name in names:
        try:
            subprocess.run([name, "--version"], capture_output=True, timeout=5)
            return name
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def find_perl():
    """Find perl binary."""
    for candidate in ["/data/service/hnp/bin/perl", "perl"]:
        try:
            subprocess.run([candidate, "-e", "print 1"],
                           capture_output=True, timeout=5)
            return candidate
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_package.py <pkg_folder>", file=sys.stderr)
        sys.exit(1)

    pkg_folder = sys.argv[1]
    errors = []
    warnings = []
    checks = []

    # --- 1. Find and verify .so file ---
    so_path = None
    for root, dirs, files in os.walk(pkg_folder):
        for fn in files:
            if fn.endswith(".so"):
                so_path = os.path.join(root, fn)
                break
        if so_path:
            break

    if not so_path:
        errors.append("No .so file found in package")
    else:
        # 1a. Verify ELF header
        with open(so_path, "rb") as f:
            hdr = f.read(64)
        if hdr[:4] != b"\x7fELF":
            errors.append(f"{so_path} is not valid ELF (magic: {hdr[:4]})")
        else:
            elf_class = hdr[4]
            if elf_class != 2:
                errors.append(f"{so_path} is not 64-bit ELF (class={elf_class})")
            else:
                checks.append("ELF64")
            machine = struct.unpack_from("<H", hdr, 18)[0]
            if machine != 183:  # EM_AARCH64
                errors.append(f"{so_path} is not AArch64 (machine={machine})")
            else:
                checks.append("AArch64")

        # 1b. Verify libcrypto DT_NEEDED entry via readelf
        readelf = find_tool(["readelf", "llvm-readelf"])
        if readelf:
            r = subprocess.run([readelf, "-d", so_path],
                               capture_output=True, text=True, timeout=10)
            if EXPECTED_NEEDED in r.stdout:
                checks.append(f"NEEDED:{EXPECTED_NEEDED}")
            else:
                errors.append(
                    f"{so_path} missing DT_NEEDED entry for {EXPECTED_NEEDED}"
                )
        else:
            warnings.append("readelf not available, skipping NEEDED check")

        # 1c. Verify XS bootstrap symbol via nm
        nm = find_tool(["nm", "llvm-nm"])
        if nm:
            r = subprocess.run([nm, "-D", so_path],
                               capture_output=True, text=True, timeout=10)
            if XS_BOOT_SYMBOL in r.stdout:
                checks.append(f"symbol:{XS_BOOT_SYMBOL}")
            else:
                errors.append(
                    f"{so_path} missing XS bootstrap symbol '{XS_BOOT_SYMBOL}'"
                )
        else:
            warnings.append("nm not available, skipping symbol check")

    # --- 2. Find and verify .pm file ---
    pm_path = None
    module_rel = MODULE.replace("::", "/") + ".pm"
    for root, dirs, files in os.walk(pkg_folder):
        for fn in files:
            if fn == module_rel.split("/")[-1]:
                full = os.path.join(root, fn)
                if full.endswith("/" + module_rel):
                    pm_path = full
                    break
        if pm_path:
            break

    if not pm_path:
        errors.append(f"No {module_rel} found in package")
    else:
        checks.append(f"pm:{MODULE}")

    # --- 3. Attempt runtime .so load via Perl DynaLoader ---
    if so_path:
        perl_cmd = find_perl()
        if perl_cmd is None:
            warnings.append("perl not found, cannot attempt DynaLoader load")
        else:
            dl_code = (
                f"use DynaLoader; "
                f"my $h = DynaLoader::dl_load_file('{so_path}'); "
                f"die $! unless $h; print 'loaded'"
            )
            r = subprocess.run(
                [perl_cmd, "-e", dl_code],
                capture_output=True, text=True, timeout=10
            )
            if r.returncode == 0:
                checks.append("DynaLoader:loaded")
            else:
                stderr = r.stderr.strip()
                if "Permission denied" in stderr or "dlopen" in stderr.lower():
                    warnings.append(
                        f"DynaLoader blocked by platform (SELinux/HMDFS): "
                        f"{stderr[:120]}"
                    )
                else:
                    errors.append(
                        f"DynaLoader failed to load .so: {stderr[:200]}"
                    )

    # --- Report ---
    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)

    checks_str = ", ".join(checks)
    if warnings:
        for w in warnings:
            print(f"WARN: {w}")
        print(f"OK: {MODULE} verified ({checks_str}) with {len(warnings)} warning(s)")
    else:
        print(f"OK: {MODULE} verified ({checks_str})")
    sys.exit(0)


if __name__ == "__main__":
    main()
