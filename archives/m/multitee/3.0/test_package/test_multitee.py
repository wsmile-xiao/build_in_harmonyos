#!/usr/bin/env python3
"""Functional tests for the packaged multitee 3.0 executable.

multitee 3.0 ships no upstream test suite (see MANIFEST.yml for the R51
census), so this suite drives the packaged binary through the behaviour that
multitee(1) documents.

Artifact checks (run on every host):
  A1  ELF64 little-endian image for EM_AARCH64
  A2  position-independent executable (ET_DYN)
  A3  PT_INTERP is the OHOS musl loader /lib/ld-musl-aarch64.so.1
  A4  the packaged file is executable

Functional checks (need a host that can execute the image):
  F1   0-1          stdin pipe copied to stdout byte-for-byte
  F2   0-1,A,B      200 KiB fan-out to three descriptors (tee equivalent)
  F3   -b 7 0-1     7-byte input buffer: thousands of read/write cycles
  F4   0:1 N:1      two inputs merged into one output, each chunk intact
  F5   0-1 N-1      keeps serving an input that is still open, exits once it closes
  F6   0-1eN N-1    'e' link: EOF on fd 0 forces EOF on the still-open fd N
  F7   0-1,N        EPIPE on a '-' output is only a warning, other outputs
                    complete (SIGPIPE caught by the sigaction() handler of sigsched)
  F8   0:1          EPIPE on a ':' output kills multitee with SIGPIPE
                    (sigdfl(): sigaction(SIG_DFL) + kill() + sigprocmask())
  F9   -q 0-1,N     quiet mode: F7 with nothing written to stderr
  F10  -x           unknown option: exit status 1 plus a diagnostic
  F11  (no args)    nothing to do: exit status 0, no output

Descriptor numbers are whatever this process owns; they are inherited through
pass_fds and spelled into the multitee arguments, so no descriptor juggling is
needed.

On an aarch64 host (the OHOS CI worker) every functional check is mandatory.
On a foreign-architecture host the functional layer is reported as SKIPPED -
never as passed - and only when launching the image fails with an explicit
loader/format marker; an image that starts is always judged by the checks.

usage: test_multitee.py <path/to/bin/multitee> [workdir]
"""

import os
import platform
import signal
import struct
import subprocess
import sys
import tempfile

EM_AARCH64 = 183
ET_DYN = 3
PT_INTERP = 3
OHOS_LOADER = "/lib/ld-musl-aarch64.so.1"
AARCH64_HOSTS = ("aarch64", "arm64", "armv8", "armv8l")
NOT_EXECUTABLE_MARKERS = (
    "Could not open '/lib/ld-musl",   # binfmt/qemu: target loader absent
    "Exec format error",              # kernel refused the image
)
TIMEOUT = 60


def artifact_checks(binary):
    """A1-A4 on the packaged file; returns a list of failure messages."""
    with open(binary, "rb") as handle:
        image = handle.read()
    if image[:4] != b"\x7fELF" or image[4] != 2 or image[5] != 1:
        return ["A1: not an ELF64 little-endian image"]
    failures = []
    e_type, e_machine = struct.unpack_from("<HH", image, 16)
    e_phoff = struct.unpack_from("<Q", image, 32)[0]
    e_phentsize, e_phnum = struct.unpack_from("<HH", image, 54)
    if e_machine != EM_AARCH64:
        failures.append(f"A1: e_machine={e_machine}, want EM_AARCH64 ({EM_AARCH64})")
    if e_type != ET_DYN:
        failures.append(f"A2: e_type={e_type}, want ET_DYN ({ET_DYN}, PIE)")
    interp = None
    for index in range(e_phnum):
        p_type, _flags, p_offset, _vaddr, _paddr, p_filesz = struct.unpack_from(
            "<IIQQQQ", image, e_phoff + index * e_phentsize)
        if p_type == PT_INTERP:
            interp = image[p_offset:p_offset + p_filesz].rstrip(b"\0").decode()
    if interp != OHOS_LOADER:
        failures.append(f"A3: PT_INTERP={interp!r}, want {OHOS_LOADER!r}")
    if not os.access(binary, os.X_OK):
        failures.append("A4: packaged file is not executable")
    return failures


