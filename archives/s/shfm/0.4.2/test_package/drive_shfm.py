#!/usr/bin/env python3
"""Drive the packaged shfm through a pseudo-terminal and report where it exits.

shfm cannot run headless: its body is executed as ``main >/dev/tty``, it switches the
terminal with ``stty -icanon -echo`` and reads keys with ``dd``.  The test therefore
creates a pty, makes it the controlling terminal of shfm and types the keys itself,
while shfm's stdout is a pipe -- exactly the situation of ``cd "$(shfm)"``.

usage: drive_shfm.py <shfm-script> <workdir> <result-file>

<workdir> holds alpha/, ohos_consumer/{consumer.c,notes.txt} and zeta.txt.  The scenario
runs once per launcher (``bash shfm`` and ``shfm`` through its #!/bin/sh shebang):

  start in <workdir>      screen lists alpha/ ohos_consumer/ zeta.txt, status line (1/3)
  j, l                    enters ohos_consumer/, status line (1/2) <workdir>/ohos_consumer
  l on consumer.c         shfm runs $SHFM_OPENER consumer.c; fd 3 must be closed in the child
  q                       exit status 0 and <workdir>/ohos_consumer printed on *stdout*

The unpatched script prints that path to the terminal instead of stdout whenever the shell
keeps the ``>/dev/tty`` redirect active while the EXIT trap runs (bash, mksh, zsh).  The
directory printed by shfm is stored in <result-file>.
"""
import fcntl
import os
import pty
import select
import shutil
import signal
import struct
import subprocess
import sys
import termios
import time

TIMEOUT = 30  # seconds per step; CI hosts can be slow

OPENER = """#!/bin/sh
# SHFM_OPENER stand-in: record the argument and whether fd 3 (cd-on-exit pipe) leaked in.
{
    printf 'arg=%s\\n' "$1"
    if ( : >&3 ) 2>/dev/null; then echo fd3=open; else echo fd3=closed; fi
} >"$OPENER_LOG"
"""


class Session:
    """shfm on a pty (stdin/stderr = slave, controlling tty) with a pipe as stdout."""

    def __init__(self, argv, env):
        self.master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
        try:
            self.proc = subprocess.Popen(
                argv, stdin=slave, stdout=subprocess.PIPE, stderr=slave, env=env,
                close_fds=True, start_new_session=True,
                preexec_fn=lambda: fcntl.ioctl(0, termios.TIOCSCTTY, 0))
        finally:
            os.close(slave)
        self.screen = b""

    def _pump(self, wait):
        """Read pty output for up to `wait` seconds; False once the pty is closed."""
        ready, _, _ = select.select([self.master], [], [], wait)
        if not ready:
            return True
        try:
            data = os.read(self.master, 65536)
        except OSError:  # EIO: every slave fd is closed, shfm is gone
            return False
        self.screen += data
        return bool(data)

    def expect(self, text, since):
        """Wait until `text` shows up on the screen after offset `since`."""
        needle = text.encode()
        deadline = time.monotonic() + TIMEOUT
        while needle not in self.screen[since:]:
            if time.monotonic() > deadline or not self._pump(0.2):
                raise AssertionError("timeout waiting for %r; screen tail: %r"
                                     % (text, self.screen[-300:]))
        return len(self.screen)

    def send(self, key):
        os.write(self.master, key.encode())

    def finish(self):
        deadline = time.monotonic() + TIMEOUT
        while self.proc.poll() is None:
            if time.monotonic() > deadline:
                raise AssertionError("shfm did not exit after 'q'; screen tail: %r"
                                     % self.screen[-300:])
            self._pump(0.2)
        out, _ = self.proc.communicate(timeout=TIMEOUT)
        return self.proc.returncode, out.decode()

    def close(self):
        if self.proc.poll() is None:
            os.killpg(self.proc.pid, signal.SIGKILL)
            self.proc.wait()
        if self.proc.stdout:
            self.proc.stdout.close()
        os.close(self.master)


def run_scenario(label, argv, workdir, env):
    expected = os.path.join(workdir, "ohos_consumer")
    log = env["OPENER_LOG"]
    if os.path.exists(log):
        os.remove(log)
    session = Session(argv + [workdir], env)
    try:
        pos = session.expect("(1/3) " + workdir, 0)
        for name in ("alpha/", "ohos_consumer/", "zeta.txt"):
            assert name.encode() in session.screen, "%s: %s not listed" % (label, name)

        session.send("j")
        pos = session.expect("(2/3) " + workdir, pos)

        before = pos
        session.send("l")
        pos = session.expect("(1/2) " + expected, pos)
        for name in ("consumer.c", "notes.txt"):
            assert name.encode() in session.screen[before:pos], \
                "%s: %s not listed after entering ohos_consumer/" % (label, name)

        session.send("l")  # consumer.c is a file: shfm hands it to $SHFM_OPENER
        pos = session.expect("(1/2) " + expected, pos)  # redraw after the opener returned
        with open(log) as handle:
            recorded = handle.read().split()
        assert recorded == ["arg=consumer.c", "fd3=closed"], \
            "%s: opener recorded %r" % (label, recorded)

        session.send("q")
        rc, out = session.finish()
    finally:
        session.close()
    assert rc == 0, "%s: shfm exit status %r" % (label, rc)
    assert out == expected + "\n", \
        "%s: cd-on-exit stdout is %r, expected %r" % (label, out, expected + "\n")
    print("PASS shfm[%s]: listing, navigation, opener(arg=consumer.c, fd3 closed), "
          "cd-on-exit stdout=%s" % (label, out.strip()))
    return out.strip()


def main():
    shfm, workdir, result = sys.argv[1:4]
    shfm = os.path.abspath(shfm)
    workdir = os.path.realpath(workdir)
    assert os.access(shfm, os.X_OK), "packaged script is not executable: " + shfm

    aux = workdir + ".aux"
    shutil.rmtree(aux, ignore_errors=True)
    os.makedirs(aux)
    opener = os.path.join(aux, "opener.sh")
    with open(opener, "w") as handle:
        handle.write(OPENER)
    os.chmod(opener, 0o755)

    env = dict(os.environ, LC_ALL="C", TERM="xterm", SHFM_OPENER=opener,
               OPENER_LOG=os.path.join(aux, "opener.log"))
    bash = shutil.which("bash") or "/data/service/hnp/bin/bash"
    selected = {run_scenario(label, argv, workdir, env)
                for label, argv in (("bash", [bash, shfm]), ("sh-shebang", [shfm]))}
    assert len(selected) == 1, "launchers disagree: %r" % selected
    with open(result, "w") as handle:
        handle.write(selected.pop() + "\n")


if __name__ == "__main__":
    main()
