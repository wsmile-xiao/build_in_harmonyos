#!/usr/bin/env python3
"""Functional test for the npush terminal game (used by test_package).

Spawns the packaged `npush` launcher inside a pseudo terminal, waits for the
main menu to be drawn and then drives the keyboard to select the "Quit"
entry (Down Down Enter).  The game must exit with status 0.

Return code: 0 = pass, 1 = fail.
"""
import os
import pty
import select
import signal
import sys
import time


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: functional_test.py <npush-launcher-path>")
        return 2
    launcher = sys.argv[1]
    if not os.path.exists(launcher):
        print(f"FAIL: launcher not found: {launcher}")
        return 1

    # A terminal emulation + a terminfo entry.  The ncurses conan package's
    # runenv (TERMINFO -> its share/terminfo) is injected through the
    # "conanrun" env when this script is launched by test_package; without a
    # valid TERM/TERMINFO the game cannot start (initscr would fail).
    os.environ["TERM"] = os.environ.get("TERM", "") or "xterm-256color"
    if not os.environ.get("TERMINFO"):
        print("WARN: TERMINFO not set - ncurses may fail to find xterm-256color entry")
    # run from the package share dir so a stray "start game" cannot fail on
    # missing level data (levels/ lives next to the real binary).

    pid, fd = pty.fork()
    if pid == 0:
        # child: let the launcher cd into share/npush itself; keep cwd sane
        os.chdir(os.path.dirname(launcher) + "/../share/npush")
        os.execv(launcher, [launcher])

    seen_menu = False
    output = b""
    deadline = time.time() + 8
    try:
        while time.time() < deadline:
            r, _, _ = select.select([fd], [], [], 0.4)
            if r:
                try:
                    chunk = os.read(fd, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                output += chunk
                if b"Welcome to nPush" in output:
                    seen_menu = True
                    break

        time.sleep(0.6)
        # application cursor key sequences for this ncurses terminfo:
        #   kcud1 = ESC O B  (down),  kent / \\n = activate
        os.write(fd, b"\x1bOB")
        time.sleep(0.3)
        os.write(fd, b"\x1bOB")
        time.sleep(0.3)
        os.write(fd, b"\n")

        # Wait for a clean exit.
        exit_code = None
        wait_deadline = time.time() + 8
        while time.time() < wait_deadline:
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
            print(f"FAIL: npush did not exit after Quit (menu seen: {seen_menu})")
            return 1
        if not seen_menu:
            print("FAIL: npush menu was never rendered")
            return 1
        if exit_code != 0:
            print(f"FAIL: npush exited with {exit_code} (expected 0 after Quit)")
            return 1
        print(f"OK: npush menu rendered and Quit exited cleanly (seen={seen_menu}, rc={exit_code})")
        return 0
    finally:
        try:
            os.close(fd)
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())