def run(binary, args, stdin=None, stdout=subprocess.PIPE, pass_fds=(),
        data=None):
    """Run multitee to completion; returns (returncode, stdout, stderr)."""
    proc = subprocess.Popen([binary] + args, stdin=stdin, stdout=stdout,
                            stderr=subprocess.PIPE, pass_fds=pass_fds)
    out, err = proc.communicate(input=data, timeout=TIMEOUT)
    return proc.returncode, out or b"", err


def probe(binary):
    """Can this host start the image at all? (verdict ignores exit status)"""
    try:
        _rc, out, err = run(binary, [], stdin=subprocess.DEVNULL)
    except OSError as exc:
        text = str(exc)
    else:
        text = (out + err).decode(errors="replace")
    for marker in NOT_EXECUTABLE_MARKERS:
        if marker in text:
            return False, text.strip().splitlines()[0]
    return True, ""


class Suite:
    def __init__(self, binary, workdir):
        self.binary = binary
        self.workdir = workdir
        self.payload = os.urandom(200 * 1024)

    def path(self, name):
        return os.path.join(self.workdir, name)

    def infile(self, name, data):
        with open(self.path(name), "wb") as handle:
            handle.write(data)
        return open(self.path(name), "rb")

    def read(self, name):
        with open(self.path(name), "rb") as handle:
            return handle.read()

    def f1_stdin_to_stdout(self):
        data = b"".join(b"line %05d of the F1 payload\n" % i for i in range(2000))
        rc, out, err = run(self.binary, ["0-1"], stdin=subprocess.PIPE, data=data)
        assert rc == 0 and err == b"", (rc, err)
        assert out == data, "stdout differs from stdin"

    def f2_fanout(self):
        with self.infile("f2.in", self.payload) as src, \
                open(self.path("f2.a"), "wb") as out_a, \
                open(self.path("f2.b"), "wb") as out_b:
            fa, fb = out_a.fileno(), out_b.fileno()
            rc, out, err = run(self.binary, [f"0-1,{fa},{fb}"], stdin=src,
                               pass_fds=(fa, fb))
        assert rc == 0 and err == b"", (rc, err)
        assert out == self.payload, "fd 1 copy differs"
        assert self.read("f2.a") == self.payload, f"fd {fa} copy differs"
        assert self.read("f2.b") == self.payload, f"fd {fb} copy differs"

    def f3_small_buffer(self):
        data = self.payload[:20 * 1024]
        rc, out, err = run(self.binary, ["-b", "7", "0-1"],
                           stdin=subprocess.PIPE, data=data)
        assert rc == 0 and err == b"", (rc, err)
        assert out == data, "stdout differs with -b 7"

    def f4_merge(self):
        first = b"alpha from fd 0\n" * 40
        second = b"beta from the extra descriptor\n" * 40
        with self.infile("f4.0", first) as src0, self.infile("f4.n", second) as srcn:
            fd = srcn.fileno()
            rc, out, err = run(self.binary, ["0:1", f"{fd}:1"], stdin=src0,
                               pass_fds=(fd,))
        assert rc == 0 and err == b"", (rc, err)
        assert out in (first + second, second + first), "merged output is not two intact chunks"

    def f5_waits_for_open_input(self):
        early, late = b"early data from fd 0\n", b"late data from the pipe\n"
        rfd, wfd = os.pipe()
        with self.infile("f5.0", early) as src, open(self.path("f5.out"), "wb") as sink:
            proc = subprocess.Popen([self.binary, "0-1", f"{rfd}-1"], stdin=src,
                                    stdout=sink, stderr=subprocess.PIPE,
                                    pass_fds=(rfd,))
        os.close(rfd)
        try:
            try:
                proc.wait(timeout=1.5)
            except subprocess.TimeoutExpired:
                pass
            else:
                raise AssertionError(f"exited ({proc.returncode}) while fd {rfd} was still open")
            os.write(wfd, late)
        finally:
            os.close(wfd)
        _out, err = proc.communicate(timeout=TIMEOUT)
        assert proc.returncode == 0 and err == b"", (proc.returncode, err)
        assert self.read("f5.out") == early + late, "output is not early+late"

    def f6_eof_link(self):
        rfd, wfd = os.pipe()  # write end stays open for the whole run
        try:
            with self.infile("f6.0", self.payload) as src:
                rc, out, err = run(self.binary, [f"0-1e{rfd}", f"{rfd}-1"],
                                   stdin=src, pass_fds=(rfd,))
        finally:
            os.close(rfd)
            os.close(wfd)
        assert rc == 0 and err == b"", (rc, err)
        assert out == self.payload, "stdout differs"

    def _broken_stdout(self, args, name):
        """Run with fd 1 = pipe without reader and one extra file output."""
        rfd, wfd = os.pipe()
        os.close(rfd)
        try:
            with self.infile(name + ".in", self.payload[:64 * 1024]) as src, \
                    open(self.path(name + ".out"), "wb") as sink:
                fd = sink.fileno()
                rc, _out, err = run(self.binary, [a.replace("N", str(fd)) for a in args],
                                    stdin=src, stdout=wfd, pass_fds=(fd,))
        finally:
            os.close(wfd)
        return rc, err, self.read(name + ".out")

    def f7_epipe_warning(self):
        rc, err, copy = self._broken_stdout(["0-1,N"], "f7")
        assert rc == 0, f"exit status {rc}"
        assert b"multitee: warning: cannot write descriptor 1" in err, err
        assert copy == self.payload[:64 * 1024], "surviving output incomplete"

    def f8_sigpipe_fatal(self):
        rfd, wfd = os.pipe()
        os.close(rfd)
        try:
            with self.infile("f8.in", self.payload[:64 * 1024]) as src:
                rc, _out, _err = run(self.binary, ["0:1"], stdin=src, stdout=wfd)
        finally:
            os.close(wfd)
        assert rc == -signal.SIGPIPE, f"exit status {rc}, want death by SIGPIPE"

    def f9_quiet(self):
        rc, err, copy = self._broken_stdout(["-q", "0-1,N"], "f9")
        assert rc == 0 and err == b"", (rc, err)
        assert copy == self.payload[:64 * 1024], "surviving output incomplete"

    def f10_bad_option(self):
        rc, out, err = run(self.binary, ["-x", "0-1"], stdin=subprocess.DEVNULL)
        assert rc == 1, f"exit status {rc}"
        assert out == b"" and b"illegal option -- x" in err, (out, err)

    def f11_no_arguments(self):
        rc, out, err = run(self.binary, [], stdin=subprocess.DEVNULL)
        assert (rc, out, err) == (0, b"", b""), (rc, out, err)

    def run_all(self):
        checks = [getattr(self, name) for name in sorted(
            (n for n in dir(self) if n[0] == "f" and n[1].isdigit()),
            key=lambda n: int(n[1:].split("_")[0]))]
        failed = 0
        for check in checks:
            label = check.__name__
            try:
                check()
            except Exception as exc:  # fail closed: any error is a failure
                failed += 1
                print(f"[fail] {label}: {exc!r}")
            else:
                print(f"[ok]   {label}")
        return len(checks) - failed, failed


