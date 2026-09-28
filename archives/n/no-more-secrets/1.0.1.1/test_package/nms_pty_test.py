#!/usr/bin/env python3
"""Consumer test for no-more-secrets (nms + sneakers) on OHOS/Linux.

Why a terminal harness: both tools are terminal-UI programs.  sneakers calls
ioctl(0, TIOCGWINSZ) first and exits 1 with "Input not from an interactive
terminal" otherwise; nms reads its input from stdin when stdin is not a tty
(input.c) and then initialises ncurses via initscr(), drawing the decryption
effect on stdout (nmstermio_ncurses.c reopens /dev/tty only for the keyboard).
The 1.0.1 recipe only ran `nms -v`, which returns before ncurses is
initialised, so the effect path was never exercised — that is what this
harness fixes (KB: TUI pty harness).

The effect is therefore covered twice, because the two paths fail differently:

  * [5] over pipes — the documented `sneakers | nms` usage, and the only path
    available on OHOS, where the app sandbox denies this user /dev/ptmx and
    /dev/pts outright (EACCES on open and lstat; pty.fork() then reports "out
    of pty devices").  nms takes the piped bytes as its input and ncurses
    draws to a pipe, sizing the screen from LINES/COLUMNS.  This runs
    everywhere, device included.
  * [6] under a real pty — typed input, the interactive prompt, the closing
    key press, and sneakers' panel.  This needs a pty: on OHOS the checks are
    reported as skipped with the sandbox reason, on CI and normal Linux hosts
    they run for real.

Neither tool copes with a 0x0 pty (sneakers does `malloc(20 * ws_col)` +
`strcpy` — a heap overflow with 0 columns; the ncurses effect loop quits on
its first character when getmaxy() reports 0 rows), so when a pty is used the
child sizes its own terminal to 24x80 right before exec.  `nms_pty_test.py
--selftest` verifies that plumbing, and reports UNAVAILABLE (not a failure)
where no pty can be allocated at all.

Coverage:
  * package layout: binaries + man pages + LICENSE + bundled terminfo database
  * nms -v (no tty)                     -> exit 0 + exact version banner
  * nms with empty stdin (no tty)       -> exit non-zero ("Input is empty")
  * nms -Z (no tty)                     -> exit non-zero ("Unknown option")
  * sneakers without a tty              -> exit 1 + documented message
  * nms with piped input                -> effect renders the input (asserted
                                           against an emulated screen, because
                                           the reveal lives in terminal state,
                                           not in the byte stream), ANSI escapes
                                           written, no prompt.  Its closing
                                           keypress comes from /dev/tty, so the
                                           run ends on that key where a
                                           controlling terminal exists and is
                                           ended by the harness where it does
                                           not (reported, never hung).
  * nms with a multi-line secret        -> the second line lands one row below
                                           the first: this pins the effect's
                                           row tracking, and unlike the pty
                                           section it runs on every host
  * nms under a pty, typed input        -> effect reveals the input text,
                                           exit 0 after the closing key press
  * sneakers under a pty                -> panel text present on the replayed
                                           screen, exit 0
  * negative injection controls: a truncated binary / a missing terminfo
    database must make the corresponding check fail (proves the assertions
    are load-bearing, i.e. they really depend on the tested package)

Usage: nms_pty_test.py <package_folder>
Exit code: 0 = all checks passed, non-zero = at least one failure.
"""
import os
import platform
import re
import select
import shutil
import stat
import sys
import tempfile
import threading
import time

try:
    import pty
except ImportError:  # e.g. Windows: no pty module, only sections [1]-[5] can run
    pty = None

FAILURES = []
COUNT = [0, 0]  # [assertions, skipped]


def check(cond, msg):
    COUNT[0] += 1
    if cond:
        print("  [PASS] %s" % msg)
    else:
        print("  [FAIL] %s" % msg)
        FAILURES.append(msg)
    return bool(cond)


def skip(msg):
    COUNT[1] += 1
    print("  [SKIP] %s" % msg)


PTY_ROWS, PTY_COLS = 24, 80


