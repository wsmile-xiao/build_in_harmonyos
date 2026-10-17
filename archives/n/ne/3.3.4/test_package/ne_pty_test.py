#!/usr/bin/env python3
"""Pty-based functional test for ne (the nice editor).

ne aborts when stdin is not a tty (ne.c freopen("/dev/tty") failure), so
every invocation must run under a pseudo-terminal. This harness:

  1. runs `ne --help` and checks the version banner (ne has no --version)
  2. macro round-trip: InsertString + Save + Exit -> edit persisted
  3. macro round-trip: Find + ReplaceAll + Save -> search/replace works
     (plain `Replace` is interactive; macros must use ReplaceAll/ReplaceOnce)
  4. undo round-trip: InsertString + Undo + Save -> original restored
     (the core invariant upstream test.rc checks with cmp)

Usage: ne_pty_test.py <ne_binary> <terminfo_dir>
Exit code: 0 = all tests passed, non-zero = failure.
"""
import os
import pty
import select
import sys
import tempfile
import time


def run_ne_pty(ne_bin, args, run_env, timeout=30):
    """Run ne under a pty; return (exit_code, output).

    On OHOS, reading the pty master after the child exits raises EIO
    instead of returning EOF. So: loop reading; on EOF/EIO or child exit,
    reap the child (waitpid) to get its real exit status.
    """
    env = dict(os.environ)
    env.update(run_env)

    pid, fd = pty.fork()
    if pid == 0:
        try:
            os.execve(ne_bin, args, env)
        except Exception:
            os._exit(127)

    deadline = time.time() + timeout
    output = b""
    io_done = False
    while not io_done and time.time() < deadline:
        r, _, _ = select.select([fd], [], [], 0.3)
        if r:
            try:
                data = os.read(fd, 65536)
                if not data:
                    io_done = True
                else:
                    output += data
            except OSError:
                io_done = True  # EIO: child side of the pty is gone
        else:
            try:
                wpid, st = os.waitpid(pid, os.WNOHANG)
                if wpid:
                    if os.WIFEXITED(st):
                        return os.WEXITSTATUS(st), output
                    return -os.WTERMSIG(st), output
            except ChildProcessError:
                return -1, output

    # Child closed its tty side but may still be alive: wait briefly for a
    # clean exit, otherwise kill and report.
    def _reap(block_s=2.0):
        end = time.time() + block_s
        while time.time() < end:
            try:
                wpid, st = os.waitpid(pid, os.WNOHANG)
                if wpid:
                    if os.WIFEXITED(st):
                        return os.WEXITSTATUS(st)
                    return -os.WTERMSIG(st)
            except ChildProcessError:
                return -1
            time.sleep(0.1)
        return None

    if io_done:
        code = _reap()
        if code is not None:
            return code, output
    try:
        os.kill(pid, 9)
    except ProcessLookupError:
        pass
    try:
        _, status = os.waitpid(pid, 0)
    except ChildProcessError:
        return -1, output
    if os.WIFEXITED(status):
        return os.WEXITSTATUS(status), output
    return -os.WTERMSIG(status), output


def main():
    ne_bin = sys.argv[1]
    terminfo = sys.argv[2]
    run_env = {
        "TERM": "ansi",
        "TERMINFO": terminfo,
        "TERMINFO_DIRS": terminfo,
    }

    # Test 1: --help banner (version + options)
    rc, out = run_ne_pty(ne_bin, [ne_bin, "--help"], run_env)
    assert rc == 0, "--help exited %d" % rc
    assert b"3.3.4" in out, "version string missing in help banner"
    assert b"--macro" in out, "--macro option missing in help"
    assert b"--utf8" in out, "--utf8 option missing in help"
    print("test1 --help: OK")

    # Test 2: macro InsertString + Save + Exit
    with tempfile.TemporaryDirectory() as td:
        doc = os.path.join(td, "hello.txt")
        with open(doc, "w") as f:
            f.write("hello world\nsecond line\n")
        macro = os.path.join(td, "m1.macro")
        with open(macro, "w") as f:
            f.write('InsertString "INSERTED"\nSave\nExit\n')
        rc, out = run_ne_pty(
            ne_bin, [ne_bin, "--noconfig", "--macro", macro, doc], run_env)
        assert rc == 0, "insert macro exited %d, out=%r" % (rc, out[:200])
        content = open(doc).read()
        assert content.startswith("INSERTED"), (
            "edit not persisted, got %r" % content[:80])
    print("test2 insert+save: OK")

    # Test 3: macro Find + ReplaceAll + Save
    with tempfile.TemporaryDirectory() as td:
        doc = os.path.join(td, "repl.txt")
        with open(doc, "w") as f:
            f.write("foo bar baz\n")
        macro = os.path.join(td, "m2.macro")
        with open(macro, "w") as f:
            f.write('Find "bar"\nReplaceAll "BAZ"\nSave\nExit\n')
        rc, out = run_ne_pty(
            ne_bin, [ne_bin, "--noconfig", "--macro", macro, doc], run_env)
        assert rc == 0, "replace macro exited %d, out=%r" % (rc, out[:200])
        content = open(doc).read()
        assert "BAZ" in content and "bar" not in content, (
            "replace failed, got %r" % content[:80])
    print("test3 find+replaceall: OK")

    # Test 4: undo round-trip (upstream test.rc core invariant)
    with tempfile.TemporaryDirectory() as td:
        doc = os.path.join(td, "undo.txt")
        with open(doc, "w") as f:
            f.write("ORIGINAL\n")
        macro = os.path.join(td, "m3.macro")
        with open(macro, "w") as f:
            f.write('InsertString "XXX"\nUndo\nSave\nExit\n')
        rc, out = run_ne_pty(
            ne_bin, [ne_bin, "--noconfig", "--macro", macro, doc], run_env)
        assert rc == 0, "undo macro exited %d, out=%r" % (rc, out[:200])
        content = open(doc).read()
        assert content == "ORIGINAL\n", (
            "undo failed, got %r" % content[:80])
    print("test4 undo round-trip: OK")

    print("ne_pty_test: all 4 tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
