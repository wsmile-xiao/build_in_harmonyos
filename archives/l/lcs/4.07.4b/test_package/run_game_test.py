#!/usr/bin/env python3
"""Real run test for the packaged lcs (crimesquad) binary.

Drives the installed game through a PTY, exactly as a player would:

  1. spawn crimesquad on an 80x25 pty (TIOCSWINSZ; without a sane
     window size initscr renders an incomplete screen),
  2. wait for the title screen text ("Liberal Crime Squad" /
     "Press ESC now to quit") — reaching the title screen at all
     proves the seven gameplay XML files and sitemaps.txt were loaded
     from the installed share/lcs/art/ directory (any XML failure
     aborts with a nonzero exit before the title, and a missing
     sitemaps.txt would print "Failed to load sitemaps.txt!"),
  3. press ESC — the upstream quit path: mode_title() sees 27 and
     calls end_game() -> endwin(); exit(0),
  4. reap the real exit status with waitpid (os.read raising EIO
     after the child exits is normal PTY behaviour, NOT an error).

Timeout / kill means FAILURE — a clean run must exit by itself.

Env: TERM=xterm, TERMINFO pointing into the Conan ncurses package
(terminfo hex layout, xterm lives under 78/), LD_LIBRARY_PATH
covering libc++_shared.so from the OHOS toolchain.
"""

import fcntl
import os
import pty
import re
import select
import struct
import sys
import termios
import time

BIN = sys.argv[1]           # path to installed crimesquad
TERMINFO = sys.argv[2]      # ncurses package share/terminfo
LIBCXX_DIR = sys.argv[3]    # dir containing libc++_shared.so
TIMEOUT = float(sys.argv[4]) if len(sys.argv) > 4 else 60.0


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


pid, fd = pty.fork()
if pid == 0:
    # child: run the installed game from a throwaway HOME so any
    # save/init files are written to the sandbox, not the real HOME
    os.environ["TERM"] = "xterm"
    os.environ["TERMINFO"] = TERMINFO
    os.environ["LD_LIBRARY_PATH"] = LIBCXX_DIR
    os.environ["HOME"] = os.environ.get("TEST_HOME", os.getcwd())
    os.execv(BIN, [BIN])

# 80x25 window: the game's title screen is laid out for this size
fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 25, 80, 0, 0))

buf = b""
sent_esc = False
saw_title = False
saw_quit_hint = False
saw_sitemap_fail = False
deadline = time.time() + TIMEOUT

while time.time() < deadline:
    r, _, _ = select.select([fd], [], [], 0.3)
    if r:
        try:
            data = os.read(fd, 4096)
            if data:
                buf += data
        except OSError:
            pass  # EIO once the child side closed — fine
    if not sent_esc and (b"Press ESC now to quit" in buf
                         or b"Liberal Crime Squad" in buf):
        # title screen is up: XML data + sitemaps loaded fine
        time.sleep(1.0)
        os.write(fd, b"\x1b")  # ESC -> end_game() -> exit(0)
        sent_esc = True
    wpid, status = os.waitpid(pid, os.WNOHANG)
    if wpid == pid:
        rc = os.waitstatus_to_exitcode(status)
        break
    time.sleep(0.05)
else:
    # deadline hit while the child still ran — kill and FAIL
    os.kill(pid, 9)
    os.waitpid(pid, 0)
    fail(f"timeout after {TIMEOUT}s (sent_esc={sent_esc})")
    sys.exit(1)

if wpid != pid:
    os.kill(pid, 9)
    os.waitpid(pid, 0)
    fail("game did not exit")

text = buf.decode("utf-8", "replace")
text = re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]|\x1b[()][A-Z0-9]|\x1b[=>]", "", text)
saw_title = "Liberal Crime Squad" in text
saw_quit_hint = "Press ESC now to quit" in text
saw_sitemap_fail = "Failed to load sitemaps.txt" in text

print(f"exit code        : {rc}")
print(f"title screen     : {saw_title}")
print(f"quit hint shown  : {saw_quit_hint}")
print(f"sitemaps failure : {saw_sitemap_fail}")
print(f"output length    : {len(buf)} bytes")

if rc != 0:
    fail(f"crimesquad exited with {rc}, expected 0")
if not saw_title:
    fail("title screen text never rendered — game did not reach mode_title()")
if not sent_esc:
    fail("ESC was never sent — title screen text not detected")
if saw_sitemap_fail:
    fail("sitemaps.txt failed to load from the installed data dir")

print("PASS: crimesquad ran from the installed package, loaded its data, "
      "and exited cleanly via ESC")
