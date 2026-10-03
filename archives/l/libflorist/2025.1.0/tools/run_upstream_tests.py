#!/usr/bin/env python3
"""Build-and-run helper for Florist's upstream POSIX.5b validation suite.

Why this exists
---------------
Florist's own runner (`tests/run_tests_1`) assumes the test binaries are
already built and executable.  On OHOS several extra things are required that
the upstream script knows nothing about:

  1. **Signing** -- OHOS refuses to exec an unsigned ELF (E489/E517), so every
     freshly linked test binary must be signed before it can run.
  2. **A terminal on stderr** -- tests/README states "Some tests require that
     the standard error file be a terminal"; redirecting stderr to a file
     manufactures failures that do not exist.  Each test is therefore run with
     stderr attached to a PTY, and the PTY is given a sane window size
     (p070200 manipulates terminal characteristics).
  3. **A fresh, hermetic working directory** -- upstream's `test.dir` target
     creates the directory once (`mkdir test.dir; ln -s .. test.dir/bin`).
     Several tests create files/directories with fixed names, so a stale
     directory makes assertions fail on a re-run.  The run directory is
     therefore recreated per run, exactly like `make test.dir`.
  4. **The run environment `run_tests_1` relies on** -- `PWD` (p040300 needs
     it), `PATH` containing the tests directory (children are started by
     *filename*, e.g. `p030100b`, via `Start_Process_Search`), a writable
     `HOME`, and a C locale/timezone.  `umask 033` before p050300 is
     reproduced verbatim from upstream's script.

Two further corrections concern *which* entries are tests at all:

  * `tests/Makefile` lists helper child programs alongside real tests so that
    they get built (e.g. `p030100b`, `p030306a`, `p990040b`).  Upstream's
    runner never runs them standalone -- it only `ln -fs ../p030100b`.  Running
    a helper standalone can never pass: it reports "bad arg" because it was
    started without the `-child <n>` argument its parent passes.  Entries that
    are a prerequisite of another listed entry are therefore recorded as
    `HELPER` and excluded from the executed census, matching upstream.
  * Every test gets its own timeout so a hanging test cannot stall the build.

A machine-readable result table is written for the R51 evidence trail.

Usage:
    run_upstream_tests.py --tests-dir <tests> --names <file> [--timeout 90]
                          [--makefile <tests/Makefile>] [--run-dir <dir>]
                          [--results <file>] [--keep-run-dir] [--only <name>]
"""
from __future__ import annotations

import argparse
import fcntl
import os
import pty
import re
import select
import shutil
import signal
import struct
import subprocess
import sys
import termios
import time

# Verdicts recorded in the result table.
VERDICT_PASS = "PASS"
VERDICT_NA = "NOT_APPLICABLE"
VERDICT_FAIL = "FAIL"
VERDICT_TIMEOUT = "TIMEOUT"
VERDICT_HELPER = "HELPER"
VERDICT_NOT_LINKED = "NOT_LINKED"

# Reproduced verbatim from tests/run_tests_1: "umask 033" precedes p050300.
PER_TEST_UMASK = {"p050300": 0o033}
DEFAULT_UMASK = 0o022
# Upstream runs from the tests directory so the children resolve through ./bin.
PTY_COLS, PTY_ROWS = 80, 24


def sign_executable(path: str) -> bool:
    """Sign an ELF in place so OHOS will execute it."""
    objcopy = shutil.which("llvm-objcopy")
    signer = shutil.which("binary-sign-tool")
    if not objcopy or not signer:
        return False
    try:
        subprocess.run([objcopy, "--remove-section", ".codesign", path],
                       check=False, capture_output=True)
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", path,
                        "-selfSign", "1"], check=False, capture_output=True)
        return True
    except OSError:
        return False


def helper_entries(makefile: str, listed) -> set:
    """Listed entries that are helpers for another listed entry.

    `tests/Makefile` writes e.g. `p030100: p030100.ads p030100.adb p030100b`
    and `p030306: p030306.ads p030306.adb p030306a p030300a`.  A listed entry
    that also appears as a prerequisite of another listed entry is a child
    program: upstream's run_tests_1/run_tests_2 only `ln -fs` it and never
    executes it.  Sources (`.ads`/`.adb`/`.c`/`.o`) are not listed entries and
    are ignored.
    """
    if not makefile or not os.path.isfile(makefile):
        return set()
    listed_set = set(listed)
    helpers = set()
    with open(makefile, "r", errors="replace") as handle:
        for line in handle:
            if line.startswith(("\t", "#")) or ":" not in line:
                continue
            target, _, prereqs = line.partition(":")
            target = target.strip().rstrip("\\")
            if target not in listed_set:
                continue
            for token in prereqs.replace("\\", " ").split():
                if token in listed_set and token != target:
                    helpers.add(token)
    return helpers


