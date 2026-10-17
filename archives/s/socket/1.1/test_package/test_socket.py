#!/usr/bin/env python3
"""Functional test suite for the packaged `socket` binary.

Two layers:
  1. artifact checks  — the binary exists and is an aarch64 ELF image;
  2. runtime checks   — real functional assertions driven over a loopback TCP
     connection, where this script plays the peer (server or client) so that
     no test depends on two instances of the binary racing each other.

Upstream ships no test suite at all (no tests/ directory, no `check` target),
so these assertions are written from the socket(1) manual page and exercise
every source file of the program: option parsing and the client/server main
loops (socket.c), host/service resolution (socketp.c), the transfer loop and
the CRLF translation (io.c), the signal setup and the `-p` pipe plumbing
(utils.c), and the signal name table (siglist.c).

Skipping the runtime layer is deliberately hard to trigger:
  * on an aarch64 host (the CI worker) the binary MUST run — a failed launch
    is reported as a failure, never as a skip;
  * on a foreign-architecture host the launch failure must carry an explicit
    "cannot execute this image" marker (missing musl loader, exec format
    error, qemu signal). A binary that starts and then misbehaves is always
    judged by the functional assertions below.
"""
import os
import platform
import socket as pysocket
import subprocess
import sys
import threading
import time

EM_AARCH64 = 0xB7

# Markers proving the image itself could not be loaded/executed by this host.
# Anything outside this list means the process did start → assertions decide.
NOT_EXECUTABLE_MARKERS = (
    "Could not open '/lib/ld-musl",       # binfmt/qemu: target loader absent
    "Exec format error",                  # kernel refused the image
    "cannot execute binary file",
    "uncaught target signal",             # qemu-user cannot run the loader
    "qemu: could not open",
)

AARCH64_HOST_NAMES = ("aarch64", "arm64", "armv8", "armv8l")

SIGTERM_EXIT_STATUS = 241                 # the handler calls exit(-SIGTERM)


def find_binary(bindir):
    """Locate `socket` inside the tested package only.

    Deliberately no PATH fallback: a same-named binary elsewhere on PATH would
    let this suite pass without the package under test, defeating both R34 and
    the CI destructive reverse check.
    """
    if not bindir:
        return None
    candidate = os.path.join(bindir, "socket")
    return candidate if os.path.isfile(candidate) else None


def artifact_checks(binary):
    """Validate the packaged file is an executable aarch64 ELF."""
    with open(binary, "rb") as handle:
        header = handle.read(20)
    if header[:4] != b"\x7fELF":
        print(f"[fail] not an ELF image: {binary}")
        return False
    machine = int.from_bytes(header[18:20], "little")
    if machine != EM_AARCH64:
        print(f"[fail] unexpected ELF machine 0x{machine:x} (want 0x{EM_AARCH64:x})")
        return False
    if not os.access(binary, os.X_OK):
        print(f"[fail] not executable: {binary}")
        return False
    print(f"[ok] artifact: {binary} (aarch64 ELF, executable)")
    return True


def run_socket(binary, args, stdin_data=None, timeout=60):
    return subprocess.run([binary] + args, input=stdin_data,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, timeout=timeout)


def probe_runnable(binary):
    """Decide whether this host can execute the image at all.

    The verdict must not depend on the binary's exit status: a program that
    launches and then fails is a real test failure, not a skip condition.
    Called without arguments, socket(1) prints its usage line.
    """
    try:
        proc = run_socket(binary, [], stdin_data="", timeout=30)
    except OSError as exc:
        return False, f"OSError: {exc}"
    combined = f"{proc.stdout}{proc.stderr}"
    for marker in NOT_EXECUTABLE_MARKERS:
        if marker in combined:
            return False, combined.strip().splitlines()[:2]
    return True, (combined.strip().splitlines() or [f"exit status {proc.returncode}"])[0]