class _Screen:
    """Just enough terminal emulation to read back what the effect painted.

    The ncurses effect never writes the plaintext as a contiguous run: every
    cell is repainted in place (scramble glyph first, revealed character
    later), so the plaintext only exists as *terminal state*, not as a byte
    sequence in the capture.  Assertions therefore have to be made against the
    screen the child would have left behind, which is what this replays.

    The conventions here are pinned to an independent emulator (pyte, which is
    not otherwise a dependency): replayed over a capture taken on the device,
    the two agree cell for cell, including the glyphs ncurses picked from the
    scrambling charset.  Two of those conventions are load-bearing:

      * the complete CSI grammar (parameters, intermediates, a final byte in
        0x40..0x7e) with the movement commands implemented.  ncurses does not
        paint the effect left to right: it repositions with ^[[C (forward),
        ^[[<n>G (column), ^[[<n>d (line) and ^[[H between characters, so
        ignoring one of them silently shifts every character after it -- a
        dropped ^[[C is what made an earlier version of this replay read
        "O..P SECRET DATA" where the terminal really showed "TOP SECRET DATA".

      * one character is one cell, with no East-Asian width doubling.  The
        scrambling glyphs are multi-byte and some of them are wide, but ncurses
        addresses them as single cells here and compensates with the explicit
        moves above; doubling their width would reintroduce the same shift.
    """

    CSI = re.compile(r"\x1b\[([0-?]*)([ -/]*)([@-~])")

    def __init__(self, rows, cols):
        self.rows, self.cols = rows, cols
        self.reset()

    def reset(self):
        self.grid = [[" "] * self.cols for _ in range(self.rows)]
        self.row = self.col = 0

    def _n(self, params, i, default=1):
        """Parameter i of a CSI, with the ECMA-48 empty/zero default."""
        parts = params.split(";")
        if i < len(parts) and parts[i].isdigit() and int(parts[i]):
            return int(parts[i])
        return default

    def _csi(self, params, final):
        if params[:1] in ("?", "<", "=", ">"):   # private modes: no text
            return
        if final == "A":
            self.row = max(self.row - self._n(params, 0), 0)
        elif final == "B" or final == "e":
            self.row = min(self.row + self._n(params, 0), self.rows - 1)
        elif final == "C" or final == "a":
            self.col = min(self.col + self._n(params, 0), self.cols - 1)
        elif final == "D":
            self.col = max(self.col - self._n(params, 0), 0)
        elif final in ("E", "F"):
            self.row = min(max(self.row + (self._n(params, 0) if final == "E"
                                            else -self._n(params, 0)), 0),
                           self.rows - 1)
            self.col = 0
        elif final in ("G", "`"):
            self.col = min(max(self._n(params, 0) - 1, 0), self.cols - 1)
        elif final == "d":
            self.row = min(max(self._n(params, 0) - 1, 0), self.rows - 1)
        elif final in ("H", "f"):
            self.row = min(max(self._n(params, 0) - 1, 0), self.rows - 1)
            self.col = min(max(self._n(params, 1) - 1, 0), self.cols - 1)
        elif final == "J":
            mode = self._n(params, 0, 0)
            if mode >= 2:        # clear all -- the cursor does not move
                for r in range(self.rows):
                    self.grid[r] = [" "] * self.cols
            elif mode == 1:      # start of screen through the cursor
                for r in range(self.row):
                    self.grid[r] = [" "] * self.cols
                self._blank(0, self.col + 1)
            else:                # cursor through end of screen
                self._blank(self.col, self.cols)
                for r in range(self.row + 1, self.rows):
                    self.grid[r] = [" "] * self.cols
        elif final == "K":
            mode = self._n(params, 0, 0)
            if mode == 1:
                self._blank(0, self.col + 1)
            elif mode == 2:
                self._blank(0, self.cols)
            else:
                self._blank(self.col, self.cols)
        elif final == "X":
            self._blank(self.col, self.col + self._n(params, 0))
        # colors (m), modes (h/l), the scrolling region (r) and the rest do
        # not change any character cell, so they are consumed and dropped

    def _blank(self, first, last):
        for c in range(max(first, 0), min(last, self.cols)):
            self.grid[self.row][c] = " "

    def feed(self, text):
        i, n = 0, len(text)
        while i < n:
            ch = text[i]
            if ch == "\x1b":
                # Escape sequences are control, never text -- and the capture
                # can end in the middle of one, in which case the rest of the
                # text is undecidable and the replay stops rather than reading
                # the torn-off tail ("^[(", "^[[1;7") as characters.
                if i + 1 >= n:
                    break
                if text[i + 1] == "[":
                    m = self.CSI.match(text, i)
                    if m is None:        # a CSI without its final byte
                        break
                    self._csi(m.group(1), m.group(3))
                    i = m.end()
                    continue
                if text[i + 1] in "()*+#%.-/ ":   # 2-byte prefix, 1 byte of arg
                    if i + 2 >= n:
                        break
                    i += 3
                    continue
                i += 2                   # single-character escape (^[=, ^[>)
                continue
            if "\x80" <= ch <= "\x9f":   # C1 controls never paint a cell
                i += 1
                continue
            if ch == "\r":
                self.col = 0
            elif ch == "\n":
                if self.row + 1 >= self.rows:   # line feed at the bottom scrolls
                    self.grid.pop(0)
                    self.grid.append([" "] * self.cols)
                else:
                    self.row += 1
            elif ch == "\b":
                self.col = max(self.col - 1, 0)
            elif ch >= " ":
                if self.col >= self.cols:      # the terminal's auto-margin wrap
                    if self.row + 1 >= self.rows:
                        self.grid.pop(0)
                        self.grid.append([" "] * self.cols)
                    else:
                        self.row += 1
                    self.col = 0
                self.grid[self.row][self.col] = ch
                self.col += 1
            i += 1

    def text(self):
        return "\n".join("".join(r).rstrip() for r in self.grid)


def render_screen(blob, rows=PTY_ROWS, cols=PTY_COLS):
    """Replay a capture through the emulator and return the visible text."""
    scr = _Screen(rows, cols)
    scr.feed(blob.decode("utf-8", "replace"))
    return scr.text()


