#!/usr/bin/env python3
"""Consumer regression tests for the OHOS package of mhddfs 0.1.39.0.

mhddfs is a FUSE union filesystem: at runtime fuse_main() hands the merged
tree to the kernel through /dev/fuse, so a real mount only works where an
ordinary process may use the FUSE device. On HarmonyOS PC that is currently
not the case (see the package notes.md), therefore this suite verifies the
parts of the published binary that are platform independent - option parsing,
directory validation, duplicate directory elimination, mlimit parsing and the
startup diagnostics - and adds one bounded real mount attempt whose outcome is
classified as either a real mount (process stayed alive, cleaned up best
effort) or a clean diagnostic failure. Either way the binary must run, report
its state and never crash silently.
"""

import os
import shutil
import subprocess
import sys
import tempfile

EXE = sys.argv[1]
QUICK_TIMEOUT = 30
MOUNT_TIMEOUT = 20

results = []


def check(condition, label, detail=""):
    status = "PASS" if condition else "FAIL"
    print("%s  %s" % (status, label))
    if detail and not condition:
        print("      %s" % detail.strip().replace("\n", "\n      "))
    results.append((label, bool(condition)))
    return bool(condition)


def run(args, timeout=QUICK_TIMEOUT):
    """Run the binary; a timeout is reported instead of raised.

    Returns (returncode or None on timeout, combined output, timed_out).
    """
    try:
        proc = subprocess.run(
            [EXE] + list(args),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout + proc.stderr, False
    except subprocess.TimeoutExpired as exc:
        chunks = []
        for stream in (exc.stdout, exc.stderr):
            if not stream:
                continue
            chunks.append(stream if isinstance(stream, str) else stream.decode())
        return None, "".join(chunks), True


def writable_base():
    for candidate in (os.getcwd(), os.environ.get("TMPDIR"), tempfile.gettempdir()):
        if candidate and os.path.isdir(candidate) and os.access(candidate, os.W_OK):
            return candidate
    raise RuntimeError("no writable scratch directory for functional tests")


root = os.path.join(writable_base(), "mhddfs-selftest-%d" % os.getpid())
shutil.rmtree(root, ignore_errors=True)
os.makedirs(root)

try:
    proc = run(["--version"])
    check(
        proc[0] == 0 and "mhddfs version: 0.1.39.0" in proc[1],
        "T1 --version prints the packaged release and exits 0",
        proc[1],
    )

    proc = run(["-V"])
    check(
        proc[0] == 0 and "mhddfs version: 0.1.39.0" in proc[1],
        "T2 -V prints the packaged release and exits 0",
        proc[1],
    )

    proc = run([])
    check(
        proc[0] is not None and proc[0] != 0 and "Usage:" in proc[1],
        "T3 no arguments prints usage and exits non-zero",
        proc[1],
    )

    dir1 = os.path.join(root, "d1")
    dir2 = os.path.join(root, "d2")
    mnt = os.path.join(root, "mnt")
    for path in (dir1, dir2, mnt):
        os.makedirs(path)

    proc = run([dir1])
    check(
        proc[0] is not None and proc[0] != 0 and "Usage:" in proc[1],
        "T4 a single directory prints usage and exits non-zero",
        proc[1],
    )

    missing = os.path.join(root, "no-such-dir")
    proc = run([dir1, missing, mnt])
    check(
        proc[0] is not None and proc[0] != 0 and "can not stat" in proc[1],
        "T5 a nonexistent source directory is rejected with a diagnostic",
        proc[1],
    )

    plain_file = os.path.join(root, "plain-file")
    with open(plain_file, "w") as handle:
        handle.write("not a directory\n")
    proc = run([dir1, plain_file, mnt])
    check(
        proc[0] is not None and proc[0] != 0 and "is not directory" in proc[1],
        "T6 a non-directory source argument is rejected with a diagnostic",
        proc[1],
    )

    # One combined startup run: duplicate elimination + mlimit + directory list
    proc = run([dir1 + "," + dir2 + "," + dir1, mnt, "-o", "mlimit=64m"])
    check(
        "Duplicate directories" in proc[1] and "excluded from dirlist" in proc[1],
        "T7 duplicate source directories are eliminated at startup",
        proc[1],
    )
    check(
        "move size limit 67108864 bytes" in proc[1],
        "T8 mlimit=64m is parsed into 64 MiB",
        proc[1],
    )
    check(
        ("directory '%s' added to list" % dir1) in proc[1]
        and ("directory '%s' added to list" % dir2) in proc[1]
        and ("mount to: %s" % mnt) in proc[1],
        "T9 startup reports the merged directory list and the mount point",
        proc[1],
    )

    # Bounded real mount attempt: on a platform that allows FUSE from an
    # ordinary process fuse_main() stays in the foreground (timeout outcome);
    # on HarmonyOS PC it exits with a FUSE diagnostic instead. Both are
    # reported truthfully, and a mount is cleaned up best effort.
    proc = run([dir1, dir2, mnt], timeout=MOUNT_TIMEOUT)
    if proc[2]:
        for cmd in (["fusermount", "-u", mnt], ["umount", mnt]):
            try:
                subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            except Exception:
                pass
        startup_ok = (
            ("directory '%s' added to list" % dir1) in proc[1]
            and ("mount to: %s" % mnt) in proc[1]
        )
        check(
            startup_ok,
            "T10 mount attempt: fuse_main stayed in the foreground after full startup (mount supported)",
            proc[1],
        )
    else:
        check(
            proc[0] is not None and proc[0] != 0 and "fuse" in proc[1].lower(),
            "T10 real mount attempt fails cleanly with a FUSE diagnostic",
            proc[1],
        )
finally:
    shutil.rmtree(root, ignore_errors=True)

failed = [label for label, ok in results if not ok]
print("mhddfs functional tests: %d/%d passed" % (len(results) - len(failed), len(results)))
if failed:
    print("failed: " + "; ".join(failed))
    sys.exit(1)
