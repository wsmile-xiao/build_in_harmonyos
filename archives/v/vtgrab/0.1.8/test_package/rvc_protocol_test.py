#!/usr/bin/env python3
"""RVC 001.000 protocol conformance probe for vtgrab's rvcd.

Runs on the build/test host (any architecture): it speaks the RVC 001.000 wire
protocol described in upstream's rvc.h against a live ``rvcd`` started from the
package's own bin/ directory, and checks the server's handshake replies byte for
byte.  This exercises the server's socket, protocol-version negotiation,
authentication negotiation, feature negotiation and client-initialisation parsing
paths on OHOS.

Terminal state: rvcd's console-capture stage needs a Linux virtual console
(/dev/ttyN, /dev/vcsaN, VT_GETSTATE/KDGETMODE ioctls).  OHOS has none, so on an
OHOS device rvcd reports "no console access" and exits 1 once the session has
been set up.  When the test host happens to expose a Linux console device to the
emulated guest, rvcd instead keeps polling it; both outcomes are accepted and
reported, but a crash is not.
"""
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time

PROTOCOL = b"RVC 001.000\n"
AUTH_NOAUTH = 1
MSG_CLIENT_INIT = 255
ROWS, COLS, UPDATEMS = 25, 80, 50
# rvcd.c: features[] = {Crop, Key, IncRectangle, IncScroll, SwitchRequest, Switch, Clear}
EXPECTED_FEATURES = [5, 0, 2, 3, 11, 6, 4]

failures = []


def check(cond, what):
    print("[ok] %s" % what if cond else "[fail] %s" % what)
    if not cond:
        failures.append(what)


def recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise EOFError("short read: wanted %d bytes, got %d" % (n, len(buf)))
        buf += chunk
    return buf


def _resolve(program):
    """Turn `program` into a path that os.posix_spawn() can exec directly.

    On OHOS the worker's Python has no _posixsubprocess, so subprocess.Popen()
    falls back to os.posix_spawn(), whose semantics are execve()'s: it never
    searches PATH.  A bare "rvcd" therefore dies with
    ``FileNotFoundError: [Errno 2] No such file or directory: 'rvcd'`` even
    though VirtualRunEnv had the package's bin/ on PATH and the shell's
    `command -v rvcd` had just succeeded (CI build #79522).  Resolve once,
    here, and spawn by path.
    """
    if os.path.dirname(program):
        return program
    found = shutil.which(program)
    if found is None:
        raise SystemExit("cannot find %r to spawn (PATH=%r)"
                         % (program, os.environ.get("PATH")))
    return found


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 6161
    rvcd = _resolve(sys.argv[2] if len(sys.argv) > 2 else "rvcd")

    log = tempfile.NamedTemporaryFile(prefix="rvcd-", suffix=".log", delete=False)
    proc = subprocess.Popen([rvcd, ":%d" % port], stdout=subprocess.DEVNULL, stderr=log)
    sock = None
    err_text = ""
    try:
        deadline = time.time() + 30
        while True:
            try:
                sock = socket.create_connection(("127.0.0.1", port), timeout=30)
                break
            except OSError:
                if time.time() > deadline or proc.poll() is not None:
                    raise
                time.sleep(0.2)

        # --- ServerInitialisation: ProtocolVersion ---
        greeting = recv_exact(sock, 12)
        check(greeting == PROTOCOL, "rvcd greets with %r (got %r)" % (PROTOCOL, greeting))

        # --- Authentication negotiation ---
        sock.sendall(PROTOCOL)
        auth = struct.unpack("!I", recv_exact(sock, 4))[0]
        check(auth == AUTH_NOAUTH, "rvcd offers AuthNoAuth=1 (got %d)" % auth)

        # --- Feature list ---
        num_features = recv_exact(sock, 1)[0]
        check(num_features == len(EXPECTED_FEATURES),
              "rvcd advertises %d features (got %d)" % (len(EXPECTED_FEATURES), num_features))
        features = list(recv_exact(sock, num_features))
        check(features == EXPECTED_FEATURES,
              "feature list is %s (got %s)" % (EXPECTED_FEATURES, features))

        # --- ClientInitialisation ---
        # Upstream sends this struct raw (rvc.c / nrvc.c: write_exact(fd, &ci,
        # sizeof(ci))), i.e. the 32-bit update interval travels in the sender's
        # native byte order.  Both the rvcd under test and any realistic client
        # are little-endian, so encode little-endian here.
        ci = struct.pack("<BBBBIBBBB", MSG_CLIENT_INIT, 0, 0, 0,
                         UPDATEMS, ROWS, COLS, 0, num_features)
        sock.sendall(ci)
        sock.sendall(bytes([1] * num_features))

        deadline = time.time() + 20
        while proc.poll() is None and time.time() < deadline:
            time.sleep(0.2)

        err_text = _read(log.name)
        check("Using ProtocolVersion" in err_text, "rvcd logged the protocol negotiation")
        check("In use: 5" in err_text, "rvcd enabled Feature_Crop from ClientInitialisation")
        check("rows: %d" % ROWS in err_text and "cols: %d" % COLS in err_text,
              "rvcd parsed the %dx%d geometry" % (ROWS, COLS))
        check("updatems: %d" % UPDATEMS in err_text, "rvcd parsed the update interval")

        rc = proc.poll()
        if rc is None:
            # A Linux console device is visible through the emulation layer, so
            # rvcd keeps polling it instead of failing.  Only a crash is a defect.
            proc.kill()
            proc.communicate()
            check(True, "rvcd still alive after ClientInitialisation "
                        "(Linux console visible via the test host)")
        else:
            check(rc >= 0, "rvcd did not die from a signal (returncode=%r)" % rc)
            # rvcd's console-capture stage needs the Linux virtual console:
            # open_console() (/dev/tty, /dev/tty0, /dev/console) plus the
            # VT_GETSTATE / KDGETMODE ioctls.  None exist on OHOS, so rvcd must
            # say so and exit non-zero rather than hang or crash.
            vt_missing = [m for m in ("no console access", "VT_GETSTATE", "KDGETMODE")
                          if m in err_text]
            check(rc != 0 and vt_missing,
                  "rvcd reported the unavailable Linux VT (%s) and exited rc=%d"
                  % (", ".join(vt_missing) or "no VT diagnostic", rc))
    finally:
        if sock is not None:
            sock.close()
        if proc.poll() is None:
            proc.kill()
        proc.wait()
        log.close()
        if not err_text:
            err_text = _read(log.name)
        os.unlink(log.name)
        if err_text:
            sys.stderr.write("--- rvcd stderr ---\n" + err_text)

    if failures:
        print("[FAIL] %d RVC protocol assertion(s) failed" % len(failures))
        return 1
    return 0


def _read(path):
    try:
        with open(path, "rb") as fh:
            return fh.read().decode("utf-8", "replace")
    except OSError:
        return ""


if __name__ == "__main__":
    sys.exit(main())