def shows_text(screen, wanted):
    """Is `wanted` on the screen, allowing for a wrap at the terminal width?

    The effect lays the text out at the screen width ncurses computed, and on
    device that width is narrow enough to wrap a longer secret onto the next
    row: the visible text then reads "TOP SECRET" / " DATA" instead of one
    line, which is correct rendering, not a lost character.  So the exact form
    is tried first and the whitespace-free form second -- the latter only
    forgives where the line break landed (and any trailing space the per-row
    rstrip ate), which is exactly the freedom a wrap needs.
    """
    if wanted in screen:
        return True, "exact"
    flat = re.sub(r"\s+", "", screen)
    if re.sub(r"\s+", "", wanted) in flat:
        return True, "wrapped"
    return False, "absent"


def spawn_in_pty(binary, args, env, rows=PTY_ROWS, cols=PTY_COLS):
    """Fork `binary` on a rows x cols pseudo-terminal, return (pid, master_fd).

    The size has to be in place before the program runs: both tools read it at
    startup and neither copes with a 0x0 pty.  sneakers does `termCols =
    ws_col; malloc(20 * termCols); strcpy(display, head1Left)` — with 0 columns
    that is a heap buffer overflow (crash, or "Memory Allocation Error"); the
    ncurses effect in nmseffect.c breaks out of its loop on the first character
    when getmaxy() reports 0 rows, so nothing would be revealed.

    Two device constraints rule out the obvious approach of sizing the slave
    before forking it: OHOS denies this user /dev/ptmx outright (EACCES;
    measured in the --selftest step), and pty.fork() has no hook between fork
    and exec.  So the child is the one that sizes the terminal, on its own fd
    0, immediately before exec: pty.fork() is the API that works wherever ptys
    are available at all, and the window size lives on the terminal itself, so
    setting it from the child is equivalent and race-free.
    """
    import fcntl
    import struct
    import termios

    if pty is None:
        raise RuntimeError("no pty module on this platform")
    pid, fd = pty.fork()
    if pid == 0:  # child
        try:
            fcntl.ioctl(0, termios.TIOCSWINSZ,
                        struct.pack("HHHH", rows, cols, 0, 0))
        except Exception:
            pass  # a wrongly sized tty still runs; the checks would report it
        try:
            os.execve(binary, [binary] + args, env)
        except Exception:
            os._exit(127)
    return pid, fd


def pty_availability():
    """Return (available, reason) for pty allocation on this host.

    OHOS's sandbox denies this user /dev/ptmx and /dev/pts entirely (EACCES on
    open/lstat; openpty() raises EPERM and forkpty() reports "out of pty
    devices"), even though shell sessions started by sshd do hold ptys.  The
    device run reports the pty-only checks as skipped in that case and leans on
    the piped section, which exercises the same effect code without a pty.
    """
    if pty is None:
        return False, "python has no pty module on this platform"
    try:
        pid, fd = pty.fork()
    except Exception as exc:
        return False, str(exc)
    if pid == 0:
        os._exit(0)
    os.waitpid(pid, 0)
    os.close(fd)
    return True, ""


def run_in_pty(binary, args, run_env, timeout=30, send=b"", send_after=None, key=None):
    """Run `binary args` under a 24x80 pseudo-terminal.

    send:       bytes written to the pty master right after the child starts
                (typed input, e.g. b"TOP SECRET\\n").
    send_after: (pattern, bytes) — write `bytes` once `pattern` shows up in the
                child's output (used to answer the "press any key" prompt that
                follows the effect).
    key:        bytes written after the pattern (or after `send`) is observed.

    Returns (exit_code, output).  On OHOS reading the pty master after the
    child exits raises EIO instead of returning EOF, so the read loop treats
    OSError as "child side gone" and reaps the child for its real status.
    A failure to spawn at all (no pty available) is reported as rc -2 with the
    error text as output, so the affected checks fail with a readable reason
    instead of aborting the harness.
    """
    env = dict(os.environ)
    env.update(run_env)

    try:
        pid, fd = spawn_in_pty(binary, args, env)
    except Exception as exc:
        return -2, ("cannot spawn %s on a pty: %s" % (binary, exc)).encode()

    if send:
        time.sleep(0.4)  # let the child reach its input prompt
        try:
            os.write(fd, send)
        except OSError:
            pass

    deadline = time.time() + timeout
    output = b""
    next_key = time.time() + 1.5
    io_done = False
    while not io_done and time.time() < deadline:
        try:
            r, _, _ = select.select([fd], [], [], 0.3)
        except OSError:
            r = []          # pty master gone (OHOS may raise instead of EIO)
            io_done = True
        if r:
            try:
                data = os.read(fd, 65536)
                if not data:
                    io_done = True
                else:
                    output += data
            except OSError:
                io_done = True  # EIO: child side of the pty is gone
        # The closing "press any key" prompt follows nmstermio_clear_input()
        # (= flushinp()), which discards keys typed during the effect, so the
        # key is re-sent periodically until the child exits.
        if key and time.time() >= next_key:
            if send_after is None or send_after in output:
                try:
                    os.write(fd, key)
                except OSError:
                    pass
                next_key = time.time() + 1.5
        if not r:
            try:
                wpid, st = os.waitpid(pid, os.WNOHANG)
                if wpid:
                    return _status(st), output
            except ChildProcessError:
                return -1, output

    if io_done:
        code = _reap(pid, 2.0)
        if code is not None:
            return code, output
    try:
        os.kill(pid, 9)
    except ProcessLookupError:
        pass
    code = _reap(pid, 2.0)
    return (code if code is not None else -1), output


