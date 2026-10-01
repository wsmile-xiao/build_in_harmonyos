#!/usr/bin/env python3
"""Conan consumer test for rudof 0.3.6.

Layers of assertions:

  A. Generic consumer smoke/functional test — runs the packaged `rudof`
     binary:
       A1 `rudof --help` exits 0
       A2 `--help` output lists the sub-commands (mentions "validate")
       A3 `rudof --version` exits 0 and reports 0.3.6
       A4 `rudof data <file.ttl>` actually loads an RDF graph and
          re-serialises it (the triple object "Alice" appears on stdout)

  B. HarmonyOS-specific (鸿蒙特有) assertions — verify the platform traits
     that make the artifact usable on OHOS at all:
       B1. ELF machine is AArch64 (the OHOS PC target)
       B2. PT_INTERP is the OHOS musl loader (ld-musl-aarch64.so.1) — proves
           this is a bionic/musl-flavoured OHOS binary, not a glibc Linux one
       B3. the binary carries an OHOS code signature — HarmonyOS refuses to
           execve unsigned ELF (EACCES errno 13), so this is mandatory and
           is the exact failure the recipe's _sign_binaries() fixes
       B4. the binary is a non-empty regular executable file

Every assertion is reported on its own line so the counts quoted in the PR
description stay auditable.
"""

import os
import struct
import subprocess
import sys
import tempfile

PASSED = 0
FAILED = 0

OHOS_MUSL_LOADER = "ld-musl-aarch64.so.1"
EM_AARCH64 = 183

TURTLE_SAMPLE = (
    "PREFIX ex: <http://example.org/>\n"
    "ex:alice ex:name \"Alice\" ;\n"
    "         ex:knows ex:bob .\n"
    "ex:bob ex:name \"Bob\" .\n"
)


def check(name, ok, detail=""):
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"[ok] {name}{(': ' + detail) if detail else ''}")
    else:
        FAILED += 1
        print(f"[fail] {name}{(': ' + detail) if detail else ''}", file=sys.stderr)
    return ok


def elfinfo(path):
    """Return (e_machine, interp) or (None, None) when unreadable."""
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return None, None
    if data[:4] != b"\x7fELF":
        return None, None
    e_machine = struct.unpack_from("<H", data, 18)[0]
    phoff = struct.unpack_from("<Q", data, 0x20)[0]
    phentsize = struct.unpack_from("<H", data, 0x36)[0]
    phnum = struct.unpack_from("<H", data, 0x38)[0]
    interp = None
    for i in range(phnum):
        off = phoff + i * phentsize
        if struct.unpack_from("<I", data, off)[0] == 3:  # PT_INTERP
            p_offset = struct.unpack_from("<Q", data, off + 8)[0]
            p_filesz = struct.unpack_from("<Q", data, off + 32)[0]
            interp = (data[p_offset:p_offset + p_filesz]
                      .rstrip(b"\x00").decode("utf-8", "replace"))
            break
    return e_machine, interp


def main():
    package_folder = os.environ.get("PACKAGE_FOLDER", "")
    exe = os.path.join(package_folder, "bin", "rudof")

    # ── B. 鸿蒙特有测试 (HarmonyOS-specific) ──
    print("== 鸿蒙特有测试 / HarmonyOS-specific assertions ==")
    if not check("B4: rudof is a non-empty regular executable file",
                 os.path.isfile(exe) and os.path.getsize(exe) > 0,
                 f"{exe} ({os.path.getsize(exe) if os.path.isfile(exe) else 0} bytes)"):
        raise AssertionError(f"Missing rudof executable: {exe}")

    e_machine, interp = elfinfo(exe)
    check("B1: ELF machine is AArch64 (EM_AARCH64=183)",
          e_machine == EM_AARCH64, f"e_machine={e_machine}")

    check(f"B2: PT_INTERP is the OHOS musl loader ({OHOS_MUSL_LOADER})",
          interp is not None and OHOS_MUSL_LOADER in interp, f"interp={interp}")

    with open(exe, "rb") as fh:
        payload = fh.read()
    check("B3: OHOS code signature present (unsigned ELF cannot execve)",
          b"codesign" in payload)

    # ── A. 通用消费者冒烟/功能测试 ──
    print("== 消费者冒烟测试 / consumer smoke test ==")
    help_run = subprocess.run(
        [exe, "--help"], capture_output=True, text=True, timeout=30
    )
    if not check("A1: `rudof --help` exits 0", help_run.returncode == 0,
                 f"rc={help_run.returncode} err={help_run.stderr.strip()[:160]}"):
        raise AssertionError(f"`rudof --help` failed: {help_run.stderr}")
    check("A2: `--help` output lists sub-commands (mentions validate)",
          "validate" in help_run.stdout.lower())

    version_run = subprocess.run(
        [exe, "--version"], capture_output=True, text=True, timeout=30
    )
    check("A3: `rudof --version` exits 0 and reports 0.3.6",
          version_run.returncode == 0 and "0.3.6" in version_run.stdout,
          f"rc={version_run.returncode} out={version_run.stdout.strip()[:80]}")

    # A4: real RDF load + re-serialise round-trip via the `data` sub-command.
    with tempfile.TemporaryDirectory(prefix="rudof-tp-") as work:
        ttl = os.path.join(work, "sample.ttl")
        with open(ttl, "w", encoding="utf-8") as fh:
            fh.write(TURTLE_SAMPLE)
        data_run = subprocess.run(
            [exe, "data", ttl], capture_output=True, text=True, timeout=60
        )
        check("A4: `rudof data sample.ttl` loads and re-serialises the graph",
              data_run.returncode == 0 and "Alice" in data_run.stdout,
              f"rc={data_run.returncode} "
              f"out={data_run.stdout.strip().splitlines()[:1]} "
              f"err={data_run.stderr.strip()[:120]}")

    print(f"SUMMARY: executed={PASSED + FAILED} passed={PASSED} "
          f"failed={FAILED} (harmonyos_specific=4)")
    if FAILED:
        raise AssertionError(f"{FAILED} assertion(s) failed")
    print("rudof test_package OK: HarmonyOS traits + functionality verified")


if __name__ == "__main__":
    sys.exit(main())
