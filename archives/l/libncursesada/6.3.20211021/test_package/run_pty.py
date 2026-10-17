#!/usr/bin/env python3
"""Drive the Ada consumer under a pseudo-terminal and assert its marker."""
import os, pty, select, sys, time

MARKER = b"LIBNCURSESADA_CONSUMER_OK"


def main(argv):
    pid, fd = pty.fork()
    if pid == 0:
        env = dict(os.environ)
        # test.sh records the ncurses terminfo directory; without it a minimal
        # OHOS image has no compiled terminfo and initscr() dies with
        # "Error opening terminal: xterm".
        terminfo = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".terminfo_path")
        try:
            with open(terminfo) as fh:
                recorded = fh.read().strip()
            if recorded and os.path.isdir(recorded):
                env.setdefault("TERMINFO_DIRS", recorded)
        except OSError:
            pass
        # A bare CI shell often exports TERM=dumb; ncurses then aborts with
        # "Error opening terminal: dumb." before the marker is printed.
        if not env.get("TERM") or env["TERM"] == "dumb":
            env["TERM"] = "xterm"
        env.setdefault("LINES", "24")
        env.setdefault("COLUMNS", "80")
        os.execve(argv[0], argv, env)
    out = b""
    deadline = time.time() + 30
    while time.time() < deadline:
        r, _, _ = select.select([fd], [], [], 1.0)
        if not r:
            continue
        try:
            chunk = os.read(fd, 4096)
        except OSError:
            break
        if not chunk:
            break
        out += chunk
        if MARKER in out:
            break
    try:
        os.kill(pid, 9)
    except OSError:
        pass
    try:
        os.waitpid(pid, 0)
    except OSError:
        pass
    sys.stdout.write(out.decode("utf-8", "replace"))
    if MARKER not in out:
        sys.stderr.write("\nPTY_MARKER_MISSING\n")
        return 1
    sys.stdout.write("\nPTY_OK\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