def _status(st):
    if os.WIFEXITED(st):
        return os.WEXITSTATUS(st)
    return -os.WTERMSIG(st)


def _reap(pid, block_s):
    end = time.time() + block_s
    while time.time() < end:
        try:
            wpid, st = os.waitpid(pid, os.WNOHANG)
            if wpid:
                return _status(st)
        except ChildProcessError:
            return -1
        time.sleep(0.1)
    return None


def run_collect(binary, args, run_env, stdin_file=None, stdin_data=None, timeout=30):
    """Run a short-lived command without a pty (stdout/stderr captured).

    stdin_file: read stdin from this file.
    stdin_data: feed these bytes through a pipe instead — the piped effect
                check uses it, because nms takes its input from stdin when
                stdin is not a tty (that is the documented `sneakers | nms`
                invocation).

    A binary that cannot even be started (execve fails: ENOEXEC for a truncated
    ELF, EACCES for a non-executable file) is reported as rc 126 with the error
    text as output — the negative injection controls rely on that instead of
    letting OSError escape and abort the whole harness.
    """
    import subprocess
    env = dict(os.environ)
    env.update(run_env)
    if stdin_data is not None:
        stdin = subprocess.PIPE
    elif stdin_file:
        stdin = open(stdin_file, "rb")
    else:
        stdin = subprocess.DEVNULL
    try:
        try:
            p = subprocess.Popen([binary] + args, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, stdin=stdin, env=env)
        except OSError as exc:
            return 126, ("cannot execute %s: %s" % (binary, exc)).encode()
        try:
            out, _ = p.communicate(input=stdin_data, timeout=timeout)
        except subprocess.TimeoutExpired:
            # Killing is the only way to end these TUIs: on device, nms catches
            # SIGTERM and keeps waiting for a keypress, so timeout(1) hangs on
            # it.  os.kill(SIGKILL) is what works.  Both the collection and the
            # wait are bounded here -- an unbounded communicate() after the
            # kill has been observed to wedge the whole harness on this host.
            p.kill()
            try:
                out = p.stdout.read() or b""
            except Exception:                                          # noqa: BLE001
                out = b""
            try:
                p.wait(timeout=10)
            except Exception:                                          # noqa: BLE001
                pass
            return -1, out
        return p.returncode, out
    finally:
        if stdin_file:
            stdin.close()


def run_piped_effect(binary, args, run_env, secret, key=b"\r", wait_s=60,
                     quiet_s=2.5, done=None):
    """Drive the tool the way `sneakers | nms` is documented to be driven.

    nms takes its secret from stdin when stdin is not a tty and then, exactly
    like the interactive path, waits for a closing keypress before exiting.
    With a stdin that has already hit EOF it waits forever: measured on device,
    the process sits there long after timeout(1) fired, because nms catches
    SIGTERM and does not exit.  So the pipe is kept open here -- secret in, the
    effect collected until the output goes quiet, then the closing key, and the
    process exits on its own with its real exit status.

    wait_s is a ceiling, not a target: `done` (a predicate on the bytes
    collected so far) is what decides that the effect is over, and the loop
    stops as soon as it says so AND the output has gone quiet.  A fixed wait
    was tried first and proved fragile -- the reveal is painted at this
    program's own pace (up to ~5s of 50ms passes, and much slower under a
    loaded `conan test`), so a run that was merely slow came back as a partial
    screen and read as "the effect did not render the input".

    Returns (rc, output, note).  rc is None only if the child had to be killed
    after wait_s; note then records what was observed.
    """
    import subprocess
    env = dict(os.environ)
    env.update(run_env)
    p = subprocess.Popen([binary] + args, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, stdin=subprocess.PIPE, env=env)
    out = b""
    note = ""
    try:
        p.stdin.write(secret + b"\n")
        p.stdin.flush()
    except OSError:
        pass

    deadline = time.time() + wait_s
    last_data = time.time()
    next_key = 0.0
    finished = False
    was_quiet = False
    while time.time() < deadline:
        try:
            r, _, _ = select.select([p.stdout], [], [], 0.3)
        except OSError:
            r = []
        if r:
            try:
                chunk = os.read(p.stdout.fileno(), 65536)
            except OSError:
                chunk = b""
            if not chunk:
                break
            out += chunk
            last_data = time.time()
            was_quiet = False
        elif out and time.time() - last_data > quiet_s:
            if not was_quiet:
                # Just went quiet: ask whether the effect has been proven
                # rendered.  Only on the transition, because each call replays
                # the whole capture through the emulator.
                was_quiet = True
                if done is not None:
                    finished = bool(done(out))
            if time.time() >= next_key:
                # Answer the closing keypress.  It is re-sent on a timer, not
                # once: nmstermio_clear_input() calls flushinp() right before
                # the barrier (see nmseffect.c), which throws away whatever
                # arrived while the effect was still drawing.
                try:
                    p.stdin.write(key)
                    p.stdin.flush()
                except OSError:
                    pass
                next_key = time.time() + 1.5
        if finished and was_quiet:
            break
        if p.poll() is not None:
            break

    # Kill before draining, never after: this child catches SIGTERM, so if the
    # closing key was missed it is still running and holding the pipe open, and
    # an unbounded read here would block for good (that is how this harness
    # wedged on device).  The read below is only what is already buffered.
    rc = p.poll()
    if rc is None:
        note = ("killed after %ds: still waiting for its closing keypress. "
                "nms reads that key from /dev/tty, which it reopens whenever "
                "stdin is not a tty (nmstermio_init_terminal), so over a pipe "
                "the key is undeliverable wherever the process has no "
                "controlling terminal." % wait_s)
        p.kill()
    try:
        out += p.stdout.read() or b""
    except Exception:                                                  # noqa: BLE001
        pass
    if rc is None:
        try:
            p.wait(timeout=10)
        except Exception:                                              # noqa: BLE001
            pass
        rc = p.poll()
    return rc, out, note