def main(argv):
    if len(argv) not in (2, 3):
        print(__doc__.strip().splitlines()[-1])
        return 2
    if sys.flags.optimize:
        print("[fail] python -O strips the assert statements of F1-F11; run without -O")
        return 1
    binary = argv[1]
    workdir = argv[2] if len(argv) == 3 else os.getcwd()
    if not os.path.isfile(binary):
        print(f"[fail] multitee binary not found: {binary}")
        return 1

    problems = artifact_checks(binary)
    for problem in problems:
        print(f"[fail] {problem}")
    if problems:
        return 1
    print(f"[ok]   A1-A4 artifact checks: {binary} is an aarch64 PIE for {OHOS_LOADER}")

    host = platform.machine().lower()
    if host not in AARCH64_HOSTS:
        runnable, detail = probe(binary)
        if not runnable:
            print(f"[skip] F1-F11 not run: this {host} host cannot execute the "
                  f"aarch64 OHOS image ({detail}); they run on the aarch64 CI worker")
            print("RESULT: artifact checks 4/4 passed, functional checks 0/11 run (SKIPPED)")
            return 0

    with tempfile.TemporaryDirectory(prefix="multitee-test-", dir=workdir) as tmp:
        passed, failed = Suite(binary, tmp).run_all()
    print(f"RESULT: artifact checks 4/4 passed, functional checks {passed}/{passed + failed} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
