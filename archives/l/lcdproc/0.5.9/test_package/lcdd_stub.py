#!/usr/bin/env python3
"""lcdd_stub.py - a minimal LCDd wire-protocol peer for the consumer test.

Why this exists
---------------
`lcdproc` 0.5.9 is a *client/server* suite.  The only honest way to prove the
packaged client really works on HarmonyOS PC is to drive it through a complete
LCDd session: TCP connect, `hello` greeting, geometry negotiation, screen and
widget generation from real system data, and a clean protocol-driven shutdown.
`test.sh` runs the real packaged binary; this file is the *peer* on the other
end of the socket.

It is a test fixture, not a re-implementation of the product: nothing here is
shipped in the package, and every assertion in test.sh is made against bytes
the *packaged aarch64 OHOS client* actually put on the wire.

Why not the real LCDd daemon
----------------------------
`server/sock.c` uses `FD_SET`, and the OHOS NDK's <sys/select.h> rewrites that
macro to call `__fd_chk()` first.  Real OHOS libc exports `__fd_chk`, so LCDd
runs on the device; the local WSL emulation guest runs plain musl, which does
not, so the dynamic loader refuses to start LCDd there.  Driving LCDd itself
would therefore make the test pass or fail purely on which libc the machine
happens to have - a platform assumption, not a fact.  The client under test
does not use FD_SET, so driving the real client against this peer is
deterministic on both the build host and the device.

Protocol (upstream 0.5.9, clients/lcdproc/main.c + shared/sockets.c)
    client -> "hello\\n"
    server -> "connect wid <W> hgt <H> cellwid <CW> cellhgt <CH>\\n"
    server -> "listen <X>\\n"          (one per screen the client should show)
    client -> "client_set -name {LCDproc <hostname>}"
    client -> "screen_add <X>" / "screen_set ..." / "widget_add ..." /
              "widget_set ..."          (real values read from the live system)
    server -> "bye\\n"                  -> client exits 0 (exit_program())

The non-default geometry matters: `main.c` hardcodes wid=20 hgt=4 as the
pre-handshake fallback, so a client that ignored the `connect` line would emit
"widget_set L zero 20 4 0" instead of the negotiated numbers.  That single
line is therefore a hard proof that the handshake was really parsed.

Usage: lcdd_stub.py <portfile> <greetingfile> <streamfile> <hostfile> [seconds]
Exit code 0 = a full session was observed; non-zero = the session did not
complete (test.sh turns that into a FAIL).

`<hostfile>` receives this process's own hostname, so that test.sh can check
the hostname the *client* announced on the wire against the hostname the
machine really has.  That cross-check is what turns "the client said
something" into "the client read the live system".
"""
import os
import socket
import sys
import time

# Deliberately non-default and non-round: the packaged client must echo these
# numbers back, it cannot have them by accident.
WID = 33
HGT = 6
CELLWID = 5
CELLHGT = 8

# Screens the client is asked to build.  Chosen because `widget_set L zero
# <wid> <hgt> 0` (clients/lcdproc/load.c) carries the negotiated geometry
# verbatim and `widget_set T three` (clients/lcdproc/time_screen.c) carries
# live data read from /proc, so both are hard assertions.
SCREENS = "CLT"


def write_atomic(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        fh.write(data)
    os.rename(tmp, path)


def main():
    if len(sys.argv) < 5:
        sys.stderr.write("usage: lcdd_stub.py <portfile> <greetingfile> <streamfile>"
                         " <hostfile> [seconds]\n")
        return 2
    portfile, greetfile, streamfile, hostfile = sys.argv[1:5]
    budget = float(sys.argv[5]) if len(sys.argv) > 5 else 40.0

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    srv.settimeout(budget)
    port = srv.getsockname()[1]
    # Publish the port atomically: test.sh polls for this file, and a partially
    # written file would make the client connect to a truncated port number.
    write_atomic(portfile, "%d\n" % port)
    write_atomic(hostfile, socket.gethostname() + "\n")
    sys.stderr.write("lcdd_stub: listening on 127.0.0.1:%d\n" % port)
    sys.stderr.flush()

    conn = None
    try:
        conn, _ = srv.accept()
    except socket.timeout:
        sys.stderr.write("lcdd_stub: no client connected within %.0fs\n" % budget)
        write_atomic(greetfile, "")
        write_atomic(streamfile, "")
        return 1

    conn.settimeout(budget)
    try:
        greeting = conn.recv(4096)
        write_atomic(greetfile, greeting.decode("utf-8", "replace"))

        # Geometry negotiation + screen visibility, exactly as LCDd does.
        conn.sendall(("connect wid %d hgt %d cellwid %d cellhgt %d\n"
                      % (WID, HGT, CELLWID, CELLHGT)).encode())
        for ch in SCREENS:
            conn.sendall(("listen %s\n" % ch).encode())

        buf = b""
        deadline = time.time() + budget
        # Completion markers: the load screen echoes the negotiated geometry
        # and the time screen carries live /proc data.  Both only appear once
        # the client has parsed the connect line and entered main_loop().
        want = (b"widget_set L zero", b"widget_set T three", b"screen_add T")
        while time.time() < deadline:
            if all(m in buf for m in want):
                time.sleep(0.5)          # let the final widget_set land
                break
            try:
                chunk = conn.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            buf += chunk

        write_atomic(streamfile, buf.decode("utf-8", "replace"))
        conn.sendall(b"bye\n")             # clean, protocol-driven shutdown
        time.sleep(0.3)
        return 0 if all(m in buf for m in want) else 1
    except OSError as exc:
        sys.stderr.write("lcdd_stub: %s\n" % exc)
        write_atomic(greetfile, "")
        write_atomic(streamfile, "")
        return 1
    finally:
        try:
            if conn is not None:
                conn.close()
        finally:
            srv.close()


if __name__ == "__main__":
    sys.exit(main())