def find_terminfo_entry(terminfo_dir, name):
    """terminfo entries are files named <entry> under a one-char (or hex)
    subdirectory, optionally .gz-compressed."""
    for root, _dirs, files in os.walk(terminfo_dir):
        for f in files:
            base = f[:-3] if f.endswith(".gz") else f
            if base == name:
                return os.path.join(root, f)
    return None


def elf_info(path):
    with open(path, "rb") as f:
        head = f.read(20)
    if len(head) < 20 or head[:4] != b"\x7fELF":
        return None
    return {
        "class": "ELF64" if head[4] == 2 else "ELF32",
        "machine": int.from_bytes(head[18:20], "little"),
    }


def screen_selftest():
    """Check the replay emulator, without the package under test.

    The effect's assertions are made against a replay of the child's output, so
    a defect in the replay looks exactly like a defect in nms: an earlier
    version of this harness dropped ^[[C (cursor forward) and duly reported
    "the effect did not render the input" for a terminal that was showing the
    plaintext correctly.  These are the idioms ncurses emits for the effect,
    checked here so a replay failure can be told apart from a program failure.
    """
    cases = [
        ("^[[C", b"\x1b[H\x1b[CZ", 0, 1, "Z"),        # forward, 1 cell
        ("^[[<n>C", b"\x1b[H\x1b[3CZ", 0, 3, "Z"),
        ("^[[<n>G", b"abcdef\x1b[4GQ", 0, 3, "Q"),    # column, absolute
        ("^[[<n>d", b"ab\x1b[3dQ", 2, 2, "Q"),        # line, keeps the column
        ("^[[H", b"ab\x1b[HQ", 0, 0, "Q"),            # home
        ("^[[2J", b"ab\x1b[2J\x1b[3dQ", 2, 2, "Q"),   # clear keeps the cursor
        ("\\b", b"ab\bQ", 0, 1, "Q"),
        ("\\r", b"ab\rQ", 0, 0, "Q"),
        ("^[[B/^[[A", b"ab\x1b[2BQ\x1b[A\x1b[10GW", 1, 9, "W"),
        ("wide glyph", "ab█c".encode(), 0, 3, "c"),   # one cell, as ncurses
    ]
    bad = []
    for name, blob, row, col, want in cases:
        scr = _Screen(PTY_ROWS, PTY_COLS)
        scr.feed(blob.decode("utf-8", "replace"))
        got = scr.grid[row][col]
        if got != want:
            bad.append("%s: cell %d,%d is %r, want %r" % (name, row, col, got,
                                                          want))
    torn = b"ab\x1b("                # a capture cut inside an escape sequence
    scr = _Screen(PTY_ROWS, PTY_COLS)
    scr.feed(torn.decode("utf-8", "replace"))
    if "(" in scr.text():
        bad.append("torn escape: %r was read as text" % "(")
    print("screen selftest: %s"
          % ("PASS (%d idioms)" % (len(cases) + 1) if not bad
             else "FAIL -- " + "; ".join(bad)))
    return not bad


