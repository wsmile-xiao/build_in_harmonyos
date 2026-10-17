#!/usr/bin/env python3
"""Consumer functional test for the packaged inoticoming binary.

Usage: test_inoticoming.py <inoticoming-binary> <workdir>

inoticoming is a CLI daemon, so the consumer test drives the installed
binary for real instead of linking a library:

  1. `--version` reports the packaged version.
  2. `--help` prints the action syntax (exit 0).
  3. IN_CLOSE_WRITE: a file written and closed inside the watched
     directory triggers the configured action with the {} substitution.
  4. IN_MOVED_TO: a file renamed into the watched directory triggers the
     action as well.
  5. `--suffix` filtering: non-matching arrivals are ignored, matching
     ones are still dispatched.
  6. SIGTERM shuts the daemon down with exit code 0.

Every case runs in its own freshly created directory (never a reused one)
and prints PASS/FAIL; the run ends with a machine readable
"RESULT: N passed, M failed" line (parsed by test_package/conanfile.py).
"""

import os
import shutil
import signal
import subprocess
import sys
import time

PASS = 0
FAIL = 0

ACTION_TEMPLATE = """#!/bin/sh
# inoticoming consumer-test action: $1 = marker file, $2 = matched filename
printf '%s\\n' "$2" >> "$1"
"""


def ok(message):
    global PASS
    PASS += 1
    print("PASS: %s" % message)


def bad(message):
    global FAIL
    FAIL += 1
    print("FAIL: %s" % message)


def fresh_dir(base, name):
    """Create an empty directory, removing leftovers from earlier runs."""
    path = os.path.join(base, name)
    shutil.rmtree(path, ignore_errors=True)
    os.makedirs(path)
    return path


def find_shell():
    for candidate in ("/bin/sh", "/usr/bin/sh", "/system/bin/sh"):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def write_action(path):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(ACTION_TEMPLATE)
    os.chmod(path, 0o755)
    return path


def wait_for(predicate, timeout=15.0, interval=0.05):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


def read_lines(path):
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return [line.strip() for line in handle if line.strip()]


class Daemon(object):
    """inoticoming running in --foreground mode with a pid-file handshake."""

    def __init__(self, binary, shell, case_dir, watchdir, marker,
                 extra_action_args=None):
        self.log_path = os.path.join(case_dir, "daemon.log")
        self.pid_path = os.path.join(case_dir, "daemon.pid")
        self.watchdir = watchdir
        self.marker = marker
        action = write_action(os.path.join(case_dir, "action.sh"))
        args = [binary, "--foreground", "--pid-file", self.pid_path]
        args.append(watchdir)
        args += list(extra_action_args or [])
        args += [shell, action, marker, "{}", ";"]
        self.command = args
        self.log = open(self.log_path, "wb")
        self.proc = subprocess.Popen(
            args, cwd=case_dir, stdout=self.log, stderr=subprocess.STDOUT
        )
        # Ready when the daemon wrote *its own* pid: a stale pid file from a
        # previous run can never satisfy this.
        self.ready = wait_for(self._pid_matches, timeout=20)

    def _pid_matches(self):
        if not os.path.isfile(self.pid_path):
            return False
        with open(self.pid_path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read().strip() == str(self.proc.pid)

    def log_text(self):
        try:
            self.log.flush()
        except Exception:
            pass
        if os.path.isfile(self.log_path):
            with open(self.log_path, "r", encoding="utf-8", errors="replace") as handle:
                return handle.read()
        return ""

    def stop(self):
        if self.proc.poll() is None:
            # inoticoming installs its SIGTERM handler right after writing the
            # pid file, so give the daemon a moment before signalling.
            time.sleep(0.5)
            self.proc.send_signal(signal.SIGTERM)
        try:
            self.proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=5)
        try:
            self.log.close()
        except Exception:
            pass
        return self.proc.returncode


def case_version(binary):
    proc = subprocess.run(
        [binary, "--version"], capture_output=True, text=True, timeout=30
    )
    out = ((proc.stdout or "") + (proc.stderr or "")).strip()
    if proc.returncode == 0 and out == "inoticoming 0.2.3":
        ok("--version -> %r" % out)
    else:
        bad("--version rc=%s out=%r" % (proc.returncode, out[:300]))


