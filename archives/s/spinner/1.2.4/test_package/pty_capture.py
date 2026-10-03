#!/usr/bin/env python3
"""Verify spinner's VT100 rotation on a real pty, or report why it is untestable.

Allocates a pty with pty.openpty(), runs spinner in the foreground on the slave,
and keeps draining the master AFTER the daemonised parent exits so that sustained
rotation (many frames) is observable rather than just a single frame.

Why a dedicated helper instead of script(1): on the headless HarmonyOS runner
script(1) does not give the child a usable *controlling terminal*, which is what
spinner's OpenTTY() requires (isatty() + tcdrain()). spinner also cannot be pointed
at a pty through its own -t switch here: its usage string is
`spinner[-IntTuvl<path>...]` so the path must be attached (`-t/dev/pts/N`); the
detached form exits EX_USAGE(64) and the attached form crashed (exit -11).

Capability probing
------------------
"spinner wrote nothing" and "this host cannot support spinner's daemon model" are
two different findings and must never be recorded as the same thing. The
discriminator is a *replica* of the exact syscall sequence spinner performs
(spinner.c Daemonize() + OpenTTY()):

    fork()
      child: setsid(); chdir("/"); umask(0); close(0); close(1); close(2);
      OpenTTY(): open(ttyname(STDIN_FILENO), O_WRONLY)   # by path, post-setsid
                 isatty(fd)
                 tcdrain(fd)                              # drain before writing
                 write(fd, frame)

The replica runs a known-good writer instead of spinner. Only when the replica
itself succeeds can "0 bytes from spinner" be attributed to spinner; otherwise it
is a property of the build host and is reported as untestable.

Exit codes:
  0  frames were captured and written to the output file
  3  this host cannot support spinner's daemon/pty sequence (replica failed);
     the caller should record this as SKIPPED, never as a pass
  4  the replica PROVED this host supports the sequence, yet spinner emitted no
     frame; that is a genuine defect of the artifact under test, not a runner
     limitation -- the caller must FAIL, never skip
  2  bad usage
"""
import os
import pty
import select
import subprocess
import sys
import termios
import time

if len(sys.argv) < 3:
    sys.stderr.write("usage: pty_capture.py <spinner> <outfile> [seconds]\n")
    sys.exit(2)

spinner, outfile = sys.argv[1], sys.argv[2]
seconds = float(sys.argv[3]) if len(sys.argv) > 3 else 6.0

HEAD = b"\x1b7\x1b[H\x1b[7m"

# Marker used by the daemon-sequence replica. Deliberately unrelated to spinner so
# that a pass can only come from the replica's own write reaching the master.
DAEMON_PROBE = b"DAEMONSEQPROBE"


def read_until(fds, needle, deadline):
    """Drain fds until needle is seen or the deadline passes. Returns all bytes."""
    chunks = b""
    pending = set(fds)
    while needle not in chunks and time.time() < deadline:
        if not pending:
            time.sleep(0.05)
            continue
        try:
            ready, _, _ = select.select(list(pending), [], [], 0.2)
        except (OSError, select.error):
            break
        for fd in ready:
            try:
                chunk = os.read(fd, 4096)
            except OSError:
                pending.discard(fd)
                continue
            if not chunk:
                pending.discard(fd)
                continue
            chunks += chunk
    return chunks


def daemon_sequence_replica():
    """Run spinner's exact fork/setsid/close/reopen/isatty/tcdrain/write sequence
    with a known-good writer, on a private pty that this process keeps open for
    the whole attempt.

    The private pty matters: closing the last descriptor on a pty slave makes the
    kernel tear the device down and unlink its /dev/pts entry, so the replica must
    never reuse (or run after the close of) the probe pty from steps 1 and 2.

    Returns (ok, evidence)."""
    try:
        rep_master, rep_slave = pty.openpty()
    except OSError as exc:
        return False, "daemon-sequence replica could not allocate a pty: %s" % exc
    try:
        path = os.ttyname(rep_slave)
    except OSError as exc:
        os.close(rep_master)
        os.close(rep_slave)
        return False, "daemon-sequence replica could not resolve the tty name: %s" % exc

    msg_r, msg_w = os.pipe()
    pid = os.fork()
    if pid == 0:  # ---- replica child: never let an exception escape ----
        os.close(msg_r)
        os.close(rep_master)
        stage = b"ok"
        try:
            os.setsid()
            for fd in (0, 1, 2):
                try:
                    os.close(fd)
                except OSError:
                    pass
            try:
                tty = os.open(path, os.O_WRONLY)  # exactly OpenTTY()
            except OSError as exc:
                stage = ("open-by-path:%s" % exc).encode("utf-8", "replace")
            else:
                if not os.isatty(tty):
                    stage = b"isatty-false-after-reopen"
                else:
                    # spinner drains the tty driver queue before each frame write
                    # (termios.h tcdrain). A missing Python binding is a binding
                    # gap, not a host limitation, so only a real OSError counts.
                    tcdrain = getattr(termios, "tcdrain", None)
                    if tcdrain is not None:
                        try:
                            tcdrain(tty)
                        except OSError as exc:
                            stage = ("tcdrain:%s" % exc).encode("utf-8", "replace")
                    if stage == b"ok":
                        try:
                            os.write(tty, DAEMON_PROBE)
                        except OSError as exc:
                            stage = ("write:%s" % exc).encode("utf-8", "replace")
                try:
                    os.close(tty)
                except OSError:
                    pass
        except Exception as exc:  # noqa: BLE001 - child must not raise
            stage = ("unexpected:%s" % exc).encode("utf-8", "replace")
        try:
            os.write(msg_w, stage[:200])
        except OSError:
            pass
        os._exit(0)

    # ---- replica parent: holds rep_slave open so the device survives ----
    os.close(msg_w)
    stage = b"child-silent"
    roundtrip = False
    deadline = time.time() + 5
    pending = {msg_r, rep_master}
    while pending and time.time() < deadline:
        try:
            ready, _, _ = select.select(list(pending), [], [], 0.2)
        except (OSError, select.error):
            break
        for fd in ready:
            try:
                data = os.read(fd, 4096)
            except OSError:
                pending.discard(fd)
                continue
            if not data:
                pending.discard(fd)
                continue
            if fd == msg_r:
                stage = data
                pending.discard(msg_r)
            else:
                if DAEMON_PROBE in data:
                    roundtrip = True
    for fd in (msg_r, rep_master, rep_slave):
        try:
            os.close(fd)
        except OSError:
            pass
    try:
        os.waitpid(pid, 0)
    except OSError:
        pass

    if stage != b"ok":
        return False, "daemon-sequence replica failed at %s" % stage.decode(
            "utf-8", "replace")
    if not roundtrip:
        return False, ("daemon-sequence replica wrote %r but the master never saw it"
                       % DAEMON_PROBE.decode())
    return True, ("daemon-sequence replica ok "
                  "(fork/setsid/close/reopen/isatty/tcdrain/write)")


