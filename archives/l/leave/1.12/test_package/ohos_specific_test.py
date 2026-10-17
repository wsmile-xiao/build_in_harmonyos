#!/usr/bin/env python3
"""HarmonyOS-specific test suite for the packaged leave 1.12 executable.

This is an INDEPENDENT HarmonyOS-specific entry (distinct from the generic
consumer entry test_leave.sh), fail closed: any failed check — including an
unexpected exception — makes the whole run fail, and nothing is silently
skipped.

  H1 ohos-elf-identity       bin/leave is ELF64 little-endian AArch64
                             (EI_CLASS=ELFCLASS64, EI_DATA=ELFDATA2LSB,
                             e_machine=EM_AARCH64=183).
  H2 ohos-musl-interpreter   PT_INTERP is exactly /lib/ld-musl-aarch64.so.1
                             (OHOS musl libc, not glibc).
  H3 ohos-no-rpath           the installed binary carries no RPATH/RUNPATH
                             dynamic entries (a terminal tool must not embed
                             host library paths).
  H4 ohos-invalid-arg-exit   actually runs `leave 9999` on the OHOS PC: exit
                             status 1 and "Usage: leave [[+]hhmm]" on stderr.
  H5 ohos-noarg-eof          actually runs `leave` with stdin at EOF: prints
                             "When do you have to leave?" and exits 0.
  H6 ohos-valid-schedule     actually runs `leave +6`: the parent exits 0 and
                             the forked child announces the alarm; the child
                             is then killed and confirmed gone.

Usage: ohos_specific_test.py <path-to-installed-leave>
Exit code: 0 all checkpoints passed, 1 any failure (fail closed).
"""

import os
import re
import signal
import struct
import subprocess
import sys
import time

# ELF constants (self-contained header parse; readelf is only used for H3).
ELFCLASS64 = 2
ELFDATA2LSB = 1
EM_AARCH64 = 183
PT_INTERP = 3


def find_readelf():
    import shutil

    for cand in (
        shutil.which("llvm-readelf"),
        shutil.which("readelf"),
        "/data/service/hnp/bin/readelf",
    ):
        if cand and os.path.isfile(cand):
            return cand
    return None


def check_elf_identity(blob):
    """H1: ELF64 little-endian AArch64 via a direct header parse."""
    if len(blob) < 64 or blob[:4] != b"\x7fELF":
        return False, "not an ELF file"
    ei_class, ei_data = blob[4], blob[5]
    if ei_class != ELFCLASS64:
        return False, "EI_CLASS=%d is not ELF64" % ei_class
    if ei_data != ELFDATA2LSB:
        return False, "EI_DATA=%d is not little-endian" % ei_data
    e_machine = struct.unpack_from("<H", blob, 18)[0]
    if e_machine != EM_AARCH64:
        return False, "e_machine=%d is not EM_AARCH64 (%d)" % (e_machine, EM_AARCH64)
    return True, "ELF64 little-endian AArch64"


def check_pt_interp(blob):
    """H2: program interpreter is exactly /lib/ld-musl-aarch64.so.1."""
    e_phoff = struct.unpack_from("<Q", blob, 0x20)[0]
    e_phentsize = struct.unpack_from("<H", blob, 0x36)[0]
    e_phnum = struct.unpack_from("<H", blob, 0x38)[0]
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type = struct.unpack_from("<I", blob, off)[0]
        if p_type == PT_INTERP:
            p_offset = struct.unpack_from("<Q", blob, off + 8)[0]
            end = blob.index(b"\x00", p_offset)
            interp = blob[p_offset:end].decode("ascii", "replace")
            if interp == "/lib/ld-musl-aarch64.so.1":
                return True, interp
            return False, "interpreter is %r" % interp
    return False, "no PT_INTERP segment"


