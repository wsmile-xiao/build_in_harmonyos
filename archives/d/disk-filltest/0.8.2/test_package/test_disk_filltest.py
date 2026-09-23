#!/usr/bin/env python3
"""Functional regression tests for the OHOS package of disk-filltest 0.8.2.

disk-filltest writes random files until the filesystem reports full, so every
invocation here is hard-bounded with -S 1 -f 1 and runs inside a scratch
directory that is deleted in the finally block. Never call the binary from this
suite without both bounds.
"""

import os
import shutil
import subprocess
import sys
import tempfile

EXE = sys.argv[1]
SEED = "1234"
TIMEOUT = 300

results = []


def check(condition, label, detail=""):
    status = "PASS" if condition else "FAIL"
    print("%s  %s" % (status, label))
    if detail and not condition:
        print("      %s" % detail.strip().replace("\n", "\n      "))
    results.append((label, bool(condition)))
    return bool(condition)


def run(args, cwd):
    return subprocess.run(
        [EXE] + list(args), cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT
    )


def out(proc):
    return proc.stdout + proc.stderr


def writable_base():
    for candidate in (os.getcwd(), os.environ.get("TMPDIR"), tempfile.gettempdir()):
        if candidate and os.path.isdir(candidate) and os.access(candidate, os.W_OK):
            return candidate
    raise RuntimeError("no writable scratch directory for functional tests")


def toggle_byte(path):
    with open(path, "rb") as handle:
        data = bytearray(handle.read())
    data[8192] ^= 0xFF
    with open(path, "wb") as handle:
        handle.write(bytes(data))


root = os.path.join(writable_base(), "dft-selftest-%d" % os.getpid())
shutil.rmtree(root, ignore_errors=True)
os.makedirs(root)

try:
    proc = run(["-V"], root)
    check(
        proc.returncode == 0 and "disk-filltest 0.8.2" in out(proc),
        "T1 -V prints the packaged version",
        out(proc),
    )

    proc = run(["-h"], root)
    check(
        proc.returncode != 0 and "Usage:" in out(proc),
        "T2 -h prints usage and exits non-zero",
        out(proc),
    )

    work = os.path.join(root, "fill")
    os.makedirs(work)
    proc = run(["-C", work, "-s", SEED, "-S", "1", "-f", "1", "-u"], root)
    text = out(proc)
    check(proc.returncode == 0, "T3 bounded fill+verify exits 0", text)
    check("Wrote 1 MiB random data to random-00000000" in text, "T3 one MiB file written", text)
    check("Successfully verified 1 files" in text, "T3 random sequence verified", text)
    check(os.listdir(work) == [], "T3 -u removes the scratch files", repr(os.listdir(work)))

    kept = os.path.join(root, "kept")
    os.makedirs(kept)
    proc = run(["-C", kept, "-s", SEED, "-S", "1", "-f", "1"], root)
    text = out(proc)
    check(
        proc.returncode == 0 and os.path.isfile(os.path.join(kept, "random-00000000")),
        "T4 fill without -u keeps random-00000000",
        text,
    )

    proc = run(["-C", kept, "-r", "-s", SEED, "-S", "1"], root)
    text = out(proc)
    check(
        proc.returncode == 0 and "Successfully verified 1 files" in text,
        "T5 -r re-verifies the stored file with the same seed",
        text,
    )

    toggle_byte(os.path.join(kept, "random-00000000"))
    proc = run(["-C", kept, "-r", "-s", SEED, "-S", "1"], root)
    text = out(proc)
    check(
        proc.returncode != 0 and "Mismatch to random sequence" in text,
        "T6 corrupted block is detected as a mismatch",
        text,
    )

    unlink_now = os.path.join(root, "unlink")
    os.makedirs(unlink_now)
    proc = run(["-C", unlink_now, "-s", SEED, "-S", "1", "-f", "1", "-U"], root)
    text = out(proc)
    check(
        proc.returncode == 0
        and "Finished all opened file handles" in text
        and os.listdir(unlink_now) == [],
        "T7 -U verifies through file handles and leaves no files",
        text,
    )
finally:
    shutil.rmtree(root, ignore_errors=True)

failed = [label for label, ok in results if not ok]
print("disk-filltest functional tests: %d/%d passed" % (len(results) - len(failed), len(results)))
if failed:
    print("failed: " + "; ".join(failed))
    sys.exit(1)
