#!/usr/bin/env python3
"""Functional tests for the packaged sleepenh 1.8 executable.

Upstream ships no test suite (the archive holds sleepenh.c, sleepenh.1,
Makefile, changelog and .gitignore; the Makefile has no check/test target,
see MANIFEST.yml for the R51 census), so this script checks the packaged
binary against the behaviour documented in sleepenh.c and sleepenh.1: print
the absolute end time, exit 0 after a real sleep, exit 1 when no sleep was
needed, exit 10/12 on bad arguments.

Artifact checks (every host):
  A1  bin/sleepenh is an ELF64 little-endian EM_AARCH64 image
  A2  position-independent executable (ET_DYN)
  A3  PT_INTERP is the OHOS musl loader /lib/ld-musl-aarch64.so.1
  A4  share/man/man1/sleepenh.1 is the upstream man page (.TH SLEEPENH 1)

Functional checks (need a host that can execute the image):
  F1  --version / -V   first stdout line "sleepenh 1.8", exit 0 (the version
                       is injected at build time, the archive has no .git)
  F2  --help / -h      usage names the program "sleepenh", exit 0 (patch: the
                       name comes from argv[0], not program_invocation_short_name)
  F3  no argument      version and usage on stderr, empty stdout, exit 10
  F4  inf / nan        exit 12 with empty stdout, for TIMETOSLEEP and INITIALTIME
  F5  expired start    "1000.25 0.5" prints 1000.750000 without sleeping, exit 1
  F6  --warp           end time warped to INITIALTIME + k * 0.5 inside the last
                       0.5 s before the call returned, exit 1
  F7  real sleep 0.3s  SIGALRM through setitimer()/pause(): exit 0, at least
                       0.29 s elapsed, printed end time inside the run window
  F8  chained sleeps   T0=$(sleepenh 0) exits 1; "sleepenh T 0.5" twice prints
                       exactly T0+0.5 and T0+1.0 and exits 0: no cumulative drift
Every run is bounded by a 30 s timeout; the script writes no files.

On an aarch64 host (the OHOS CI worker) every functional check is mandatory.
On a foreign-architecture host the functional layer is reported as SKIPPED -
never as passed - and only when launching the image fails with an explicit
loader/format marker; an image that starts is always judged by the checks.

usage: test_sleepenh.py <sleepenh package folder>
"""
import errno
import os
import platform
import re
import struct
import subprocess
import sys
import time

EM_AARCH64 = 183
ET_DYN = 3
PT_INTERP = 3
OHOS_LOADER = "/lib/ld-musl-aarch64.so.1"
AARCH64_HOSTS = ("aarch64", "arm64", "armv8", "armv8l")
NOT_EXECUTABLE_MARKERS = (
    "Could not open '/lib/ld-musl",   # qemu-user via binfmt_misc: target loader absent
    "Exec format error",              # kernel refused the image
)
TIMEOUT = 30
VERSION_LINE = "sleepenh 1.8"
USAGE_LINE = "Usage: sleepenh [[--warp|-w] INITIALTIME] TIMETOSLEEP"
TIMESTAMP = re.compile(r"\d+\.\d{6}\n\Z")
FUNCTIONAL = ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8")

failures = []


def record(check_id, ok, detail):
    print(f"[{'ok' if ok else 'FAIL'}] {check_id} {detail}")
    if not ok:
        failures.append(check_id)
    return ok