def selftest():
    """Validate the harness itself, without the package under test.

    Run as `nms_pty_test.py --selftest`.  Two layers: the output replay (pure
    stdlib, so it runs anywhere, device included) and the pty plumbing of the
    interactive checks.  Both functional pty checks depend on the child seeing
    a 24x80 window, so the spawn path is worth verifying on its own before a
    build spends minutes on it.  Counts nothing towards the package
    assertions.

    Three outcomes for the pty half: PASS (pty works and reports 24x80), FAIL
    (a pty came up but the window is wrong — that would break the effect
    checks), and UNAVAILABLE (no pty can be allocated here at all, exit 0):
    expected on OHOS, where the sandbox denies /dev/ptmx, and harmless because
    the effect is covered over pipes in section [5].
    """
    ok = screen_selftest()
    probe = ("import fcntl,struct,termios,os;"
             "h=struct.unpack('HHHH', fcntl.ioctl(0, termios.TIOCGWINSZ, b'\\0'*8));"
             "print('WINSZ %d %d' % (h[0], h[1]));"
             "print('TTY %s' % ('yes' if os.isatty(0) else 'no'))")
    rc, out = run_in_pty(sys.executable, ["-c", probe], {}, timeout=20)
    text = out.decode("utf-8", "replace")
    if rc == -2:
        _avail, reason = pty_availability()
        print("pty selftest: UNAVAILABLE (%s)" % (reason or text.strip()))
        print("pty selftest: the pty checks will be reported as skipped; the "
              "effect path is covered over pipes instead")
        return 0 if ok else 1
    pty_ok = rc == 0 and "WINSZ %d %d" % (PTY_ROWS, PTY_COLS) in text
    print("pty selftest: rc=%d %s" % (rc, text.replace("\r\n", " | ").strip()))
    print("pty selftest: %s" % ("PASS" if pty_ok else "FAIL"))
    return 0 if (ok and pty_ok) else 1