def case_help(binary):
    proc = subprocess.run(
        [binary, "--help"], capture_output=True, text=True, timeout=30
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode == 0 and "Syntax:" in out and ";" in out:
        ok("--help documents the action syntax (rc=0)")
    else:
        bad("--help rc=%s out=%r" % (proc.returncode, out[:300]))


def case_close_write(binary, shell, workdir):
    case = fresh_dir(workdir, "close-write")
    watch = fresh_dir(case, "incoming")
    marker = os.path.join(case, "marker")
    daemon = Daemon(binary, shell, case, watch, marker)
    try:
        if not daemon.ready:
            bad("IN_CLOSE_WRITE: daemon never became ready (%s)"
                % daemon.log_text()[-300:])
            return
        with open(os.path.join(watch, "alpha.txt"), "w", encoding="utf-8") as handle:
            handle.write("payload\n")
        if wait_for(lambda: "alpha.txt" in read_lines(marker)):
            ok("IN_CLOSE_WRITE dispatched action for alpha.txt")
        else:
            bad("IN_CLOSE_WRITE not dispatched (marker=%r log=%r)"
                % (read_lines(marker), daemon.log_text()[-300:]))
    finally:
        daemon.stop()


def case_moved_to(binary, shell, workdir):
    case = fresh_dir(workdir, "moved-to")
    watch = fresh_dir(case, "incoming")
    marker = os.path.join(case, "marker")
    daemon = Daemon(binary, shell, case, watch, marker)
    try:
        if not daemon.ready:
            bad("IN_MOVED_TO: daemon never became ready (%s)"
                % daemon.log_text()[-300:])
            return
        staging = os.path.join(case, "beta.txt.part")
        with open(staging, "w", encoding="utf-8") as handle:
            handle.write("payload\n")
        os.rename(staging, os.path.join(watch, "beta.txt"))
        if wait_for(lambda: "beta.txt" in read_lines(marker)):
            ok("IN_MOVED_TO dispatched action for beta.txt")
        else:
            bad("IN_MOVED_TO not dispatched (marker=%r log=%r)"
                % (read_lines(marker), daemon.log_text()[-300:]))
    finally:
        daemon.stop()


def case_suffix_filter(binary, shell, workdir):
    case = fresh_dir(workdir, "suffix-filter")
    watch = fresh_dir(case, "incoming")
    marker = os.path.join(case, "marker")
    daemon = Daemon(binary, shell, case, watch, marker,
                    extra_action_args=["--suffix", ".txt"])
    try:
        if not daemon.ready:
            bad("--suffix: daemon never became ready (%s)"
                % daemon.log_text()[-300:])
            return
        with open(os.path.join(watch, "gamma.bin"), "w", encoding="utf-8") as handle:
            handle.write("payload\n")
        if wait_for(lambda: "gamma.bin" in read_lines(marker), timeout=3.0):
            bad("--suffix .txt wrongly dispatched gamma.bin")
        else:
            with open(os.path.join(watch, "gamma.txt"), "w",
                      encoding="utf-8") as handle:
                handle.write("payload\n")
            if wait_for(lambda: "gamma.txt" in read_lines(marker)):
                ok("--suffix .txt ignored gamma.bin and dispatched gamma.txt")
            else:
                bad("--suffix .txt did not dispatch gamma.txt (marker=%r)"
                    % read_lines(marker))
    finally:
        daemon.stop()


def case_sigterm(binary, shell, workdir):
    case = fresh_dir(workdir, "sigterm")
    watch = fresh_dir(case, "incoming")
    marker = os.path.join(case, "marker")
    daemon = Daemon(binary, shell, case, watch, marker)
    if not daemon.ready:
        bad("SIGTERM: daemon never became ready (%s)" % daemon.log_text()[-300:])
        daemon.stop()
        return
    rc = daemon.stop()
    if rc == 0:
        ok("SIGTERM terminated the daemon with exit code 0")
    else:
        bad("SIGTERM exit code was %s (expected 0)" % rc)


def main():
    if len(sys.argv) != 3:
        print("usage: test_inoticoming.py <inoticoming-binary> <workdir>")
        return 2
    binary = sys.argv[1]
    workdir = sys.argv[2]
    if not os.path.isfile(binary):
        print("FAIL: inoticoming binary not found: %s" % binary)
        return 1
    shell = find_shell()
    if shell is None:
        print("FAIL: no POSIX shell found for the test action")
        return 1
    os.makedirs(workdir, exist_ok=True)
    print("[test] binary: %s" % binary)
    print("[test] shell : %s" % shell)
    print("[test] tmpdir: %s" % workdir)

    case_version(binary)
    case_help(binary)
    case_close_write(binary, shell, workdir)
    case_moved_to(binary, shell, workdir)
    case_suffix_filter(binary, shell, workdir)
    case_sigterm(binary, shell, workdir)

    print("RESULT: %d passed, %d failed" % (PASS, FAIL))
    if FAIL:
        print("test_inoticoming.py FAILED")
        return 1
    print("test_inoticoming.py PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
