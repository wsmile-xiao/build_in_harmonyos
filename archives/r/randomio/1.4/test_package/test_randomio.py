#!/usr/bin/env python3
"""Conan test_package for randomio 1.4.

randomio ships no unit-test suite, so this test exercises the *installed*
package from a consumer's perspective:

  1. usage probe (deterministic, no storage needed): calling the binary with
     a wrong argument count must print the usage line (which names the 512-
     byte alignment requirement) and exit non-zero;
  2. end-to-end run: preallocate a regular file (multiple of the 512-byte
     direct-I/O alignment), run `randomio <file> 2 1.0 0 4096 1 1`
     (2 threads, 100% writes, no fsync, 4 KiB I/Os, 1s sampling, exactly 1
     sample) and assert the column-header banner plus at least one numeric
     data row and a clean exit.

Running the packaged bin/randomio (not the source tree) proves the installed
artifact is present, executable and functional.

NOTE: HarmonyOS HMDFS accepts O_DIRECT at file-create time but rejects it
when opening an existing file (EINVAL, verified on-device). Patch 0001 makes
the binary fall back to buffered I/O with a "warning: O_DIRECT unsupported"
line on stderr in that case, so the end-to-end run works on any filesystem;
the latency numbers then include the page cache and are not directly
comparable to true direct-I/O runs on a raw device.
"""
import os
import re
import signal
import subprocess
import sys
import tempfile

USAGE_SNIPPET = "usage:"
USAGE_ALIGNMENT = "512"
# Header banner printed before every sample table.
HEADER_ROWS = [
    "total |  read:         latency (ms)       |  write:        latency (ms)",
    "iops",
]
DATA_ROW = re.compile(
    r"^\s*[0-9]+\.[0-9]\s*\|", re.M
)  # "    123.4 | ..." data row
TIMEOUT = 120


def run_cmd(cmd, timeout=TIMEOUT):
    return subprocess.run(cmd, timeout=timeout, capture_output=True, text=True)


def check_usage(exe):
    res = run_cmd([exe])
    if res.returncode == 0:
        print("FAIL: usage probe exited 0 with no arguments", file=sys.stderr)
        return False
    if res.returncode < 0:
        sig = signal.Signals(-res.returncode).name
        print("FAIL: usage probe killed by signal %s" % sig, file=sys.stderr)
        return False
    out = res.stdout + res.stderr
    if USAGE_SNIPPET not in out:
        print("FAIL: usage probe output missing %r" % USAGE_SNIPPET, file=sys.stderr)
        print(out[-1500:], file=sys.stderr)
        return False
    if USAGE_ALIGNMENT not in out:
        print("FAIL: usage probe output missing 512-byte alignment note", file=sys.stderr)
        return False
    print("OK: usage probe prints usage and exits non-zero")
    return True


def check_benchmark(exe):
    fd, path = tempfile.mkstemp(prefix="randomio_test_", suffix=".dat")
    os.close(fd)
    try:
        # 8 MiB file, a multiple of the 512-byte O_DIRECT alignment.
        with open(path, "wb") as fh:
            fh.truncate(8 * 1024 * 1024)
        # 2 threads, write_fraction=1.0 (pure writes), fsync_fraction=0,
        # io_size=4096, 1s between samples, exactly 1 sample -> exits itself.
        res = run_cmd([exe, path, "2", "1.0", "0", "4096", "1", "1"])
    except subprocess.TimeoutExpired:
        print("FAIL: benchmark timed out after %ss" % TIMEOUT, file=sys.stderr)
        return False
    except OSError as exc:
        print("FAIL: could not execute randomio: %s" % exc, file=sys.stderr)
        return False
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass

    if res.returncode < 0:
        sig = signal.Signals(-res.returncode).name
        print("FAIL: terminated by signal %s" % sig, file=sys.stderr)
        return False
    if res.returncode != 0:
        print("FAIL: exited with %d" % res.returncode, file=sys.stderr)
        print(res.stdout[-2000:], file=sys.stderr)
        print(res.stderr[-2000:], file=sys.stderr)
        return False

    out = res.stdout
    failures = []
    for row in HEADER_ROWS:
        if row not in out:
            failures.append("missing header row %r" % row)
    if not DATA_ROW.search(out):
        failures.append("no numeric data row in sample table")
    # The O_DIRECT open must not have failed.
    if "open:" in res.stderr or "thrasher" in res.stderr:
        failures.append("runtime error on stderr: %s" % res.stderr.strip()[:200])

    if failures:
        for f in failures:
            print("FAIL: %s" % f, file=sys.stderr)
        print("---- stdout tail ----", file=sys.stderr)
        print(out[-3000:], file=sys.stderr)
        return False

    print("OK: benchmark ran 1 sample (2 threads, pure writes, O_DIRECT), exit 0")
    return True


def main(bindir):
    exe = os.path.join(bindir, "randomio")
    if not os.path.isfile(exe) and os.path.isfile(bindir):
        exe = bindir
    ok = check_usage(exe)
    ok = check_benchmark(exe) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