def run_one(executable: str, run_dir: str, timeout: int, env: dict):
    """Run one test with stderr on a PTY; return (text, timed_out, returncode).

    Many Florist tests fork children that keep the PTY slave open after the test
    process itself has finished, so "no data for `timeout` seconds" is NOT a
    reliable hang signal.  The child's own exit is authoritative: once it has
    exited, remaining output is drained with a short idle grace period.
    """
    master, slave = pty.openpty()
    try:
        # Give the PTY a sane window size: tests/README notes that some tests
        # manipulate terminal characteristics, and a 0x0 winsize makes those
        # ioctl() calls fail.
        try:
            fcntl.ioctl(master, termios.TIOCSWINSZ,
                        struct.pack("HHHH", PTY_ROWS, PTY_COLS, 0, 0))
        except OSError:
            pass
        # stdin, stdout and stderr all sit on the PTY: tests/README requires a
        # terminal on stderr, and the tests that manipulate terminal
        # characteristics (p060100, p070200) issue tcsetattr on fd 0, which
        # fails with ENOTTY under /dev/null.
        proc = subprocess.Popen([executable, "-t"], stdin=slave,
                                stdout=slave, stderr=slave, cwd=run_dir,
                                env=env, start_new_session=True)
    except OSError as exc:
        os.close(master)
        os.close(slave)
        return ("exec failed: {}".format(exc), False, None)
    os.close(slave)

    idle_grace = 3          # seconds of silence tolerated after the child exits
    chunks = []
    timed_out = False
    deadline = time.monotonic() + timeout
    done_at = None
    try:
        while True:
            if proc.poll() is not None:
                if done_at is None:
                    done_at = time.monotonic()
                elif time.monotonic() - done_at > idle_grace:
                    break
            now = time.monotonic()
            if now > deadline:
                timed_out = True
                break
            wait = min(1.0, max(0.05, deadline - now))
            ready, _, _ = select.select([master], [], [], wait)
            if not ready:
                continue
            try:
                data = os.read(master, 65536)
            except OSError:
                break
            if not data:
                break
            chunks.append(data)
    finally:
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
        proc.wait()
        os.close(master)
    return (b"".join(chunks).decode("utf-8", "replace"), timed_out, proc.returncode)


def classify(text: str, timed_out: bool, returncode) -> str:
    if timed_out:
        return VERDICT_TIMEOUT
    if "Test Completed Successfully" in text:
        return VERDICT_PASS
    # Upstream prints this when the optional feature under test is absent on the
    # platform -- upstream's own verdict is "not a failure", so record it as
    # NOT_APPLICABLE instead of lumping it with assertion failures.
    if "Test Not Applicable" in text:
        return VERDICT_NA
    if "!!TEST FAILED" in text:
        return VERDICT_FAIL
    if returncode == 0:
        return "NO_MARKER"
    return "CRASH_{}".format(returncode)


def prepare_run_dir(run_dir: str, names) -> None:
    """Recreate the run directory the way upstream's runner does.

    Upstream does two things here that are easy to miss and both matter:

      * `make test.dir` builds `bin -> ..`;
      * `run_tests_1` then `ln -fs ../<name>` for the entries a test starts as a
        *child* (p030100b, p030101b, p030102, p030301b, p030306a, p120101,
        p120502a, p150100b).  `Start_Process_Search` resolves a bare filename
        through PATH, so those names must be reachable by their plain name.

    The directory is recreated from scratch because several tests create
    files/directories with fixed names; a stale directory makes assertions fail
    on a re-run.
    """
    if os.path.isdir(run_dir):
        shutil.rmtree(run_dir, ignore_errors=True)
    os.makedirs(run_dir, exist_ok=True)
    for name in names:
        link = os.path.join(run_dir, name)
        if not os.path.lexists(link):
            try:
                os.symlink(os.path.join(os.path.pardir, name), link)
            except OSError:
                pass
    link = os.path.join(run_dir, "bin")
    if not os.path.lexists(link):
        try:
            os.symlink(os.path.pardir, link)
        except OSError:
            pass
    os.makedirs(os.path.join(run_dir, "home"), exist_ok=True)


