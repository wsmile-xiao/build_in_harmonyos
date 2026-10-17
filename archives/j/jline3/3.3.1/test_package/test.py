#!/usr/bin/env python3
"""OpenHarmony consumer tests for the packaged JLine3 3.3.1 jars.

Verifies the exact packaged artifacts (nonempty, ZIP CRC, Java 8 bytecode,
required entries, class counts), then compiles a real consumer against the
aggregate jar and runs two scenarios:

1. pipe  (headless): TerminalBuilder dumb degradation over plain streams and
   a LineReader round trip. This is the mandatory headless smoke.
2. pty (exec-stty): the OHOS-specific system-terminal path. With no JNA/Jansi
   native runtime packaged, the system terminal must be served by ExecPty on
   top of busybox stty. The master side sets a 33x77 winsize and the child
   must report it back through stty, read one line in raw mode and restore
   the terminal attributes.
"""

import argparse
import fcntl
import os
import pty
import re
import select
import struct
import subprocess
import sys
import termios
import time
import zipfile

PIPE_EXPECTED = "jline3 3.3.1 pipe tests passed: 6"
PTY_EXPECTED = "jline3 3.3.1 pty tests passed: 9"

REQUIRED_ENTRIES = {
    "jline-terminal": (
        "org/jline/terminal/Terminal.class",
        "org/jline/terminal/TerminalBuilder.class",
        "org/jline/terminal/impl/ExecPty.class",
        "org/jline/terminal/impl/PosixSysTerminal.class",
    ),
    "jline-reader": (
        "org/jline/reader/LineReader.class",
        "org/jline/reader/impl/LineReaderImpl.class",
    ),
    "jline-builtins": (
        "org/jline/builtins/Nano.class",
        "org/jline/builtins/TTop.class",
    ),
    "jline": (
        "org/jline/terminal/Terminal.class",
        "org/jline/terminal/impl/ExecPty.class",
        "org/jline/reader/LineReader.class",
        "org/jline/reader/impl/LineReaderImpl.class",
        "org/jline/builtins/Nano.class",
        "org/jline/builtins/TTop.class",
        "org/jline/terminal/impl/jna/JnaNativePty.class",
        "META-INF/services/org.jline.terminal.spi.JansiSupport",
        "META-INF/services/org.jline.terminal.spi.JnaSupport",
    ),
}

EXPECTED_CLASS_COUNTS = {
    "jline-terminal": 65,
    "jline-reader": 50,
    "jline-builtins": 49,
    "jline": 233,
}


def fail(message):
    raise RuntimeError(message)


def class_major(data, entry, jar):
    if len(data) < 8 or data[:4] != b"\xca\xfe\xba\xbe":
        fail("{} in {} is not a valid Java class".format(entry, jar))
    return struct.unpack(">H", data[6:8])[0]


def verify_jars(lib, version):
    modules = ("jline-terminal", "jline-reader", "jline-builtins", "jline")
    paths = {}
    for module in modules:
        jar = os.path.join(lib, "{}-{}.jar".format(module, version))
        if not os.path.isfile(jar) or os.path.getsize(jar) <= 0:
            fail("Packaged {} JAR is missing or empty: {}".format(module, jar))
        with zipfile.ZipFile(jar) as archive:
            corrupt = archive.testzip()
            if corrupt:
                fail("{} has a corrupt ZIP entry: {}".format(jar, corrupt))
            entries = set(archive.namelist())
            class_entries = [e for e in entries if e.endswith(".class")]
            majors = {
                class_major(archive.read(entry), entry, jar)
                for entry in class_entries
            }
            if majors != {52}:
                fail(
                    "{} bytecode mismatch: majors={}".format(
                        jar, sorted(majors)
                    )
                )
            missing = sorted(set(REQUIRED_ENTRIES[module]) - entries)
            if missing:
                fail(
                    "{} is missing required entries: {}".format(
                        jar, ", ".join(missing)
                    )
                )
            count = len(class_entries)
            if count != EXPECTED_CLASS_COUNTS[module]:
                fail(
                    "Unexpected class count in {}: {} (expected {})".format(
                        jar, count, EXPECTED_CLASS_COUNTS[module]
                    )
                )
        paths[module] = jar
    return paths


