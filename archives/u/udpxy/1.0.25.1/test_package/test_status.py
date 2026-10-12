#!/usr/bin/env python3
"""Functional test: a live udpxy server must serve its HTTP status page.

Starts `udpxy -T -a 127.0.0.1 -p <port>` in the foreground (no daemonize),
fetches /status/ over plain TCP, and asserts:
  1. the response starts with "HTTP/1.0 200 OK" (statpg.h HTML_PAGE_HEADER),
  2. the body carries udpxy identity markers,
  3. the page echoes the port we bound (proves we talk to OUR server).
Tries three high ports in turn so one busy port cannot fail the suite.
Exit 0 on success, 1 with a diagnostic otherwise.
Uses only the standard library (socket/subprocess/time).
"""
import os
import shutil
import socket
import subprocess
import sys
import time

CANDIDATE_PORTS = (18023, 18024, 18025)
CONNECT_TIMEOUT = 2.0
STARTUP_DEADLINE = 15.0


def find_udpxy():
    """Resolve the udpxy binary to an absolute path.

    test.sh invokes `udpxy ...` via the shell (PATH lookup by the shell
    succeeds), but this script previously re-resolved the bare name via
    execvp inside Python, which failed on the CI worker with
    FileNotFoundError even though the shell saw the binary. Prefer the
    absolute path exported by test.sh (UDPXY_BIN, from `command -v udpxy`),
    then shutil.which(), so Popen never depends on Python-side PATH search.
    """
    for cand in (os.environ.get("UDPXY_BIN"), shutil.which("udpxy")):
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    # Diagnostic fallback: log PATH once so a future miss is actionable.
    print("udpxy lookup failed: UDPXY_BIN=%r which=%r PATH=%r"
          % (os.environ.get("UDPXY_BIN"), shutil.which("udpxy"),
             os.environ.get("PATH")))
    return os.environ.get("UDPXY_BIN") or shutil.which("udpxy") or "udpxy"


UDPXY_BIN = find_udpxy()


def fetch_status(port):
    """Connect, request /status/, return raw response bytes."""
    with socket.create_connection(("127.0.0.1", port), timeout=CONNECT_TIMEOUT) as s:
        s.sendall(b"GET /status/ HTTP/1.0\r\n\r\n")
        chunks = []
        s.settimeout(CONNECT_TIMEOUT)
        try:
            while True:
                data = s.recv(65536)
                if not data:
                    break
                chunks.append(data)
        except socket.timeout:
            pass
        return b"".join(chunks)


def server_ready(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.0):
            return True
    except OSError:
        return False


def check_port(port):
    """Start the server on port; return (ok, detail)."""
    proc = subprocess.Popen(
        [UDPXY_BIN, "-T", "-a", "127.0.0.1", "-p", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + STARTUP_DEADLINE
        while time.time() < deadline:
            if proc.poll() is not None:
                return False, "server exited early with rc=%d" % proc.returncode
            if server_ready(port):
                break
            time.sleep(0.2)
        else:
            return False, "server did not listen within %ds" % STARTUP_DEADLINE

        body = fetch_status(port)
        if not body.startswith(b"HTTP/1.0 200 OK"):
            return False, "bad status line: %r" % body[:60]
        if b"udpxy" not in body:
            return False, "response lacks udpxy marker (%d bytes)" % len(body)
        if str(port).encode() not in body:
            return False, "response does not echo port %d" % port
        print("status page OK on port %d (%d bytes)" % (port, len(body)))
        return True, ""
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def main():
    errors = []
    for port in CANDIDATE_PORTS:
        ok, detail = check_port(port)
        if ok:
            print("PASS: live status page verified")
            return 0
        print("port %d unusable: %s" % (port, detail))
        errors.append("port %d: %s" % (port, detail))
    print("FAIL: no candidate port served the status page")
    for e in errors:
        print("  - %s" % e)
    return 1


if __name__ == "__main__":
    sys.exit(main())
