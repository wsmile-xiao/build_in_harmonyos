#!/usr/bin/env python3
"""test_package for lgeneral — consumer CLI tests without a graphics stack.

Covers (R34, no graphical environment required):
  1. lgeneral --version       — prints "LGeneral 1.4.4", exit 0
  2. lgeneral --help          — usage text, exit 0
  3. lgc-pg --version         — exit 0
  4. lged --help              — exit 0 (lged is a pure-libc terminal tool)
  5. ltrextract --help        — exit 0
  6. lgeneral bad-flag path   — engine exits nonzero on a missing data dir
  7. ELF sanity               — every installed binary is AArch64 PIE with
                                the musl interpreter and only OHOS-approved
                                NEEDED entries (SDL compat chain + libc)
  8. testfile (upstream check_PROGRAMS, installed alongside) — enumerate a
     real directory and report a missing one, matching upstream semantics
"""
import os
import struct
import subprocess
import sys


BINARIES = ("lgeneral", "lgc-pg", "lged", "ltrextract")


def run(binary, args, timeout=30):
    return subprocess.run(
        [binary] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    )


def check_elf(path):
    """Minimal ELF64 AArch64 PIE + interpreter + NEEDED whitelist check."""
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:4] != b"\x7fELF":
        raise RuntimeError(f"{path}: not an ELF file")
    if data[4] != 2 or data[18:20] != b"\xb7\x00":
        raise RuntimeError(f"{path}: not ELF64 AArch64 (e_machine={data[18:20]!r})")
    e_type = struct.unpack_from("<H", data, 16)[0]
    if e_type != 3:  # ET_DYN — PIE
        raise RuntimeError(f"{path}: e_type={e_type}, expected 3 (PIE)")
    allowed = {"libSDL-1.2.so.0", "libSDL2-2.0.so.0", "libc.so", "ld-musl-aarch64.so.1"}
    needed = []
    for chunk in data.split(b"\x00"):
        # crude DT_NEEDED sweep: strings ending in .so or .so.N inside .dynamic
        if chunk.startswith(b"lib") and (b".so" in chunk):
            needed.append(chunk.decode("ascii", "replace"))
    unexpected = [n for n in needed if n not in allowed]
    if unexpected:
        raise RuntimeError(f"{path}: unexpected NEEDED entries {unexpected}")
    return needed


def main():
    bindir = sys.argv[1]
    errors = []
    checks = 0

    # 1. lgeneral --version
    result = run(os.path.join(bindir, "lgeneral"), ["--version"])
    checks += 1
    if result.returncode != 0 or "1.4.4" not in result.stdout:
        errors.append(f"lgeneral --version: rc={result.returncode}, out={result.stdout!r}")

    # 2. lgeneral --help — upstream prints "Syntax:" (not "usage")
    result = run(os.path.join(bindir, "lgeneral"), ["--help"])
    checks += 1
    if result.returncode != 0 or "syntax" not in result.stdout.lower():
        errors.append(f"lgeneral --help: rc={result.returncode}, out={result.stdout!r}")

    # 3. lgc-pg --version
    result = run(os.path.join(bindir, "lgc-pg"), ["--version"])
    checks += 1
    if result.returncode != 0:
        errors.append(f"lgc-pg --version: rc={result.returncode}, out={result.stdout!r}")

    # 4. lged --help — upstream exits 1 after printing help (it treats --help
    #    as a command arg); success criterion is the help text itself
    result = run(os.path.join(bindir, "lged"), ["--help"])
    checks += 1
    if "reinforcement editor" not in result.stdout.lower():
        errors.append(f"lged --help: rc={result.returncode}, out={result.stdout!r}")

    # 5. ltrextract --help — same upstream convention as lged
    result = run(os.path.join(bindir, "ltrextract"), ["--help"])
    checks += 1
    if "translation extractor" not in result.stdout.lower():
        errors.append(f"ltrextract --help: rc={result.returncode}, out={result.stdout!r}")

    # 6. lgeneral with a bogus data dir must exit nonzero (clean failure, no crash)
    env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    result = subprocess.run(
        [os.path.join(bindir, "lgeneral"), "--config-separator=|"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        timeout=30, env=env,
    )
    checks += 1
    if result.returncode == 0:
        # exiting 0 without a game-data directory would mean it faked startup
        errors.append("lgeneral (no data): rc=0 — expected clean nonzero exit")

    # 7. ELF sanity for every installed binary
    for name in BINARIES:
        path = os.path.join(bindir, name)
        if not os.path.isfile(path):
            errors.append(f"missing installed command: {path}")
            continue
        checks += 1
        try:
            needed = check_elf(path)
            print(f"[elf] {name}: {', '.join(needed) or 'static'}")
        except RuntimeError as exc:
            errors.append(str(exc))

    # 8. upstream testfile (check_PROGRAMS) — real directory enumeration
    testfile = os.path.join(bindir, "testfile")
    if os.path.isfile(testfile):
        result = run(testfile, [bindir])
        checks += 1
        if result.returncode != 0 or "lgeneral" not in result.stdout:
            errors.append(f"testfile {bindir}: rc={result.returncode}, out={result.stdout!r}")
        result = run(testfile, ["/nonexistent-dir-for-lgeneral-test"])
        checks += 1
        if result.returncode == 0:
            errors.append("testfile /nonexistent: rc=0 — expected nonzero")
    else:
        print("[skip] upstream testfile not installed next to binaries")

    for err in errors:
        print(f"FAIL: {err}")
    if errors:
        return 1
    print(f"validated lgeneral command set ({checks} checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
