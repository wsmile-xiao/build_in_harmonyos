#!/usr/bin/env python3
"""Shared pseudo-terminal harness for the splitvt test suites.

splitvt allocates two pseudo terminals and runs a program on each, so the only
way to test it is to give it a pseudo terminal of its own and read what it
renders.  This module owns that plumbing; both suites are deliberately
fail-closed: a checkpoint that cannot be evaluated is a failure, never a skip.

Blocking is designed out, not hoped away:
  * the master is drained with select() under an explicit deadline;
  * EIO on the master (all slaves closed) is recorded as `eof` and the reader
    stops touching it -- but process reaping keeps going, because the child is
    usually already gone by the time EIO shows up;
  * waitpid() is always WNOHANG, and the session is SIGKILLed + reaped in
    close(), so no path here can hang the build.
"""

import errno
import fcntl
import os
import pty
import select
import signal
import struct
import sys
import termios
import time

TIOCSCTTY = 0x540E            # Linux / OHOS asm-generic ioctls
SETUP_DONE = b"\x1b[13;23r"   # splitvt installing the lower window region

PASSED = 0
FAILED = 0
SKIPPED = 0
FAILURES = []


class BudgetExceeded(RuntimeError):
    pass


def arm_budget(seconds):
    def _hit(*_):
        raise BudgetExceeded("global test budget exceeded")
    signal.signal(signal.SIGALRM, _hit)
    signal.alarm(seconds)


def disarm_budget():
    signal.alarm(0)


def check(cond, label, detail=""):
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print("PASS  %s" % label)
    else:
        FAILED += 1
        FAILURES.append(label)
        print("FAIL  %s :: %s" % (label, detail))


def skip(label, why):
    global SKIPPED
    SKIPPED += 1
    print("SKIP  %s :: %s" % (label, why))


def tail(data, n=300):
    return repr(bytes(data)[-n:])


def summary():
    """Machine-readable roll-up; also the source of the reported counts."""
    print("RESULT: passed=%d failed=%d skipped=%d" % (PASSED, FAILED, SKIPPED))
    if FAILURES:
        print("FAILED CHECKS: " + "; ".join(FAILURES))
    return 1 if (FAILED or PASSED == 0) else 0


def child_env(term, drop=()):
    """Minimal environment: no inherited SHELL unless explicitly kept."""
    env = {
        "PATH": "/bin:/usr/bin:/data/service/hnp/bin",
        "TERM": term,
        "HOME": os.environ.get("HOME", "/tmp"),
        "LANG": "C",
    }
    for key in ("SHELL", "USER", "LOGNAME"):
        if key in os.environ and key not in drop:
            env[key] = os.environ[key]
    return env


class PtySession(object):
    """Run a program as session leader of a fresh pseudo terminal."""

    def __init__(self, argv, env, rows=24, cols=80):
        self.out = bytearray()
        self.rc = None
        self.eof = False
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ,
                    struct.pack("HHHH", rows, cols, 0, 0))
        self.pid = os.fork()
        if self.pid == 0:
            try:
                os.setsid()
                try:
                    fcntl.ioctl(slave, TIOCSCTTY, 0)
                except OSError:
                    pass
                for fd in (0, 1, 2):
                    os.dup2(slave, fd)
                for fd in (master, slave):
                    if fd > 2:
                        os.close(fd)
                os.execve(argv[0], [str(arg) for arg in argv], env)
            except BaseException as exc:                        # pragma: no cover
                sys.stderr.write("exec failed: %r\n" % (exc,))
                os._exit(127)
        os.close(slave)
        self.master = master

    # -- internal ---------------------------------------------------------
    def _drain(self, slice_s):
        if self.eof:
            return False
        ready, _, _ = select.select([self.master], [], [], slice_s)
        if not ready:
            return False
        try:
            chunk = os.read(self.master, 65536)
        except OSError as exc:
            if exc.errno in (errno.EIO, errno.EBADF):
                self.eof = True      # every slave closed == programs ended
                return False
            raise
        if not chunk:
            self.eof = True
            return False
        self.out += chunk
        return True

    def _poll(self):
        if self.pid is None or self.rc is not None:
            return
        try:
            done, status = os.waitpid(self.pid, os.WNOHANG)
        except OSError:
            self.rc = -1
            return
        if not done:
            return
        if os.WIFEXITED(status):
            self.rc = os.WEXITSTATUS(status)
        elif os.WIFSIGNALED(status):
            self.rc = -os.WTERMSIG(status)
        else:
            self.rc = -1

    # -- api --------------------------------------------------------------
    def read_until(self, needles, timeout=20.0):
        """Accumulate output until every needle shows up, or it cannot."""
        if isinstance(needles, (bytes, bytearray)):
            needles = [needles]
        deadline = time.time() + timeout
        while time.time() < deadline:
            self._drain(0.2)
            self._poll()
            if all(needle in self.out for needle in needles):
                break
            if self.eof and self.rc is not None:
                break
        return bytes(self.out)

    def send(self, data):
        os.write(self.master, data)

    def wait(self, timeout=10.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            self._drain(0.1)
            self._poll()
            if self.rc is not None:
                break
        return self.rc

    def alive(self):
        self._poll()
        return self.rc is None

    def stream(self):
        return bytes(self.out)

    def close(self):
        if self.pid is not None and self.rc is None:
            try:
                os.kill(self.pid, signal.SIGKILL)
            except OSError:
                pass
            for _ in range(50):
                self._poll()
                if self.rc is not None:
                    break
                time.sleep(0.1)
        try:
            os.close(self.master)
        except OSError:
            pass


def session_result(argv, env, seconds, ready=None):
    """Run a session for a bounded time; return (stream, still_running)."""
    ses = PtySession(argv, env)
    try:
        if ready:
            ses.read_until([ready], timeout=seconds)
            return ses.stream(), ses.alive()
        ses.read_until([b"\xff\xff-unreachable\xff"], timeout=seconds)
        return ses.stream(), ses.alive()
    finally:
        ses.close()
