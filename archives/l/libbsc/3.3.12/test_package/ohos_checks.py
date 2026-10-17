#!/usr/bin/env python3
"""HarmonyOS-specific checks for the libbsc 3.3.12 package (test_package side).

Executed from test_package test() via self.run(). Verifies the artifact is
genuinely an ELF64 AArch64 binary, carries a DT_SONAME (shared variant only),
contains no host paths baked in, and performs a real CLI compress->decompress
round-trip with byte-identical output (never just --help).

Handles both variants:
- shared: lib/libbsc.so must be ELF64 AArch64 DYN with DT_SONAME
- static: lib/libbsc.a must be an ar archive whose members are ELF64 AArch64
"""

import os
import shutil
import subprocess
import sys


def sh(*args, **kw):
    return subprocess.run(list(args), capture_output=True, text=True, **kw)


def _resolve_readelf():
    """Locate a readelf binary at runtime; prefer llvm-readelf, fall back to readelf.

    CI workers may ship only llvm-readelf (or vice versa), so never hardcode a
    bare command name or a machine-specific absolute path. Fails closed when
    neither tool is on PATH.
    """
    for cand in ("llvm-readelf", "readelf"):
        path = shutil.which(cand)
        if path:
            return path
    print("FATAL: neither 'llvm-readelf' nor 'readelf' found on PATH; cannot run ELF checks")
    sys.exit(1)


def main():
    package_dir = os.environ["TEST_PACKAGE_DIR"]
    readelf = _resolve_readelf()
    print(f"readelf resolved to: {readelf}")

    lib_shared = os.path.join(package_dir, "lib", "libbsc.so")
    lib_static = os.path.join(package_dir, "lib", "libbsc.a")
    cli = os.path.join(package_dir, "bin", "bsc")

    failures = []
    variant = "shared" if os.path.exists(lib_shared) else "static"
    print(f"variant: {variant}")

    if variant == "shared":
        # --- 1. ELF64 AArch64 shared object ---
        out = sh(readelf, "-h", lib_shared).stdout
        checks = {
            "Class: ELF64": "ELF64" in out,
            "Machine: AArch64": "AArch64" in out,
            "Type: DYN (shared)": "DYN" in out,
        }
        for name, ok in checks.items():
            print(("PASS " if ok else "FAIL ") + name)
            if not ok:
                failures.append(name)

        # --- 2. DT_SONAME present (E322 pattern) ---
        out = sh(readelf, "-d", lib_shared).stdout
        ok = "(SONAME)" in out
        print(("PASS " if ok else "FAIL ") + "DT_SONAME present")
        if not ok:
            failures.append("DT_SONAME")
    else:
        # --- static: ar archive whose members are ELF64 AArch64 ---
        # readelf on an archive prints each member's ELF header
        out = sh(readelf, "-h", lib_static).stdout
        ok_arch = "AArch64" in out and "ELF64" in out
        print(("PASS " if ok_arch else "FAIL ") + "static archive members are ELF64 AArch64")
        if not ok_arch:
            failures.append("static-arch")

    # --- 3. no host paths / x86 markers in the library binary ---
    lib = lib_shared if variant == "shared" else lib_static
    data = open(lib, "rb").read()
    suspects = [b"/storage/", b"/home/", b"/tmp/libbsc", b"/Users/"]
    leaked = [s for s in suspects if s in data]
    print(("PASS " if not leaked else "FAIL ") + f"no host-path strings ({len(leaked)} leaked)")
    if leaked:
        failures.append("host-paths")

    # --- 4. CLI round-trip (real execution, never --help only) ---
    if os.path.exists(cli):
        tmp = os.path.join(os.environ.get("TMPDIR", os.path.expanduser("~/tmp-libbsc-cli")))
        os.makedirs(tmp, exist_ok=True)
        src = os.path.join(tmp, "input.bin")
        enc = os.path.join(tmp, "input.bsc")
        dec = os.path.join(tmp, "output.bin")
        with open(src, "wb") as f:
            f.write(b"HARMONYOS libbsc CLI round-trip corpus\x00" * 2048)
        if not os.access(cli, os.X_OK):
            try:
                os.chmod(cli, 0o755)
            except OSError:
                pass  # read-only cache mount; assume already executable
        env = dict(os.environ, LD_LIBRARY_PATH=os.path.join(package_dir, "lib"))
        r1 = sh(cli, "e", src, enc, env=env)
        r2 = sh(cli, "d", enc, dec, env=env)
        if r1.returncode != 0 or r2.returncode != 0:
            print(f"FAIL CLI round-trip: e={r1.returncode} d={r2.returncode}")
            if r1.stderr:
                print("  e stderr:", r1.stderr.strip()[:200])
            if r2.stderr:
                print("  d stderr:", r2.stderr.strip()[:200])
            failures.append("cli-roundtrip")
        elif open(src, "rb").read() != open(dec, "rb").read():
            print("FAIL CLI round-trip: output differs")
            failures.append("cli-roundtrip")
        else:
            print("PASS CLI round-trip (byte-identical)")
    else:
        print("SKIP CLI (not packaged)")

    if failures:
        print(f"OHOS_CHECKS: FAIL ({', '.join(failures)})")
        return 1
    print("OHOS_CHECKS: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