def free_port():
    """Reserve a loopback port number and release it for the binary to bind."""
    with pysocket.socket(pysocket.AF_INET, pysocket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def listening_socket():
    """A listening loopback socket this script owns (peer of the client mode)."""
    server = pysocket.socket(pysocket.AF_INET, pysocket.SOCK_STREAM)
    server.setsockopt(pysocket.SOL_SOCKET, pysocket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    server.settimeout(30)
    return server, server.getsockname()[1]


def connect_with_retry(port, attempts=40, delay=0.25):
    """Connect to a port the binary is about to listen on."""
    last = None
    for _ in range(attempts):
        try:
            conn = pysocket.create_connection(("127.0.0.1", port), timeout=30)
            conn.settimeout(30)
            return conn
        except OSError as exc:       # listen() not reached yet
            last = exc
            time.sleep(delay)
    raise AssertionError(f"could not connect to 127.0.0.1:{port}: {last}")


def recv_until(conn, marker, limit=4096, deadline=20.0):
    """Read from conn until marker shows up or the deadline passes."""
    data = b""
    end = time.time() + deadline
    while marker not in data and len(data) < limit and time.time() < end:
        try:
            chunk = conn.recv(limit)
        except pysocket.timeout:
            break
        if not chunk:
            break
        data += chunk
    return data


def stop(proc):
    if proc.poll() is None:
        proc.terminate()
    try:
        return proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        return proc.wait(timeout=10)


def usage_check(binary):
    """No arguments → the usage line from utils.c is printed."""
    proc = run_socket(binary, [], stdin_data="", timeout=30)
    combined = f"{proc.stdout}{proc.stderr}"
    ok = "Usage:" in combined and "[-p prog]" in combined
    return ok, combined.strip().splitlines()[:1]


def unknown_host_check(binary):
    """Name resolution failure is reported by socketp.c, not a crash."""
    proc = run_socket(binary, ["-q", "nosuchhost.invalid", "12345"],
                      stdin_data="", timeout=60)
    combined = f"{proc.stdout}{proc.stderr}"
    return "unknown host" in combined, combined.strip().splitlines()[:1]


def client_mode_check(binary, crlf=False):
    """Binary connects as client; this script is the server peer.

    Verifies both directions of the transfer loop (io.c). With crlf=True the
    `-c` translation must turn the outgoing LF into CRLF.
    """
    server, port = listening_socket()
    args = ["-q"] + (["-c"] if crlf else []) + ["127.0.0.1", str(port)]
    proc = subprocess.Popen([binary] + args, stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True)
    try:
        conn, _ = server.accept()
        with conn:
            proc.stdin.write("PING\n")
            proc.stdin.flush()
            received = recv_until(conn, b"PING")
            conn.sendall(b"PONG\n")
            time.sleep(1)
            out, _err = proc.communicate(timeout=30)   # closes stdin → EOF
    finally:
        server.close()
        stop(proc)
    if crlf:
        ok = received == b"PING\r\n"
        return ok, f"server saw {received!r} (want b'PING\\r\\n')"
    ok = received.startswith(b"PING") and "PONG" in out
    return ok, f"server saw {received!r}, client stdout {out.strip()!r}"


def server_mode_check(binary):
    """Binary listens (-s); this script is the client peer."""
    port = free_port()
    proc = subprocess.Popen([binary, "-q", "-s", str(port)],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    received = b""
    out = ""
    try:
        conn = connect_with_retry(port)
        with conn:
            proc.stdin.write("PONG\n")
            proc.stdin.flush()
            received = recv_until(conn, b"PONG")
            conn.sendall(b"PING\n")
            time.sleep(1)
            out, _err = proc.communicate(timeout=30)   # closes stdin → EOF
    finally:
        stop(proc)
    ok = received.startswith(b"PONG") and "PING" in out
    return ok, f"client saw {received!r}, server stdout {out.strip()!r}"


def prog_mode_check(binary):
    """`-p prog` wires a program's stdio to the connection (utils.c pipes)."""
    port = free_port()
    proc = subprocess.Popen(
        [binary, "-q", "-s", "-p", "/bin/echo HELLO-FROM-PROG", str(port)],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True)
    received = b""
    try:
        conn = connect_with_retry(port)
        with conn:
            received = recv_until(conn, b"HELLO-FROM-PROG")
    finally:
        stop(proc)
    return b"HELLO-FROM-PROG" in received, f"client saw {received!r}"


def signal_check(binary):
    """SIGTERM must reach the handler patched onto POSIX sigaction.

    The handler prints the signal name from siglist.c and exits with
    exit(-SIGTERM), i.e. status 241 — proof that the sigaction replacement of
    the BSD sigvec() setup is wired up, not merely compiled.
    """
    port = free_port()
    proc = subprocess.Popen([binary, "-q", "-s", str(port)],
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE, text=True)
    time.sleep(2)                        # let it reach accept()
    proc.terminate()                     # SIGTERM
    try:
        _out, err = proc.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        return False, "no reaction to SIGTERM within 30s"
    ok = proc.returncode == SIGTERM_EXIT_STATUS and "Termination signal" in err
    return ok, f"exit status {proc.returncode}, stderr {err.strip()!r}"


RUNTIME_CHECKS = (
    ("usage line is printed", usage_check),
    ("unknown host is reported", unknown_host_check),
    ("client mode transfers both directions", client_mode_check),
    ("server mode (-s) transfers both directions", server_mode_check),
    ("-c translates outgoing LF to CRLF", lambda b: client_mode_check(b, crlf=True)),
    ("-p wires a program to the connection", prog_mode_check),
    ("SIGTERM runs the sigaction handler", signal_check),
)


def main(argv):
    bindir = argv[1] if len(argv) > 1 else ""
    binary = find_binary(bindir)
    if binary is None:
        print(f"[fail] socket binary not found (bindir={bindir!r})")
        return 1
    if not artifact_checks(binary):
        return 1

    runnable, detail = probe_runnable(binary)
    host_is_aarch64 = platform.machine().lower() in AARCH64_HOST_NAMES
    if not runnable:
        if host_is_aarch64:
            print(f"[fail] aarch64 host cannot execute the packaged binary: {detail}")
            return 1
        print(f"[skip] host {platform.machine()} cannot execute aarch64 images: {detail}")
        print("[summary] artifact checks passed; runtime checks SKIPPED "
              "(foreign-architecture host) — this is not a pass")
        return 0
    print(f"[ok] binary runs: {detail}")

    passed = 0
    for label, check in RUNTIME_CHECKS:
        try:
            ok, info = check(binary)
        except Exception as exc:                      # noqa: BLE001
            ok, info = False, f"{type(exc).__name__}: {exc}"
        print(f"[{'ok' if ok else 'fail'}] {label} — {info}")
        passed += bool(ok)

    total = len(RUNTIME_CHECKS)
    print(f"[summary] runtime checks: {passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