# ---- probe: steps 1-3 ----------------------------------------------------------
# Any failure while *proving* capability means capability was not proven, so it must
# end in exit 3 -- never in an unhandled traceback, and never in an assertion.
def run_probe():
    """Returns None when the host is proven capable, else a diagnostic string."""
    # step 1 + 2: pty byte round-trip and reopen-by-path
    probe_master, probe_slave = pty.openpty()
    try:
        probe_path = os.ttyname(probe_slave)
        os.write(probe_slave, b"PTYPROBE")
        got = read_until([probe_master], b"PTYPROBE", time.time() + 2)
        try:
            reopened = os.open(probe_path, os.O_WRONLY)
            os.close(reopened)
            reopen_ok = True
        except OSError as exc:
            reopen_ok = False
            sys.stderr.write("pty_capture: reopen-by-path failed: %s\n" % exc)
    finally:
        for fd in (probe_master, probe_slave):
            try:
                os.close(fd)
            except OSError:
                pass

    if b"PTYPROBE" not in got or not reopen_ok:
        return ("host pty is not usable (roundtrip=%s reopen=%s)"
                % (b"PTYPROBE" in got, reopen_ok))

    # step 3: replica of spinner's daemon sequence. Steps 1 and 2 run in the
    # harness process, which is NOT spinner's situation: spinner closes
    # stdin/stdout/stderr and reopens the tty by path *after* setsid(), with no
    # controlling terminal. Only the replica exercises that.
    replica_ok, replica_evidence = daemon_sequence_replica()
    sys.stderr.write("pty_capture: %s\n" % replica_evidence)
    if not replica_ok:
        return replica_evidence
    return None


try:
    probe_failure = run_probe()
except OSError as exc:
    sys.stderr.write("pty_capture: openpty unavailable: %s\n" % exc)
    sys.exit(3)
except Exception as exc:  # noqa: BLE001 - an unproven capability is not a defect
    sys.stderr.write("pty_capture: probe could not complete: %r\n" % (exc,))
    sys.exit(3)

if probe_failure is not None:
    sys.stderr.write("pty_capture: host is NOT capable: %s\n" % probe_failure)
    # Proven environment limit: a known-good writer cannot complete the sequence
    # either, so "spinner emitted nothing" carries no information about spinner.
    sys.exit(3)

# ---- real run ------------------------------------------------------------------
master, slave = pty.openpty()
proc = subprocess.Popen(
    [spinner, "-F", "-T", "1"],
    stdin=slave, stdout=slave, stderr=slave,
    start_new_session=True,
    close_fds=True,
)

data = b""
deadline = time.time() + seconds
try:
    while time.time() < deadline:
        ready, _, _ = select.select([master], [], [], 0.3)
        if not ready:
            # The daemonised parent returns immediately; that is expected.
            # Keep draining so the child's frames are captured.
            continue
        try:
            chunk = os.read(master, 4096)
        except OSError:
            break
        if not chunk:
            break
        data += chunk
finally:
    for fd in (master, slave):
        try:
            os.close(fd)
        except OSError:
            pass
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass

with open(outfile, "wb") as fh:
    fh.write(data)

frames = data.count(HEAD)
sys.stderr.write("pty_capture: %d bytes, %d frames -> %s\n"
                 % (len(data), frames, outfile))
if frames == 0:
    # The replica above PROVED this host completes spinner's exact
    # fork/setsid/close/reopen/isatty/tcdrain/write sequence with a known-good
    # writer, so silence from spinner cannot be blamed on the runner: it is a
    # real defect of the artifact. Exit 4 (not 3) so the caller fails instead of
    # silently skipping a genuine regression.
    sys.stderr.write(
        "pty_capture: replica passed but spinner produced 0 frames "
        "=> product defect, not a runner limitation\n")
    sys.exit(4)
sys.exit(0)
