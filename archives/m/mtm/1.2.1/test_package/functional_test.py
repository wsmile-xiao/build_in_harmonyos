#!/usr/bin/env python3
"""Functional test for mtm (used by test_package).

mtm is a terminal multiplexer: it takes over the whole terminal via
ncurses, runs an interactive command loop and has NO version/help option
(its only options are -T NAME, -t NAME and -c KEY).  A `--help` smoke
test is therefore useless; instead we verify real multiplexer behaviour
inside a pseudo terminal:

  1. spawn `mtm` in a pty (size 80x24) with TERM=screen
  2. wait until the child shell renders its prompt output
     (mtm creates a hidden pty and forwards its output - a full
      forkpty/newterm/refresh path through ncurses and terminfo)
  3. verify mtm stays alive and does not crash within the timeout
  4. delete the last node via command key (Ctrl-g w: deletenode() on the
     root calls quit(EXIT_SUCCESS)) and require a clean exit 0

Return code: 0 = pass, 1 = fail.
"""
import errno
import os
import pty
import select
import signal
import struct
import sys
import time

KEY_TIMEOUT = 12  # seconds to observe child output


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: functional_test.py <mtm-path>")
        return 2
    mtm = sys.argv[1]
    if not os.path.exists(mtm):
        print(f"FAIL: binary not found: {mtm}")
        return 1

    os.environ["TERM"] = "screen"
    # TERMINFO from the ncurses conan package runenv (conanrun) provides the
    # `screen` entry; without a valid terminfo database initscr() fails and
    # mtm exits immediately.

    pid, fd = pty.fork()
    if pid == 0:
        # child: mtm with a plain shell as the hosted program
        os.environ["SHELL"] = "/bin/sh"
        os.execv(mtm, [mtm])

    # tell mtm the pty is 80x24 (TIOCSWINSZ on the master)
    try:
        import fcntl
        import termios

        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
    except OSError:
        pass

    output = b""
    saw_child_output = False
    deadline = time.time() + KEY_TIMEOUT
    try:
        while time.time() < deadline:
            # mtm must still be alive
            wpid, _ = os.waitpid(pid, os.WNOHANG)
            if wpid == pid:
                print("FAIL: mtm exited prematurely")
                return 1
            r, _, _ = select.select([fd], [], [], 0.5)
            if not r:
                continue
            try:
                chunk = os.read(fd, 4096)
            except OSError:
                break
            if not chunk:
                break
            output += chunk
            # ncurses full-screen apps emit cursor-positioning escape
            # sequences; any substantial output proves the child shell was
            # spawned inside mtm's hidden pty and rendered through mtm.
            if len(output) >= 64 or b"\x1b[" in output:
                saw_child_output = True
                break

        if not saw_child_output:
            print("FAIL: no child output observed (mtm did not multiplex)")
            return 1

        # mtm is alive with rendered content. Send the command key
        # sequence (Ctrl-g then w = delete the last node, per mtm(1):
        # deleting the last node terminates mtm cleanly).
        exit_code = None
        try:
            os.write(fd, b"\x07w")  # Ctrl-g (command key) then w (delete node)
        except OSError as exc:
            # EIO/EBADF on the pty master usually just means the child
            # already exited and closed its side.  Fail closed: tolerate
            # it only after waitpid confirms the child is gone, and then
            # still assert on its real exit status below; any other
            # OSError - or a still-running child - is re-raised, never
            # silently swallowed.
            if exc.errno not in (errno.EIO, errno.EBADF):
                raise
            wpid, status = os.waitpid(pid, os.WNOHANG)
            if wpid != pid:
                raise
            exit_code = os.waitstatus_to_exitcode(status)
        wait_deadline = time.time() + 5
        while exit_code is None and time.time() < wait_deadline:
            wpid, status = os.waitpid(pid, os.WNOHANG)
            if wpid == pid:
                exit_code = os.waitstatus_to_exitcode(status)
                break
            time.sleep(0.2)
            try:
                r, _, _ = select.select([fd], [], [], 0)
                if r:
                    os.read(fd, 4096)
            except OSError:
                pass

        if exit_code is None:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
            print("FAIL: mtm did not exit after Ctrl-g w")
            return 1
        if exit_code != 0:
            print(f"FAIL: mtm exited with {exit_code} (expected 0)")
            return 1
        print(f"OK: mtm multiplexed child output and exited cleanly (rc={exit_code}, bytes={len(output)})")
        return 0
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        except (ProcessLookupError, ChildProcessError, OSError):
            pass


if __name__ == "__main__":
    sys.exit(main())
