#!/usr/bin/env python3
"""Smoke-test mconf and nconf through a real terminal (PTY)."""

import os
import sys
import time

if os.name == "posix":
    import errno
    import fcntl
    import pty
    import select
    import struct
    import subprocess
    import termios


def run_frontend(binary, kconfig):
    name = os.path.basename(binary)
    if name == "kconfig-mconf":
        # mconf starts with the Select button active; Tab moves focus to Exit.
        exit_key, confirm_key = b"\t\n", b"y\n"
    elif name == "kconfig-nconf":
        # xterm-256color encodes F9 as CSI 20~, which nconf binds to Exit.
        exit_key, confirm_key = b"\x1b[20~", b"\n"
    else:
        raise AssertionError(f"unexpected text frontend: {name}")

    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
    environment = os.environ.copy()
    environment["TERM"] = "xterm-256color"
    if not environment.get("TERMINFO"):
        for terminfo_dir in ("/usr/share/terminfo", "/system/usr/share/terminfo"):
            if os.path.isfile(os.path.join(terminfo_dir, "x", "xterm-256color")):
                environment["TERMINFO"] = terminfo_dir
                break
    process = subprocess.Popen(
        [binary, kconfig],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        env=environment,
        start_new_session=True,
    )
    os.close(slave)
    output = bytearray()
    started = time.monotonic()
    deadline = started + 10
    sent_exit = False
    sent_confirmation = False

    try:
        while time.monotonic() < deadline:
            ready, _, _ = select.select([master], [], [], 0.1)
            if ready:
                try:
                    output.extend(os.read(master, 4096))
                except OSError as error:
                    if error.errno != errno.EIO:
                        raise
                    break
            elapsed = time.monotonic() - started
            if not sent_exit and elapsed > 0.5:
                os.write(master, exit_key)
                sent_exit = True
            elif sent_exit and not sent_confirmation and elapsed > 0.8:
                # If the frontend has pending changes, accept its save prompt;
                # if it has no changes, it may already have exited.
                try:
                    os.write(master, confirm_key)
                except OSError as error:
                    if error.errno != errno.EIO:
                        raise
                sent_confirmation = True
            if process.poll() is not None:
                break

        if process.poll() is None:
            if not sent_exit:
                os.write(master, exit_key)
            if not sent_confirmation:
                os.write(master, confirm_key)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                raise AssertionError(
                    f"{os.path.basename(binary)} did not exit from its menu; "
                    f"terminal output: {output[-1200:]!r}"
                )
        else:
            process.wait()

        if process.returncode != 0:
            raise AssertionError(
                f"{os.path.basename(binary)} exited with {process.returncode}; "
                f"terminal output: {output[-1200:]!r}"
            )
        if not output:
            raise AssertionError(f"{os.path.basename(binary)} did not initialize a text UI")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        os.close(master)


def main():
    if len(sys.argv) != 4:
        raise SystemExit("usage: test_text_frontends.py <mconf> <nconf> <Kconfig>")
    if os.name != "posix":
        print("PTY frontend checks require a POSIX HarmonyOS/Linux runtime; skipped on Windows")
        return
    for binary in sys.argv[1:3]:
        run_frontend(binary, sys.argv[3])
        print(f"PASS: {os.path.basename(binary)} opened and exited cleanly")


if __name__ == "__main__":
    main()
