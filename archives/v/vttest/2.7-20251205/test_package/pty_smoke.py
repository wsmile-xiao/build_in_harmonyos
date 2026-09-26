#!/usr/bin/env python3
"""PTY smoke test for the packaged vttest binary.

vttest only does its job when stdin/stdout are a terminal: it opens /dev/tty,
switches tty modes and then drives the terminal with escape sequences.  A
pipe-based check can therefore only cover ``-V`` and the usage text; this
helper starts the packaged binary on a real pseudo-terminal, waits for the
main menu, selects the "Exit" item and asserts that vttest announced its
version, drew the menu and terminated with status 0.

Usage: pty_smoke.py <path-to-vttest>

Exit codes:
  0   all PTY assertions passed
  1   assertion failed (the binary misbehaved)
  2   bad invocation
  77  no pseudo-terminal available on this host (explicit skip)
"""

import errno
import os
import pty
import select
import sys
import time

BANNER = b"VT100 test program, version 2.7 (20251205)"
MENU = b"Choose test type:"


def _exit_code(status):
    if hasattr(os, "waitstatus_to_exitcode"):
        return os.waitstatus_to_exitcode(status)
    if os.WIFSIGNALED(status):
        return -os.WTERMSIG(status)
    return os.WEXITSTATUS(status)


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("usage: pty_smoke.py <path-to-vttest>\n")
        return 2
    binary = sys.argv[1]
    timeout = float(os.environ.get("VTTEST_PTY_TIMEOUT", "20"))

    try:
        pid, fd = pty.fork()
    except OSError as exc:
        sys.stderr.write("SKIP: pseudo-terminal unavailable on this host: %s\n"
                         % exc)
        return 77

    if pid == 0:
        os.environ["TERM"] = "xterm"
        try:
            os.execv(binary, [binary, "24x80.132"])
        except OSError:
            os._exit(127)

    output = bytearray()
    status = None
    started = time.time()
    deadline = started + timeout
    sent_exit = False
    menu_seen_at = None

    try:
        while time.time() < deadline:
            if not sent_exit:
                if menu_seen_at is not None:
                    if time.time() - menu_seen_at > 0.3:
                        os.write(fd, b"0\n")
                        sent_exit = True
                elif time.time() - started > 5.0:
                    os.write(fd, b"0\n")
                    sent_exit = True
            readable, _, _ = select.select([fd], [], [], 0.25)
            if readable:
                try:
                    chunk = os.read(fd, 65536)
                except OSError as exc:
                    if exc.errno == errno.EIO:
                        break
                    raise
                if not chunk:
                    break
                output.extend(chunk)
                if menu_seen_at is None and MENU in output:
                    menu_seen_at = time.time()
            wpid, wstatus = os.waitpid(pid, os.WNOHANG)
            if wpid == pid:
                status = wstatus
                break
    finally:
        if status is None:
            os.kill(pid, 9)
            _, status = os.waitpid(pid, 0)

    code = _exit_code(status)

    if BANNER not in output:
        sys.stderr.write("FAIL: version banner missing from PTY output "
                         "(%d bytes captured)\n" % len(output))
        return 1
    if MENU not in output:
        sys.stderr.write("FAIL: main menu missing from PTY output\n")
        return 1
    if not sent_exit:
        sys.stderr.write("FAIL: main menu never became ready for input\n")
        return 1
    if code != 0:
        sys.stderr.write("FAIL: vttest did not exit cleanly after selecting "
                         "the Exit menu item (status=%s)\n" % code)
        return 1

    sys.stdout.write("PTY smoke test passed: banner + main menu + clean "
                     "exit (status 0, %d bytes)\n" % len(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