def test_env(tests_dir: str, run_dir: str) -> dict:
    """Environment upstream's run_tests_1 implicitly relies on."""
    env = dict(os.environ)
    env["PATH"] = tests_dir + os.pathsep + env.get("PATH", "/bin:/usr/bin")
    env["PWD"] = run_dir            # p040300 asserts on PWD
    env["HOME"] = os.path.join(run_dir, "home")
    env["TMPDIR"] = run_dir
    env["LC_ALL"] = "C"
    env["LANG"] = "C"
    env["TZ"] = "UTC"
    env["TERM"] = env.get("TERM") or "xterm"
    return env


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--tests-dir", required=True)
    parser.add_argument("--names", required=True,
                        help="file with one test name per line")
    parser.add_argument("--makefile", default="",
                        help="tests/Makefile, used to spot helper children")
    parser.add_argument("--run-dir", default="")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--results", default="")
    parser.add_argument("--only", default="",
                        help="run a single named test (single-test re-check)")
    parser.add_argument("--symlink-from", default="",
                        help="extra name list whose entries get a test.dir "
                             "symlink (full census while re-checking a subset)")
    parser.add_argument("--keep-run-dir", action="store_true",
                        help="do not recreate the run directory")
    args = parser.parse_args(argv)

    tests_dir = os.path.abspath(args.tests_dir)
    run_dir = os.path.abspath(args.run_dir or os.path.join(tests_dir, "test.dir"))
    results_path = args.results or os.path.join(run_dir, "upstream-results.txt")

    with open(args.names, "r", errors="replace") as handle:
        names = [line.strip() for line in handle if line.strip()]

    makefile = args.makefile or os.path.join(tests_dir, "Makefile")
    helpers = helper_entries(makefile, names)
    print("[census] test entries listed: {}".format(len(names)))
    print("[census] helper children (not independent tests): {}".format(
        " ".join(sorted(helpers)) or "none"))

    if args.only:
        names = [args.only]
    # The run directory must be clean: upstream's `make test.dir` builds it once
    # and several tests create fixed-name files/directories.
    if not args.keep_run_dir:
        link_names = list(names)
        if args.symlink_from and os.path.isfile(args.symlink_from):
            with open(args.symlink_from, "r", errors="replace") as handle:
                for line in handle:
                    token = line.strip()
                    if token and token not in link_names:
                        link_names.append(token)
        prepare_run_dir(run_dir, link_names)
    env = test_env(tests_dir, run_dir)

    rows = []
    for name in names:
        if name in helpers and not args.only:
            # Recorded for census honesty, but not executed: upstream never runs
            # a helper standalone, and a standalone helper always reports
            # "bad arg" because its parent supplies the `-child <n>` argument.
            rows.append((name, VERDICT_HELPER))
            print("  %-12s %s" % (name, VERDICT_HELPER), flush=True)
            continue
        executable = os.path.join(tests_dir, name)
        if not os.path.isfile(executable):
            rows.append((name, VERDICT_NOT_LINKED))
            print("  %-12s %s" % (name, VERDICT_NOT_LINKED), flush=True)
            continue
        sign_executable(executable)
        os.umask(PER_TEST_UMASK.get(name, DEFAULT_UMASK))
        text, timed_out, rc = run_one(executable, run_dir, args.timeout, env)
        os.umask(DEFAULT_UMASK)
        with open(os.path.join(run_dir, "{}.log".format(name)), "w") as handle:
            handle.write(text)
        verdict = classify(text, timed_out, rc)
        rows.append((name, verdict))
        print("  %-12s %s" % (name, verdict), flush=True)

    with open(results_path, "w") as handle:
        for name, verdict in rows:
            handle.write("{} {}\n".format(name, verdict))

    total = len(rows)
    executed = sum(1 for _, v in rows
                   if v not in (VERDICT_NOT_LINKED, VERDICT_HELPER))
    passed = sum(1 for _, v in rows if v == VERDICT_PASS)
    print("[census] entries={} helpers={} executed={} passed={}".format(
        total, len(helpers), executed, passed))
    print("[census] results table: {}".format(results_path))
    # Never fail the build on upstream assertion failures: they are recorded as
    # R51 evidence and explained in the test report.  Only a missing suite is an
    # error (there is nothing to report).
    return 0 if rows else 1


if __name__ == "__main__":
    sys.exit(main())