def check_no_rpath(binary):
    """H3: no RPATH/RUNPATH dynamic entries."""
    readelf = find_readelf()
    if not readelf:
        return False, "no readelf available (fail closed)"
    proc = subprocess.run(
        [readelf, "-d", binary], capture_output=True, text=True, timeout=30
    )
    hits = [
        line
        for line in proc.stdout.splitlines()
        if "RPATH" in line or "RUNPATH" in line
    ]
    if hits:
        return False, "RPATH/RUNPATH present: %s" % hits
    return True, "no RPATH/RUNPATH"


def check_invalid_arg(binary):
    """H4: run `leave 9999` and assert usage + exit 1."""
    proc = subprocess.run(
        [binary, "9999"], capture_output=True, text=True, timeout=30
    )
    if proc.returncode != 1:
        return False, "exit status %d (expected 1)" % proc.returncode
    if "Usage: leave" not in proc.stderr:
        return False, "stderr=%r" % proc.stderr
    return True, "exit 1 + usage on stderr"


def check_noarg_eof(binary):
    """H5: run `leave` with stdin at EOF and assert prompt + exit 0."""
    proc = subprocess.run(
        [binary],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        return False, "exit status %d (expected 0)" % proc.returncode
    if "When do you have to leave?" not in proc.stdout:
        return False, "stdout=%r" % proc.stdout
    return True, "prompt printed + exit 0"


def check_valid_schedule(binary, tmpdir):
    """H6: run `leave +6`, assert the alarm announcement, kill the child."""
    out_path = os.path.join(tmpdir, "ohos-leave-schedule.txt")
    # Redirect to a *file*, not a pipe: the forked child keeps the pipe open
    # and would otherwise block the test until its nagging loop finishes.
    with open(out_path, "wb") as fh:
        proc = subprocess.run(
            [binary, "+6"], stdout=fh, stderr=subprocess.STDOUT, timeout=30
        )
    if proc.returncode != 0:
        return False, "parent exit status %d (expected 0)" % proc.returncode

    text = ""
    for _ in range(20):
        text = open(out_path, encoding="utf-8", errors="replace").read()
        if "Alarm set for" in text:
            break
        time.sleep(0.5)
    if "Alarm set for" not in text:
        return False, "no alarm announcement (output=%r)" % text

    match = re.search(r"\(pid\s+(\d+)\)", text)
    if not match:
        return False, "no pid in announcement: %r" % text
    pid = int(match.group(1))

    os.kill(pid, signal.SIGKILL)
    for _ in range(20):
        try:
            os.kill(pid, 0)
        except OSError:
            return True, "alarm announced (pid %d), child killed" % pid
        time.sleep(0.25)
    return False, "child pid %d still alive after SIGKILL" % pid


def main():
    if len(sys.argv) < 2:
        print("usage: ohos_specific_test.py <path-to-leave>")
        return 2

    binary = sys.argv[1]
    if not os.path.isfile(binary):
        print("FAIL: executable not found: %s" % binary)
        return 1

    tmpdir = os.environ.get("TMPDIR") or os.path.expanduser("~/tmp")
    os.makedirs(tmpdir, exist_ok=True)

    blob = open(binary, "rb").read()

    checks = [
        ("H1 ohos-elf-identity", lambda: check_elf_identity(blob)),
        ("H2 ohos-musl-interpreter", lambda: check_pt_interp(blob)),
        ("H3 ohos-no-rpath", lambda: check_no_rpath(binary)),
        ("H4 ohos-invalid-arg-exit", lambda: check_invalid_arg(binary)),
        ("H5 ohos-noarg-eof", lambda: check_noarg_eof(binary)),
        ("H6 ohos-valid-schedule", lambda: check_valid_schedule(binary, tmpdir)),
    ]

    failed = 0
    for name, func in checks:
        try:
            ok, detail = func()
        except Exception as exc:  # fail closed
            ok, detail = False, "exception: %r" % exc
        print("%s %s: %s" % ("PASS" if ok else "FAIL", name, detail))
        if not ok:
            failed += 1

    print(
        "---- ohos_specific_test.py: %d/%d checks passed ----"
        % (len(checks) - failed, len(checks))
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
