#!/usr/bin/env python3
"""OHOS-specific consumer test for mpssh (test_package).

Validates the installed package against HarmonyOS PC adaptation requirements
with NO external network:
  1. ELF64 AArch64 + musl libc verification (readelf on the installed binary)
  2. .codesign section present (E082/R38: required to execute on OHOS)
  3. No RPATH/RUNPATH pointing to build-host paths
  4. No hardcoded host paths in the binary (except the by-design baked
     /usr/bin/ssh and /usr/bin/scp tool paths)

The binary path is resolved through the tested package's package_folder
(no PATH reliance), mirroring the cloud-utils-ec2metadata precedent.
"""
import os
import re
import shutil
import struct
import subprocess
import sys

MPSSH = os.environ.get("MPSSH_BIN", "mpssh")
READELF = (
    os.environ.get("READELF")
    or shutil.which("llvm-readelf")
    or shutil.which("readelf")
)

failures = []

if not READELF:
    failures.append("tool: neither llvm-readelf nor readelf is available")


def run(cmd, label, timeout=45):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, env=dict(os.environ))
        return p
    except subprocess.TimeoutExpired:
        failures.append(f"{label}: TIMEOUT ({timeout}s)")
        return None
    except Exception as ex:
        failures.append(f"{label}: {ex}")
        return None


def parse_dt_needed(readelf_stdout):
    """Parse every DT_NEEDED shared library name from `readelf -d` output.

    readelf prints each dynamic dependency as:
        0x0000000000000001 (NEEDED)  Shared library: [libc.so]
    The library name is the exact string inside the brackets. Returns a
    set of exact names.

    Callers must test membership ("libc.so" in needed), never substring
    match against the raw line: "libc.so" is a substring of "libc.so.6",
    so a line-level `in` check silently accepts glibc linkage.
    """
    names = set()
    for line in readelf_stdout.splitlines():
        if "NEEDED" not in line:
            continue
        m = re.search(r"\[([^\]]+)\]", line)
        if m:
            names.add(m.group(1))
    return names


def glibc_violations(needed):
    """Exact-match checks for glibc leakage in a DT_NEEDED name set.

    musl libc links against "libc.so"; glibc links against "libc.so.6".
    Returns a list of human-readable violations (empty = clean).
    """
    violations = []
    if "libc.so.6" in needed:
        violations.append('glibc dependency "libc.so.6" in DT_NEEDED '
                          "(musl libc links as \"libc.so\")")
    for name in sorted(needed):
        if name.startswith("ld-linux"):
            violations.append(f'glibc loader "{name}" in DT_NEEDED '
                              "(musl uses /lib/ld-musl-*.so.1)")
        if "GLIBC" in name:
            violations.append(f'glibc version marker "{name}" in DT_NEEDED')
    return violations


def parser_selftest():
    """Deterministic self-test of the DT_NEEDED parser and glibc checks:
      {"libc.so"}            must pass  (pure musl)
      {"libc.so.6"}          must fail  (pure glibc)
      {"libc.so","libc.so.6"} must fail (glibc leaked alongside musl)
    """
    errors = []
    if glibc_violations({"libc.so"}):
        errors.append('selftest: {"libc.so"} must pass (musl)')
    if not glibc_violations({"libc.so.6"}):
        errors.append('selftest: {"libc.so.6"} must fail (glibc)')
    if not glibc_violations({"libc.so", "libc.so.6"}):
        errors.append('selftest: {"libc.so", "libc.so.6"} must fail (glibc leak)')
    sample = ("  0x0000000000000001 (NEEDED)  Shared library: [libc.so]\n"
              "  0x0000000000000001 (NEEDED)  Shared library: [libc.so.6]\n")
    parsed = parse_dt_needed(sample)
    if parsed != {"libc.so", "libc.so.6"}:
        errors.append(f"selftest: parser returned {sorted(parsed)}, "
                      'expected ["libc.so", "libc.so.6"]')
    return errors


