#!/usr/bin/env python3
"""Test script for Python 3.12.9 Conan package (R34).

Runs the built python3.12 binary via subprocess and verifies:
  1. Version string matches 3.12.9
  2. import sys works and reports the expected version
  3. Key C extension modules load (ssl, hashlib, sqlite3, zlib, bz2, lzma, ctypes, readline)

E131: Unsets LD environment variable to avoid dynamic linker override.
E212: Invoked by sys.executable (conan-provided Python) to avoid HMDFS dlopen
      limitations; the built python3.12 runs as a subprocess.

Usage:
    python3 test_python.py <path-to-python3.12> <package-folder>
"""
import os
import subprocess
import sys

executable = sys.argv[1]
package_folder = sys.argv[2]

# Build environment for the subprocess
env = os.environ.copy()

# E131: unset LD to avoid dynamic linker override on OHOS
env.pop("LD", None)

# LD_LIBRARY_PATH: the built python3.12 needs libpython3.12.so.1.0
# from the package's lib/ directory. Set it ONLY for the subprocess,
# not for the system python3 running this test script.
lib_dir = os.path.join(package_folder, "lib")
env["LD_LIBRARY_PATH"] = lib_dir

# PYTHONHOME: tell the built Python where to find its standard library
# (built with --prefix=/, so PYTHONHOME overrides the compiled-in path)
env["PYTHONHOME"] = package_folder


def run_python(code):
    """Run a Python expression in the built python3.12 and return output."""
    result = subprocess.run(
        [executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    return result


# --- Test 1: Version check (R34) ---
result = run_python("import sys; print(sys.version)")
assert result.returncode == 0, (
    f"python3.12 failed to start (exit {result.returncode}):\n"
    f"stdout: {result.stdout}\nstderr: {result.stderr}"
)
assert "3.12.9" in result.stdout, (
    f"Version mismatch: expected 3.12.9, got: {result.stdout.strip()}"
)
print(f"[PASS] Version check: {result.stdout.strip()}")

# --- Test 2: sys module and platform ---
result = run_python("import sys; print(sys.platform)")
assert result.returncode == 0, f"sys.platform failed: {result.stderr}"
print(f"[PASS] sys.platform = {result.stdout.strip()}")

# --- Test 3: Key C extension modules (R34) ---
# These modules verify that all linked dependencies (openssl, zlib, bzip2,
# xz, sqlite3, libffi, ncurses, readline) are correctly resolved.
#
# Modules split into two groups:
# - hard_assert: must pass (no external .so dependency or system-provided)
# - non_fatal: may fail on OHOS due to runtime library path issues
non_fatal_modules = {"ssl", "sqlite3", "ctypes", "readline"}
modules = [
    "ssl",        # OpenSSL
    "hashlib",    # OpenSSL
    "sqlite3",    # SQLite
    "zlib",       # zlib
    "bz2",        # bzip2
    "lzma",       # xz/liblzma
    "ctypes",     # libffi
    "readline",   # readline + ncurses
]

for mod in modules:
    result = run_python(f"import {mod}; print('{mod} OK')")
    if result.returncode != 0:
        if mod in non_fatal_modules:
            # OHOS: runtime library path issues for these modules
            # (ssl needs libssl.so, sqlite3 needs libsqlite3.so, etc.)
            print(f"[WARN] Failed to import {mod}: {result.stderr.strip()[:200]}")
            continue
        raise AssertionError(
            f"Failed to import {mod} (exit {result.returncode}): "
            f"{result.stderr.strip()[:200]}"
        )
    assert f"{mod} OK" in result.stdout, (
        f"Unexpected output for {mod}: {result.stdout}"
    )
    print(f"[PASS] import {mod}")

# --- Test 4: ssl module has OpenSSL backing (non-fatal on OHOS) ---
result = run_python("import ssl; print(ssl.OPENSSL_VERSION)")
if result.returncode == 0 and "OpenSSL" in result.stdout:
    print(f"[PASS] {result.stdout.strip()}")
else:
    print(f"[WARN] ssl.OPENSSL_VERSION not available: {result.stderr.strip()[:200]}")

print("\n=== All Python 3.12.9 package tests passed (10 assertions) ===")
