#!/usr/bin/env python3
"""Consumer tests for the packaged splitvt executable (OHOS aarch64).

splitvt allocates two pseudo terminals, fork+execs a program on each and
renders a split VT100 screen on its own terminal, so these tests run the
*installed* binary under a real pty and assert on the bytes that come back
through the outer master -- exactly what a user's terminal would see.  Nothing
here inspects files; see ptyharness.py for why no wait can hang.

Scenarios (one check() == one assertion):
  S1  `splitvt -v`             version self-report matches the package version
  S2  `splitvt -h`             usage text and its exit status
  S3  TERM=vt100, two windows  both child programs reach the screen, the
                               scrolling regions are torn down and splitvt
                               exits 0 on its own
  S4  TERM=vt100, live shell   the child owns its pty (interactive prompt) and
                               a line typed into the upper window is executed
  S5  TERM=xterm, two windows  the xterm branch renders, including the title
  S6  TERM=dumb                refused with the documented message, exit 3

Summary line: RESULT: passed=N failed=M skipped=K
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ptyharness import (SETUP_DONE, PtySession, arm_budget, check,  # noqa: E402
                        child_env, disarm_budget, summary, tail)


def main():
    if len(sys.argv) < 2:
        print("usage: test_splitvt_pty.py <path-to-packaged-splitvt>")
        return 2
    binary = os.path.abspath(sys.argv[1])
    print("== splitvt consumer tests, binary=%s ==" % binary)
    arm_budget(420)

    # ---- S1: version self-report ----------------------------------------
    proc = subprocess.run([binary, "-v"], stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, timeout=60)
    out = proc.stdout
    check(proc.returncode == 0, "S1 exit code of -v is 0",
          "rc=%d out=%s" % (proc.returncode, tail(out)))
    check(b"Splitvt 1.6.6" in out, "S1 version banner states 1.6.6",
          "out=%s" % tail(out))

    # ---- S2: usage text -------------------------------------------------
    proc = subprocess.run([binary, "-h"], stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, timeout=60)
    out = proc.stdout
    check(b"Usage:" in out, "S2 usage header present", "out=%s" % tail(out))
    check(b"-upper command" in out, "S2 documents -upper", "out=%s" % tail(out))
    check(proc.returncode == 1, "S2 usage exit code is 1", "rc=%d" % proc.returncode)

    # ---- S3: both windows really run their programs ---------------------
    ses = PtySession([binary, "-norc",
                      "-upper", "/bin/echo SPLITVT-UP-MARK",
                      "-lower", "/bin/echo SPLITVT-LOW-MARK"],
                     child_env("vt100"))
    try:
        stream = ses.read_until([SETUP_DONE, b"SPLITVT-UP-MARK",
                                 b"SPLITVT-LOW-MARK"], timeout=40)
        check(b"SPLITVT-UP-MARK" in stream,
              "S3 upper window program output reached the terminal",
              "stream=%s" % tail(stream))
        check(b"SPLITVT-LOW-MARK" in stream,
              "S3 lower window program output reached the terminal",
              "stream=%s" % tail(stream))
        check(b"pseudo terminals" not in stream,
              "S3 did not report pseudo-terminal exhaustion",
              "stream=%s" % tail(stream))
        rc = ses.wait(timeout=30)
        check(rc == 0, "S3 splitvt exits 0 by itself once both windows end",
              "rc=%r" % rc)
        check(b"\x1b[r" in ses.stream(),
              "S3 scrolling regions reset on exit (screen torn down)",
              "stream=%s" % tail(ses.stream()))
    finally:
        ses.close()

    # ---- S4: keystrokes are relayed *and executed* ----------------------
    ses = PtySession([binary, "-norc", "-upper", "/bin/sh",
                      "-lower", "/bin/echo SPLITVT-LOW2-MARK"],
                     child_env("vt100"))
    try:
        ses.read_until([SETUP_DONE], timeout=40)
        # A prompt only appears when the child owns its pty, i.e. when
        # dropctty() gave it a real controlling terminal.
        prompt = ses.read_until([b"$ "], timeout=25)
        check(b"$ " in prompt, "S4 upper window shell became interactive",
              "stream=%s" % tail(prompt, 400))
        # Ask for a word the echoed input line cannot contain literally (the
        # terminal echoes "X$n", the shell prints "XOLY"), so a match can only
        # come from the child having executed the command.
        ses.send(b"n=OLY; echo X$n\r")
        stream = ses.read_until([b"XOLY"], timeout=25)
        check(b"XOLY" in stream,
              "S4 command typed into the upper window was executed",
              "stream=%s" % tail(stream, 500))
        ses.send(b"exit\r")
        ses.wait(timeout=25)
    finally:
        ses.close()

    # ---- S5: TERM=xterm takes the xterm branch --------------------------
    ses = PtySession([binary, "-norc",
                      "-upper", "/bin/echo SPLITVT-XUP-MARK",
                      "-lower", "/bin/echo SPLITVT-XLOW-MARK"],
                     child_env("xterm"))
    try:
        stream = ses.read_until([SETUP_DONE, b"SPLITVT-XUP-MARK",
                                 b"SPLITVT-XLOW-MARK"], timeout=40)
        check(b"SPLITVT-XUP-MARK" in stream and b"SPLITVT-XLOW-MARK" in stream,
              "S5 both windows render under TERM=xterm",
              "stream=%s" % tail(stream, 400))
        check(b"0;Splitvt" in stream,
              "S5 xterm title escape emitted (X_SUPPORT path live)",
              "stream=%s" % tail(stream, 400))
        rc = ses.wait(timeout=30)
        check(rc == 0, "S5 exit code 0", "rc=%r" % rc)
    finally:
        ses.close()

    # ---- S6: unsupported terminal type is refused -----------------------
    ses = PtySession([binary, "-norc",
                      "-upper", "/bin/echo SHOULD-NOT-RUN",
                      "-lower", "/bin/echo SHOULD-NOT-RUN"],
                     child_env("dumb"))
    try:
        stream = ses.read_until([b"Terminal type must be set to vt100"],
                                timeout=40)
        check(b"Terminal type must be set to vt100" in stream,
              "S6 refuses a non-vt100 terminal with the documented message",
              "stream=%s" % tail(stream))
        rc = ses.wait(timeout=30)
        check(rc == 3, "S6 exit code 3 (screen initialisation failure)",
              "rc=%r" % rc)
        check(b"SHOULD-NOT-RUN" not in stream,
              "S6 started no child windows before refusing",
              "stream=%s" % tail(stream))
    finally:
        ses.close()

    disarm_budget()
    return summary()


if __name__ == "__main__":
    try:
        exit_code = main()
    except Exception as exc:                # fail closed, never silently pass
        check(False, "consumer suite aborted", repr(exc))
        exit_code = summary()
    sys.exit(exit_code)