def run(binary, *args):
    """Run the image; return (exit code, stdout, stderr, elapsed seconds)."""
    start = time.monotonic()
    proc = subprocess.run([binary, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=TIMEOUT, universal_newlines=True)
    return proc.returncode, proc.stdout, proc.stderr, time.monotonic() - start


def elf_facts(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
        return None
    e_type, e_machine = struct.unpack_from("<HH", data, 16)
    e_phoff = struct.unpack_from("<Q", data, 32)[0]
    e_phentsize, e_phnum = struct.unpack_from("<HH", data, 54)
    interp = None
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        if struct.unpack_from("<I", data, off)[0] == PT_INTERP:
            p_offset = struct.unpack_from("<Q", data, off + 8)[0]
            p_filesz = struct.unpack_from("<Q", data, off + 32)[0]
            interp = data[p_offset:p_offset + p_filesz].rstrip(b"\0").decode("ascii", "replace")
    return {"type": e_type, "machine": e_machine, "interp": interp}


def artifact_checks(binary, man_page):
    facts = elf_facts(binary)
    record("A1", facts is not None and facts["machine"] == EM_AARCH64,
           "ELF64 little-endian EM_AARCH64 image")
    record("A2", facts is not None and facts["type"] == ET_DYN,
           "position-independent executable (ET_DYN)")
    record("A3", facts is not None and facts["interp"] == OHOS_LOADER,
           f"PT_INTERP is {OHOS_LOADER} (found {facts and facts['interp']})")
    head = ""
    if os.path.isfile(man_page):
        with open(man_page, encoding="utf-8", errors="replace") as f:
            head = f.read(4096)
    record("A4", re.search(r"^\.TH SLEEPENH 1 ", head, re.M) is not None,
           "share/man/man1/sleepenh.1 is the upstream man page")


def launch_failure(binary):
    """None when the image starts, otherwise the loader/format failure text."""
    try:
        rc, _, err, _ = run(binary, "--version")
    except OSError as exc:
        if exc.errno == errno.ENOEXEC:
            return f"Exec format error ({exc})"
        raise
    if rc != 0 and any(marker in err for marker in NOT_EXECUTABLE_MARKERS):
        return err.strip().splitlines()[0]
    return None


def f1(binary):
    runs = [run(binary, opt) for opt in ("--version", "-V")]
    ok = all(rc == 0 and out.splitlines()[:1] == [VERSION_LINE] and "GPLv2+" in out and err == ""
             for rc, out, err, _ in runs) and runs[0][1] == runs[1][1]
    return ok, f"--version / -V print '{VERSION_LINE}', exit 0"


def f2(binary):
    runs = [run(binary, opt) for opt in ("--help", "-h")]
    ok = all(rc == 0 and out.startswith(USAGE_LINE + "\n") and err == ""
             for rc, out, err, _ in runs) and runs[0][1] == runs[1][1]
    return ok, "--help / -h usage names the program 'sleepenh', exit 0"


def f3(binary):
    rc, out, err, _ = run(binary)
    ok = rc == 10 and out == "" and err.startswith(VERSION_LINE + "\n") and USAGE_LINE in err
    return ok, f"no argument: version + usage on stderr, exit 10 (got {rc})"


def f4(binary):
    codes = [run(binary, *args)[:2] for args in (("inf",), ("nan",), ("nan", "1"))]
    ok = all(rc == 12 and out == "" for rc, out in codes)
    return ok, f"inf / nan / nan INITIALTIME rejected with exit 12 (got {[c for c, _ in codes]})"


def f5(binary):
    rc, out, err, _ = run(binary, "1000.25", "0.5")
    ok = rc == 1 and out == "1000.750000\n" and err == ""
    return ok, f"expired start prints 1000.750000, exit 1 (got {rc}, {out.strip()!r})"


def f6(binary):
    rc0, out0, _, _ = run(binary, "0")
    initial = f"{float(out0) - 10.2:.6f}"
    before = time.time()
    rc, out, _, _ = run(binary, "--warp", initial, "0.5")
    after = time.time()
    value = float(out)
    steps = (value - float(initial)) / 0.5
    ok = (rc0 == 1 and rc == 1 and TIMESTAMP.match(out) is not None
          and abs(steps - round(steps)) < 1e-3 and round(steps) >= 20
          and before - 0.55 < value <= after + 0.05)
    return ok, f"--warp moves the end time to INITIALTIME + {round(steps)} * 0.5, exit 1 (got {rc})"


def f7(binary):
    before = time.time()
    rc, out, err, elapsed = run(binary, "0.3")
    after = time.time()
    ok = (rc == 0 and err == "" and TIMESTAMP.match(out) is not None and 0.29 <= elapsed < 10
          and before + 0.25 <= float(out) <= after + 0.05)
    return ok, f"sleeps 0.3 s until SIGALRM, exit 0 (got {rc}, {elapsed:.3f} s)"


def f8(binary):
    rc0, t0, _, _ = run(binary, "0")
    rc1, t1, _, _ = run(binary, t0.strip(), "0.5")
    rc2, t2, _, _ = run(binary, t1.strip(), "0.5")
    after = time.time()
    ok = (rc0 == 1 and TIMESTAMP.match(t0) is not None
          and rc1 == 0 and t1 == "%f\n" % (float(t0) + 0.5)
          and rc2 == 0 and t2 == "%f\n" % (float(t1) + 0.5)
          and after >= float(t0) + 1.0 - 0.05)
    return ok, f"chained calls end at T0+0.5 and T0+1.0 exactly, exits {rc0}/{rc1}/{rc2}"


def functional_checks(binary):
    for check_id, check in zip(FUNCTIONAL, (f1, f2, f3, f4, f5, f6, f7, f8)):
        try:
            ok, detail = check(binary)
        except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        record(check_id, ok, detail)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__.rsplit("usage: ", 1)[1])
    package_folder = sys.argv[1]
    binary = os.path.join(package_folder, "bin", "sleepenh")
    man_page = os.path.join(package_folder, "share", "man", "man1", "sleepenh.1")
    if not os.path.isfile(binary):
        record("A1", False, f"missing package binary {binary}")
        return 1

    artifact_checks(binary, man_page)
    artifact_failed = len(failures)

    host = platform.machine().lower()
    reason = launch_failure(binary)
    if reason is None:
        functional_checks(binary)
        summary = f"functional checks {len(FUNCTIONAL) - (len(failures) - artifact_failed)}/{len(FUNCTIONAL)} passed"
    elif host in AARCH64_HOSTS:
        record("F1-F8", False, f"image does not start on this aarch64 host: {reason}")
        summary = "functional checks could not run on an aarch64 host"
    else:
        print(f"[skip] F1-F8 not run: this {host} host cannot execute the aarch64 OHOS image ({reason})")
        summary = f"functional checks 0/{len(FUNCTIONAL)} run (SKIPPED)"

    print(f"RESULT: artifact checks {4 - artifact_failed}/4 passed, {summary}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