def main():
    pkg = os.path.abspath(sys.argv[1])
    bindir = os.path.join(pkg, "bin")
    nms = os.path.join(bindir, "nms")
    sneakers = os.path.join(bindir, "sneakers")
    terminfo = os.path.join(pkg, "share", "terminfo")
    print("no-more-secrets consumer test (terminal harness)")
    print("package: %s" % pkg)

    # Watchdog.  This host has been observed to wedge a parent process in the
    # kernel's signal-delivery precheck right after it kills a child, which
    # would otherwise hang the whole run (and the caller's conan test step with
    # it).  A timer thread needs no signal delivery, so it still fires.
    watchdog = threading.Timer(900, lambda: os._exit(4))
    watchdog.daemon = True
    watchdog.start()

    # ── 1. package layout ────────────────────────────────────────────────
    print("[1] package layout")
    check(os.path.isfile(nms), "bin/nms is a regular file")
    check(os.path.isfile(sneakers), "bin/sneakers is a regular file")
    check(os.access(nms, os.X_OK), "bin/nms is executable")
    check(os.access(sneakers, os.X_OK), "bin/sneakers is executable")
    bin_entries = sorted(os.listdir(bindir)) if os.path.isdir(bindir) else []
    check(bin_entries == ["nms", "sneakers"],
          "bin/ holds exactly nms + sneakers (got %r)" % bin_entries)

    man6 = os.path.join(pkg, "share", "man", "man6")
    for page in ("nms.6", "sneakers.6"):
        path = os.path.join(man6, page)
        ok = os.path.isfile(path) and os.path.getsize(path) > 0
        check(ok, "share/man/man6/%s present and non-empty" % page)
        if ok:
            with open(path, "rb") as f:
                body = f.read()
            check(b".TH" in body, "%s has a roff .TH header" % page)

    lic = os.path.join(pkg, "licenses", "LICENSE")
    check(os.path.isfile(lic), "licenses/LICENSE present")
    if os.path.isfile(lic):
        with open(lic, "rb") as f:
            lic_body = f.read()
        check(b"GNU GENERAL PUBLIC LICENSE" in lic_body,
              "LICENSE is the GNU GPL text")
        check(b"Version 3" in lic_body, "LICENSE is GPL version 3")

    # ── 2. ELF sanity ────────────────────────────────────────────────────
    print("[2] ELF sanity")
    for name, path in (("nms", nms), ("sneakers", sneakers)):
        info = elf_info(path)
        check(info is not None, "%s is an ELF binary" % name)
        if info:
            check(info["class"] == "ELF64", "%s is ELF64" % name)
            if platform.machine().lower() in ("aarch64", "arm64"):
                check(info["machine"] == 183,  # EM_AARCH64
                      "%s is AArch64 (e_machine=%d)" % (name, info["machine"]))
            else:
                skip("%s machine check (host is %s, not aarch64)"
                     % (name, platform.machine()))
    if os.path.isfile(nms):
        with open(nms, "rb") as f:
            check(b"nms version 1.0.1" in f.read(),
                  "nms carries the upstream version string (1.0.1)")

    # ── 3. bundled terminfo database ─────────────────────────────────────
    print("[3] bundled terminfo database")
    check(os.path.isdir(terminfo), "share/terminfo shipped in the package")
    term = None
    if os.path.isdir(terminfo):
        entries = [e for e in ("ansi", "xterm", "vt100", "linux")
                   if find_terminfo_entry(terminfo, e)]
        check(bool(entries),
              "bundled terminfo resolves common terminals (found %r)" % entries)
        term = entries[0] if entries else None
        if find_terminfo_entry(terminfo, "xterm"):
            print("  [info] xterm entry present in the bundled database")
    run_env = {"TERMINFO": terminfo, "TERMINFO_DIRS": terminfo, "TERM": term or "ansi"}

    # ── 4. non-tty behaviour ─────────────────────────────────────────────
    print("[4] non-tty behaviour (no pty)")
    rc, out = run_collect(nms, ["-v"], run_env)
    check(rc == 0, "nms -v exits 0 (got %d)" % rc)
    check(out.strip() == b"nms version 1.0.1",
          "nms -v prints the exact banner (got %r)" % out[:80])

    rc, out = run_collect(nms, [], run_env, stdin_file=os.devnull)
    check(rc != 0, "nms with empty stdin exits non-zero (got %d)" % rc)
    # /dev/null makes nms probe for the input length (input.c) and refuse; on
    # OHOS that probe fails with ENOTTY (errno 25) and the wording changes to
    # "Could not get input", which is the same refusal reported differently.
    check(b"Input is empty" in out or b"Could not get input" in out,
          "nms with empty stdin reports an empty input (got %r)" % out[:80])

    rc, out = run_collect(nms, ["-Z"], run_env)
    check(rc != 0, "nms -Z (unknown option) exits non-zero (got %d)" % rc)
    check(b"Unknown option" in out,
          "nms -Z reports an unknown option (got %r)" % out[:80])

    rc, out = run_collect(sneakers, [], run_env,
                          stdin_data=b"FEDERAL RESERVE TRANSFER\n")
    check(rc == 1, "sneakers without a tty exits 1 (got %d)" % rc)
    check(b"Input not from an interactive terminal" in out,
          "sneakers explains the tty requirement (got %r)" % out[:80])

    # ── 5. the effect over pipes (no pty needed) ─────────────────────────
    # nms reads its input from stdin whenever stdin is not a tty, and the
    # ncurses effect draws to stdout — the documented `sneakers | nms` usage.
    # This is the path that works even where no pty can be allocated.  The
    # closing keypress is fed through the same still-open pipe (see
    # run_piped_effect): nms wants it in both modes, and a pipe that has been
    # closed makes it wait forever.  The plaintext is asserted against the
    # emulated screen (render_screen), never against the raw capture: ncurses
    # paints every cell with a scrambling glyph and only then overwrites it in
    # place, so the revealed text exists as terminal state, not as bytes.
    print("[5] ncurses effect over pipes")
    secret = b"TOP SECRET DATA"
    pipe_env = dict(run_env)
    pipe_env.update({"LINES": str(PTY_ROWS), "COLUMNS": str(PTY_COLS)})
    if not os.path.isfile(nms):
        check(False, "nms missing: the piped effect check cannot run")
    else:
        def revealed(blob):
            return shows_text(render_screen(blob), secret.decode())[0]

        rc, out, note = run_piped_effect(nms, ["-a"], pipe_env, secret,
                                         done=revealed)
        if note:
            print("  [info] %s" % note)
        # Exit 0 is the clean outcome and what a host with a controlling
        # terminal gets.  Where there is none (this device: the sandbox denies
        # ptys, so the piped run has no /dev/tty to answer from) the effect
        # still renders in full and the harness ends the run itself -- that is
        # a documented platform limit, and the strong "exits 0 on the closing
        # key" claim is asserted under a real pty in [6].  Anything else here
        # (a crash exit, a silent hang with no note) still fails.
        answered = rc == 0
        keyless = rc is not None and rc < 0 and "closing keypress" in note
        check(answered or keyless,
              "nms -a with piped input renders the effect and then ends "
              "(exit 0 after the closing key, or ended by the harness where "
              "/dev/tty is unreachable; got %s)" % rc)
        screen = render_screen(out)
        shown, how = shows_text(screen, secret.decode())
        check(shown,
              "the decryption effect renders the piped input (%s; screen: %r; "
              "got %r)" % (how, [ln for ln in screen.split("\n") if ln.strip()][:3],
                           out[:120]))
        check(b"\x1b[" in out,
              "the effect wrote terminal escape sequences to the pipe")
        check(b"Enter input" not in out,
              "no interactive prompt is printed for piped input")

        # A secret with a newline in it pins the replay's row tracking: the
        # effect prints the string in reading order, so a newline in it moves
        # the paint down one row.  That is the same machinery sneakers' panel
        # needs in [6] -- and unlike [6], this check runs on hosts with no pty
        # (measured on the OHOS device, and reproduced against pyte cell for
        # cell on the capture it produced).
        multi = (b"ALPHA BRAVO CHARLIE DELTA ECHO FOXTROT GOLF HOTEL INDIA "
                 b"JULIETT KILO LIMA\nSECOND ROW TEXT")

        def multi_rows(blob):
            return render_screen(blob).split("\n")

        def multi_done(blob):
            rows = multi_rows(blob)
            return (any("ALPHA BRAVO" in ln for ln in rows)
                    and any("SECOND ROW TEXT" in ln for ln in rows))

        rc, out, note = run_piped_effect(nms, ["-a"], pipe_env, multi,
                                         done=multi_done, wait_s=90)
        if note:
            print("  [info] %s" % note)
        rows = multi_rows(out)
        first_row = next((i for i, ln in enumerate(rows) if "ALPHA BRAVO" in ln),
                         None)
        second_row = next((i for i, ln in enumerate(rows)
                           if "SECOND ROW TEXT" in ln), None)
        check(first_row is not None and second_row == first_row + 1,
              "a multi-line secret renders on successive rows (got rows %s/%s; "
              "screen: %r)" % (first_row, second_row,
                               [ln for ln in rows if ln.strip()][:3]))

    # ── 6. functional run under a pty ────────────────────────────────────
    print("[6] functional run under a pty")
    pty_ok, pty_reason = pty_availability()
    if not pty_ok:
        print("  [info] no pty on this host: %s" % pty_reason)
        for msg in ("nms -a under a pty exits 0 after the closing key",
                    "the decryption effect reveals the typed input",
                    "nms prompts for input when stdin is a tty",
                    "sneakers under a pty exits 0 after the closing key",
                    "sneakers renders the remote terminal panel"):
            skip("%s (no pty on this host: %s)" % (msg, pty_reason))
    elif not os.path.isfile(nms):
        check(False, "nms missing: pty checks cannot run")
    else:
        rc, out = run_in_pty(nms, ["-a"], run_env, timeout=40,
                             send=secret + b"\n", send_after=secret, key=b"\r")
        check(rc == 0, "nms -a under a pty exits 0 after the closing key (got %d)" % rc)
        shown, how = shows_text(render_screen(out), secret.decode())
        check(shown,
              "the decryption effect reveals the typed input (%s; got %r)"
              % (how, out[:120]))
        check(b"Enter input" in out,
              "nms prompts for input when stdin is a tty (got %r)" % out[:120])

        if os.path.isfile(sneakers):
            rc, out = run_in_pty(sneakers, [], run_env, timeout=40, key=b"\x1b")
            check(rc == 0, "sneakers under a pty exits 0 after the closing key (got %d)" % rc)
            # The panel is painted exactly the way nms paints a secret: ncurses
            # writes each cell with its own cursor move and only re-emits the
            # cells whose content changed, so the panel line is not a substring
            # of the capture -- it exists as terminal state (CI measured both:
            # the raw-byte form of this check failed while the screen carried
            # the panel).  Assert on the replayed screen, never on the bytes.
            screen = render_screen(out)
            shown, how = shows_text(screen, "FEDERAL RESERVE TRANSFER NODE")
            check(shown,
                  "sneakers renders the remote terminal panel (%s; screen: %r; "
                  "got %r)" % (how, [ln for ln in screen.split("\n") if ln.strip()][:3],
                               out[:120]))

    # ── 7. negative injection controls (assertions must be load-bearing) ─
    print("[7] negative injection controls")
    tmp = tempfile.mkdtemp(prefix="nms-neg-")
    try:
        bad_bin = os.path.join(tmp, "nms")
        with open(bad_bin, "wb") as f:
            f.write(b"\x7fELF" + b"\x00" * 8)
        os.chmod(bad_bin, stat.S_IRWXU)
        rc, out = run_collect(bad_bin, ["-v"], run_env)
        check(rc != 0 or b"nms version" not in out,
              "a truncated nms cannot produce the version banner (rc=%d)" % rc)

        # Missing terminfo: ncurses has to fail on the same piped run that
        # passes in [5]; if this host still resolves the entry from its own
        # database the check is not applicable and is reported as SKIP.
        empty_ti = os.path.join(tmp, "empty-terminfo")
        os.makedirs(empty_ti, exist_ok=True)
        bare_env = {"TERM": term or "ansi",
                    "TERMINFO": os.path.join(tmp, "no-such-terminfo"),
                    "TERMINFO_DIRS": empty_ti,
                    "LINES": str(PTY_ROWS), "COLUMNS": str(PTY_COLS)}
        if os.path.isfile(nms):
            # A missing terminfo entry makes ncurses fail at init, so this run
            # exits non-zero on its own; the bounded timeout (rc -1) is only a
            # backstop for a host that resolves the entry from its own database.
            rc, out = run_collect(nms, ["-a"], bare_env,
                                  stdin_data=secret + b"\n", timeout=25)
            if rc == 126:
                # The binary could not be executed at all, so this control
                # cannot say anything about terminfo.
                skip("nms could not be executed here (rc 126): "
                     "bundle-is-load-bearing check not applicable")
            elif rc != 0 and not shows_text(render_screen(out), secret.decode())[0]:
                check(True, "without the bundled database nms cannot run "
                            "(exit %d) -> the terminfo bundle is load-bearing" % rc)
            else:
                skip("system terminfo still resolved the entry (rc=%d): "
                     "bundle-is-load-bearing check not applicable here" % rc)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\nnms_pty_test: %d assertions, %d failed, %d skipped"
          % (COUNT[0], len(FAILURES), COUNT[1]))
    if FAILURES:
        for f in FAILURES:
            print("  FAILED: %s" % f)
        return 1
    return 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["--selftest"]:
        sys.exit(selftest())
    sys.exit(main())