def compile_consumer(javac, aggregate, work, source):
    classes = os.path.join(work, "consumer-classes")
    os.makedirs(classes, exist_ok=True)
    subprocess.run(
        [
            javac,
            "--release",
            "8",
            "-encoding",
            "UTF-8",
            "-cp",
            aggregate,
            "-d",
            classes,
            source,
        ],
        check=True,
    )
    return classes


def run_pipe(java, classpath):
    result = subprocess.run(
        [java, "-cp", classpath, "TestJLine3", "pipe"],
        check=True,
        text=True,
        capture_output=True,
        timeout=120,
    )
    lines = [ln.strip() for ln in result.stdout.strip().splitlines() if ln.strip()]
    if not lines:
        fail("pipe scenario produced no output")
    if lines[-1] != PIPE_EXPECTED:
        fail(
            "Unexpected pipe scenario output: {!r}; expected {!r}".format(
                lines[-1], PIPE_EXPECTED
            )
        )


def run_pty(java, classpath, work):
    pid, master = pty.fork()
    if pid == 0:  # child: exec java attached to the pty slave
        env = dict(os.environ)
        env["TERM"] = "xterm-256color"
        if not env.get("HOME"):
            env["HOME"] = work
        try:
            os.execve(java, [java, "-cp", classpath, "TestJLine3", "pty"], env)
        finally:
            os._exit(127)

    try:
        fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", 33, 77, 0, 0))
    except OSError:
        pass  # winsize set failed: the size assertion below will report it

    output = ""
    wrote_line = False
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            ready, _, _ = select.select([master], [], [], 1.0)
        except InterruptedError:
            continue
        if ready:
            try:
                chunk = os.read(master, 4096)
            except OSError:
                chunk = b""
            if not chunk:
                break
            output += chunk.decode("utf-8", "replace")
        if not wrote_line and "pty> " in output:
            os.write(master, b"ohos-pty-line\r")
            wrote_line = True
        if "tests passed:" in output and wrote_line:
            # give the child a moment to print trailing markers and exit
            time.sleep(0.5)
            try:
                while True:
                    ready, _, _ = select.select([master], [], [], 0.5)
                    if not ready:
                        break
                    chunk = os.read(master, 4096)
                    if not chunk:
                        break
                    output += chunk.decode("utf-8", "replace")
            except OSError:
                pass
            break
    else:
        os.kill(pid, 9)
        os.waitpid(pid, 0)
        fail("pty scenario timed out; output so far:\n" + output)

    _, status = os.waitpid(pid, 0)
    if status != 0:
        fail(
            "pty scenario child exited with status {}; output:\n{}".format(
                status, output
            )
        )
    if not wrote_line:
        fail("pty scenario never saw the LineReader prompt; output:\n" + output)

    size = re.search(r"JLINE_SIZE=(\d+)x(\d+)", output)
    if not size or size.group(1) != "77" or size.group(2) != "33":
        fail(
            "winsize round trip failed (expected 77x33): {!r} in:\n{}".format(
                size.groups() if size else None, output
            )
        )
    if "JLINE_CLASS=" + "org.jline.terminal.impl.PosixSysTerminal" not in output:
        fail("expected PosixSysTerminal marker; output:\n" + output)
    if "JLINE_PTYCLASS=org.jline.terminal.impl.ExecPty" not in output:
        fail("expected ExecPty marker; output:\n" + output)
    if PTY_EXPECTED not in output:
        fail(
            "Expected {!r} in pty output:\n{}".format(PTY_EXPECTED, output)
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lib", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--work", required=True)
    parser.add_argument("--java", required=True)
    parser.add_argument("--javac", required=True)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()

    paths = verify_jars(args.lib, args.version)
    aggregate = paths["jline"]
    classes = compile_consumer(args.javac, aggregate, args.work, args.source)
    classpath = os.pathsep.join([classes, aggregate])

    run_pipe(args.java, classpath)
    print("pipe scenario passed: dumb degradation + headless LineReader")
    run_pty(args.java, classpath, args.work)
    print("pty scenario passed: exec-stty driver, raw mode, winsize round trip")
    print("JAR verification passed: all 4 artifacts, clean ZIPs, Java 8 "
          "bytecode, required entries and class counts")
    print("jline3 {} OHOS consumer tests passed".format(args.version))


if __name__ == "__main__":
    main()
