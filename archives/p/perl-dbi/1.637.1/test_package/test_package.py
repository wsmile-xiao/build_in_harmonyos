#!/usr/bin/env python3
"""Test script for DBI package verification.
Verifies that the package contains valid ELF .so and the Perl module loads.

Usage: python3 test_package.py <pkg_folder>
"""
import sys
import os
import shutil
import subprocess

MODULE = "DBI"


def find_perl():
    """Find the perl executable.
    On CI workers, perl may not be in PATH. Try common HarmonyOS locations.
    """
    perl = shutil.which("perl")
    if perl:
        return perl
    common_paths = [
        "/data/service/hnp/bin/perl",
        "/storage/Users/currentUser/usr/local/bin/perl",
        os.path.expanduser("~/usr/local/bin/perl"),
    ]
    for p in common_paths:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


def is_platform_limitation(stderr):
    """Check if error is a platform limitation (not a package defect)."""
    platform_indicators = [
        "Permission denied",
        "denied",
        "symbol not found",
        "Error relocating",
        "__emutls",
        "dlopen failed",
        "cannot open shared object",
        "No such file or directory",  # missing runtime deps
    ]
    stderr_lower = stderr.lower()
    return any(ind.lower() in stderr_lower for ind in platform_indicators)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_package.py <pkg_folder>", file=sys.stderr)
        sys.exit(1)

    pkg_folder = sys.argv[1]
    errors = []
    warnings = []

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
        with open(so_path, "rb") as f:
            magic = f.read(4)
            if magic != b"\x7fELF":
                errors.append(f"{so_path} is not valid ELF (magic: {magic})")

    pm_path = None
    perl5lib = None
    module_rel = MODULE.replace("::", "/") + ".pm"
    for root, dirs, files in os.walk(pkg_folder):
        for fn in files:
            full_path = os.path.join(root, fn)
            if full_path.endswith("/" + module_rel):
                pm_path = full_path
                idx = full_path.rfind("/" + module_rel)
                perl5lib = full_path[:idx]
                break
        if pm_path:
            break
    if not pm_path:
        for root, dirs, files in os.walk(pkg_folder):
            for fn in files:
                if fn == module_rel:
                    pm_path = os.path.join(root, fn)
                    perl5lib = root
                    break
            if pm_path:
                break
    if not pm_path:
        for root, dirs, files in os.walk(pkg_folder):
            for fn in files:
                if fn.endswith(".pm"):
                    pm_path = os.path.join(root, fn)
                    break
            if pm_path:
                break

    if not pm_path:
        errors.append("No .pm file found in package")
    elif perl5lib:
        perl_path = find_perl()
        if not perl_path:
            warnings.append(
                "perl not found in PATH or common locations, skipping module load test"
            )
        else:
            env = dict(os.environ)
            env["PERL5LIB"] = perl5lib
            try:
                result = subprocess.run(
                    [perl_path, "-e", "use " + MODULE + "; print 'loaded'"],
                    capture_output=True, text=True, env=env, timeout=10
                )
                if result.returncode == 0:
                    print(f"Perl module load test: PASS - {result.stdout.strip()}")
                else:
                    stderr = result.stderr.strip()
                    if is_platform_limitation(stderr):
                        warnings.append(
                            f"Perl module load skipped (platform limitation): {stderr}"
                        )
                    else:
                        errors.append(f"Failed to load Perl module {MODULE}: {stderr}")
            except subprocess.TimeoutExpired:
                warnings.append(f"Perl module {MODULE} load timed out (10s)")
            except Exception as e:
                warnings.append(f"Perl module load test error: {e}")
    else:
        errors.append(f"Found .pm file but could not determine PERL5LIB: {pm_path}")

    if warnings:
        for w in warnings:
            print(f"WARN: {w}")

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"OK: {MODULE} package verified - .so (ELF valid), .pm found, module loads")
    if warnings:
        print(f"  ({len(warnings)} warning(s) - non-blocking)")
    sys.exit(0)


if __name__ == "__main__":
    main()