def main():
    # ── 0. parser self-test (deterministic, no binary needed) ──
    selftest_errors = parser_selftest()
    if selftest_errors:
        failures.extend(selftest_errors)
    else:
        print("[ok] selftest: DT_NEEDED parser exact-match checks pass")

    # ── 1. ELF header: ELF64 + AArch64 ──
    with open(MPSSH, "rb") as f:
        eh = f.read(64)
    if eh[:4] != b"\x7fELF":
        failures.append("elf: not an ELF file")
    else:
        ei_class, ei_data = eh[4], eh[5]
        if ei_class != 2:
            failures.append(f"elf: expected ELF64 (class=2), got class={ei_class}")
        if ei_data != 1:
            failures.append(f"elf: expected little-endian (data=1), got data={ei_data}")
        # e_machine at offset 18 (LE uint16): EM_AARCH64 = 183
        e_machine = struct.unpack_from("<H", eh, 18)[0]
        if e_machine != 183:
            failures.append(f"elf: expected EM_AARCH64 (183), got e_machine={e_machine}")
        if eh[4:5] == b"\x02" and e_machine == 183:
            print("[ok] elf: ELF64 AArch64 little-endian")

    # ── 2. musl libc linkage ──
    p = run([READELF, "-d", MPSSH], "readelf-dynamic")
    if p is not None:
        needed = parse_dt_needed(p.stdout)
        print("[info] dynamic deps:", " ".join(f"[{n}]" for n in sorted(needed))
              or "(none)")
        if needed:
            if "libc.so" in needed:
                print("[ok] musl: libc.so (musl libc) in DT_NEEDED")
            # fully static is also acceptable; only fail on glibc leakage
            for v in glibc_violations(needed):
                failures.append(f"musl: {v}")
        else:
            print("[info] musl: no DT_NEEDED entries (static)")
    # musl proof: the program interpreter must be the musl loader
    # (OHOS has no glibc; glibc binaries use /lib/ld-linux-aarch64.so.1)
    p = run([READELF, "-l", MPSSH], "readelf-interp")
    if p is not None:
        interp = [l for l in p.stdout.splitlines() if "interpreter" in l]
        if interp:
            if any("ld-musl" in l for l in interp):
                print("[ok] musl: musl program interpreter:", interp[0].split("interpreter:")[-1].strip())
            elif any("ld-linux" in l for l in interp):
                failures.append(f"musl: glibc interpreter found: {interp[0].strip()}")
            else:
                failures.append(f"musl: unknown interpreter: {interp[0].strip()}")
        else:
            # static binaries have no PT_INTERP — check for glibc banner instead
            print("[info] musl: no PT_INTERP (static) — OK if no glibc marker")
            with open(MPSSH, "rb") as f:
                blob_interp = f.read()
            if b"GNU C Library" in blob_interp or b"glibc" in blob_interp:
                failures.append("musl: glibc marker found in static binary")

    # ── 3. .codesign section present (OHOS execution requirement) ──
    p = run([READELF, "-S", "-W", MPSSH], "readelf-sections")
    if p is not None:
        if ".codesign" in p.stdout:
            print("[ok] codesign: .codesign section present")
        else:
            failures.append("codesign: .codesign section MISSING (binary won't execute on OHOS)")

    # ── 4. No RPATH/RUNPATH with host paths ──
    p = run([READELF, "-d", MPSSH], "readelf-rpath")
    if p is not None:
        rp = [l for l in p.stdout.splitlines() if "RPATH" in l or "RUNPATH" in l]
        if rp:
            # mpssh links only libc; any RPATH at all is suspicious
            bad = [l for l in rp if "build_in" in l or "/home/" in l
                   or "/storage/" in l or "conan" in l.lower()]
            if bad:
                failures.append(f"rpath: host-path RPATH found: {bad}")
            else:
                print("[warn] rpath: RPATH present (no host path):", rp)
        else:
            print("[ok] rpath: no RPATH/RUNPATH")

    # ── 5. No host build paths embedded in the binary ──
    # Read as bytes to be robust: search for the CI workspace marker string.
    with open(MPSSH, "rb") as f:
        blob = f.read()
    host_markers = [b"/storage/Users/", b"/home/", b"build_in_harmonyos",
                    b"build_in_hardriveos", b"conan/cache"]
    found = [m.decode() for m in host_markers if m in blob]
    if found:
        failures.append(f"hostpath: build-host paths embedded: {found}")
    else:
        print("[ok] hostpath: no build-host paths embedded")

    # by-design baked tool paths must still be there (functional contract)
    for tool, marker in (("ssh", b"/usr/bin/ssh"), ("scp", b"/usr/bin/scp")):
        if marker in blob:
            print(f"[ok] baked {tool} path present ({marker.decode()})")
        else:
            failures.append(f"baked {tool} path missing ({marker.decode()})")

    if failures:
        print("OHOS TEST FAILED:")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("OHOS TEST PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
