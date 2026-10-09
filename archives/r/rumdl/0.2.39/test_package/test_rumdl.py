#!/usr/bin/env python3
"""Conan consumer test for rumdl 0.2.39.

Layers of assertions:

  A. Generic consumer smoke/functional test — runs the packaged `rumdl`:
       A1 `rumdl --version` exits 0 and reports 0.2.39
       A2 `rumdl --help` exits 0 and lists the `check`/`fmt` sub-commands
       A3 `rumdl check <file.md>` on a file that violates built-in rules
          exits non-zero and names at least one rule id (MD###)
       A4 `rumdl fmt <file.md>` actually rewrites the file (trailing
          whitespace removed)

  B. HarmonyOS-specific (鸿蒙特有) assertions — verify the platform traits
     that make the artifact usable on OHOS at all:
       B1. ELF machine is AArch64 (the OHOS PC target)
       B2. PT_INTERP is the OHOS musl loader (ld-musl-aarch64.so.1)
       B3. the binary carries an OHOS code signature — HarmonyOS refuses to
           execve unsigned ELF (EACCES errno 13), so this is mandatory
       B4. the binary is a non-empty regular executable file

Every assertion is reported on its own line so the counts quoted in the PR
description stay auditable.
"""

import os
import re
import struct
import subprocess
import sys
import tempfile

PASSED = 0
FAILED = 0

OHOS_MUSL_LOADER = "ld-musl-aarch64.so.1"
EM_AARCH64 = 183

BAD_MARKDOWN = (
    "# Title   \n"
    "\n"
    "This line is deliberately made much longer than the default maximum "
    "line length of eighty characters so that a line-length rule fires.   \n"
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
    exe = os.path.join(package_folder, "bin", "rumdl")

    # ── B. 鸿蒙特有测试 (HarmonyOS-specific) ──
    print("== 鸿蒙特有测试 / HarmonyOS-specific assertions ==")
    if not check("B4: rumdl is a non-empty regular executable file",
                 os.path.isfile(exe) and os.path.getsize(exe) > 0,
                 f"{exe} ({os.path.getsize(exe) if os.path.isfile(exe) else 0} bytes)"):
        raise AssertionError(f"Missing rumdl executable: {exe}")

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
    version_run = subprocess.run(
        [exe, "--version"], capture_output=True, text=True, timeout=30
    )
    check("A1: `rumdl --version` exits 0 and reports 0.2.39",
          version_run.returncode == 0 and "0.2.39" in version_run.stdout,
          f"rc={version_run.returncode} out={version_run.stdout.strip()[:80]}")

    help_run = subprocess.run(
        [exe, "--help"], capture_output=True, text=True, timeout=30
    )
    if not check("A2: `rumdl --help` exits 0 and lists check/fmt sub-commands",
                 help_run.returncode == 0
                 and "check" in help_run.stdout
                 and "fmt" in help_run.stdout,
                 f"rc={help_run.returncode}"):
        raise AssertionError(f"`rumdl --help` failed: {help_run.stderr}")

    with tempfile.TemporaryDirectory(prefix="rumdl-tp-") as work:
        md = os.path.join(work, "sample.md")
        with open(md, "w", encoding="utf-8") as fh:
            fh.write(BAD_MARKDOWN)

        # A3: lint must report at least one rule id and exit non-zero.
        check_run = subprocess.run(
            [exe, "check", md], capture_output=True, text=True, timeout=60
        )
        has_rule = re.search(r"MD\d{3}", check_run.stdout + check_run.stderr) is not None
        check("A3: `rumdl check sample.md` reports a rule violation (MD###)",
              check_run.returncode != 0 and has_rule,
              f"rc={check_run.returncode} "
              f"out={(check_run.stdout + check_run.stderr).strip().splitlines()[:1]}")

        # A4: fmt must rewrite the file (drop the trailing whitespace).
        fmt_run = subprocess.run(
            [exe, "fmt", md], capture_output=True, text=True, timeout=60
        )
        with open(md, "r", encoding="utf-8") as fh:
            fixed = fh.read()
        check("A4: `rumdl fmt sample.md` rewrites the file (trailing spaces removed)",
              all(not line.endswith(" ") for line in fixed.splitlines())
              and fixed != BAD_MARKDOWN,
              f"rc={fmt_run.returncode}")

    print(f"SUMMARY: executed={PASSED + FAILED} passed={PASSED} "
          f"failed={FAILED} (harmonyos_specific=4)")
    if FAILED:
        raise AssertionError(f"{FAILED} assertion(s) failed")
    print("rumdl test_package OK: HarmonyOS traits + functionality verified")


if __name__ == "__main__":
    sys.exit(main())
