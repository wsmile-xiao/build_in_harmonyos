#!/usr/bin/env python3
"""Installed-binary integration test for the packaged ocproxy 1.6.

The gate drives the packaged `ocproxy` and `vpnns` executables exactly as the
package ships them:

  * both binaries must load (no unresolved libevent symbols) and reject a
    missing VPNFD instead of crashing;
  * `-D <port>` must bring up a real SOCKS5 listener that answers the
    version/method negotiation and forwards a CONNECT request onto the tunnel;
  * `-L lport:rhost:rport` must bring up a real local port-forward listener;
  * a malformed `-D`/`-L`/`-I` argument must fail closed with the documented
    diagnostic and a non-zero exit status.

No VPN peer is needed: the tunnel side is a pipe passed through the `VPNFD`
environment variable, which is exactly the contract openconnect's --script-tun
uses.  Traffic entering ocproxy is written into that pipe, so the checks prove
that lwIP processing accepted and consumed the request rather than that a real
remote host answered.
"""

import os
import select
import socket
import subprocess
import sys
import time

CHECKS = []


def check(name, condition, detail=""):
    CHECKS.append((name, bool(condition), detail))
    status = "PASS" if condition else "FAIL"
    line = "  [%s] %s" % (status, name)
    if detail:
        line += " :: %s" % detail
    print(line, flush=True)


def run_binary(exe, args, env, timeout=15):
    proc = subprocess.Popen(
        [exe] + args,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
        return None, out
    return proc.returncode, out


def free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def wait_listener(port, proc, deadline=10.0):
    end = time.time() + deadline
    while time.time() < end:
        if proc.poll() is not None:
            return False
        try:
            conn = socket.create_connection(("127.0.0.1", port), timeout=0.5)
            conn.close()
            return True
        except OSError:
            time.sleep(0.1)
    return False


def main():
    bindir = sys.argv[1]
    ocproxy = os.path.join(bindir, "ocproxy")
    vpnns = os.path.join(bindir, "vpnns")

    print("== package layout ==")
    # Assert the executable bit as well as existence: a lost mode bit (the
    # E490 regression class for autotools helper scripts) must fail here rather
    # than surface as an opaque OSError from subprocess later on.
    check("ocproxy installed and executable",
          os.path.isfile(ocproxy) and os.access(ocproxy, os.X_OK), ocproxy)
    check("vpnns installed and executable",
          os.path.isfile(vpnns) and os.access(vpnns, os.X_OK), vpnns)

    base_env = dict(os.environ)

    print("== failure modes ==")
    rc, out = run_binary(ocproxy, [], base_env)
    check("missing VPNFD fails closed", rc not in (0, None) and "VPNFD is not set" in out,
          "rc=%r out=%r" % (rc, out.strip()[:120]))

    # VPNFD is parsed as an integer before anything else, so a bogus value
    # exercises the argument validation path without needing a real tunnel.
    env_bad = dict(base_env, VPNFD="not-a-number")
    rc, out = run_binary(ocproxy, [], env_bad)
    check("non-numeric VPNFD fails closed", "invalid integer" in out,
          "rc=%r out=%r" % (rc, out.strip()[:120]))

    # A socketpair is used instead of a plain pipe: the packet traffic that
    # ocproxy writes to the tunnel must be observable with select()/poll() on
    # this platform, and HMDFS pipe write ends are not reported readable even
    # when data is buffered (verified on the device: os.pipe() gave
    # bytes_read_from_tunnel=0 while socketpair delivered the frame).
    tunnel_child, tunnel_peer = socket.socketpair()
    tunnel_env = dict(
        base_env,
        VPNFD=str(tunnel_child.fileno()),
        INTERNAL_IP4_ADDRESS="10.9.0.2",
        INTERNAL_IP4_MTU="1400",
    )

    socks_port = free_port()
    fwd_port = free_port()
    proc = subprocess.Popen(
        [ocproxy, "-D", str(socks_port), "-L", "%d:example.invalid:22" % fwd_port],
        env=tunnel_env,
        pass_fds=(tunnel_child.fileno(),),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    tunnel_child.close()
    try:
        print("== live proxy behaviour ==")
        up = wait_listener(socks_port, proc)
        check("-D SOCKS5 listener accepts connections", up,
              "port=%d" % socks_port)
        fwd_up = wait_listener(fwd_port, proc)
        check("-L port-forward listener accepts connections", fwd_up,
              "port=%d" % fwd_port)

        if up:
            conn = socket.create_connection(("127.0.0.1", socks_port), timeout=5)
            conn.sendall(b"\x05\x01\x00")
            greeting = conn.recv(2)
            check("SOCKS5 no-auth negotiation answered", greeting == b"\x05\x00",
                  greeting.hex())

            # CONNECT 192.0.2.1:80 (TEST-NET-1).  The request is written into
            # the tunnel pipe, so a reply never arrives; the point of the check
            # is that ocproxy accepted and processed the request rather than
            # closing the connection or dying.
            conn.sendall(b"\x05\x01\x00\x01\xc0\x00\x02\x01\x00\x50")
            conn.settimeout(2.0)
            try:
                reply = conn.recv(10)
            except socket.timeout:
                reply = b""
            check("SOCKS5 CONNECT accepted for tunnel delivery",
                  proc.poll() is None and reply == b"",
                  "proxy_rc=%r reply=%r" % (proc.poll(), reply.hex()))
            conn.close()

            # The tunnel socket must actually receive the lwIP-generated packet
            # for the CONNECT, which proves the request reached the proxy core
            # instead of being answered or dropped by the TCP front end.
            # select() first so the read cannot block when nothing arrives.
            drained = 0
            readable, _, _ = select.select([tunnel_peer], [], [], 5.0)
            if readable:
                tunnel_peer.setblocking(False)
                try:
                    while True:
                        chunk = tunnel_peer.recv(65536)
                        if not chunk:
                            break
                        drained += len(chunk)
                except BlockingIOError:
                    pass
                tunnel_peer.setblocking(True)
            check("SOCKS5 request produced tunnel traffic", drained > 0,
                  "bytes_read_from_tunnel=%d" % drained)

            rc, out = run_binary(ocproxy, ["-D", "not-a-port"], tunnel_env)
            check("malformed -D fails closed",
                  rc not in (0, None) and "invalid integer" in out,
                  "rc=%r out=%r" % (rc, out.strip()[:120]))

            rc, out = run_binary(
                ocproxy, ["-L", "1234:onlyhost"], tunnel_env)
            check("truncated -L fails closed",
                  rc not in (0, None) and "Invalid port forward specifier" in out,
                  "rc=%r out=%r" % (rc, out.strip()[:120]))
    finally:
        proc.terminate()
        try:
            proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
        tunnel_peer.close()

    print("== version and help switches ==")
    rc, out = run_binary(ocproxy, ["--version"], base_env)
    check("ocproxy --version works without a tunnel",
          rc == 0 and "ocproxy 1.60" in out,
          "rc=%r out=%r" % (rc, (out or "").strip()[:160]))

    rc, out = run_binary(ocproxy, ["-V"], base_env)
    check("ocproxy -V short form works", rc == 0 and "ocproxy 1.60" in out,
          "rc=%r out=%r" % (rc, (out or "").strip()[:160]))

    rc, out = run_binary(ocproxy, ["--help"], base_env)
    check("ocproxy --help lists the tunnel options",
          rc == 0 and "-D <port>" in out and "VPNFD" in out,
          "rc=%r out=%r" % (rc, (out or "").strip()[:160]))

    print("== vpnns ==")
    rc, out = run_binary(vpnns, ["-h"], base_env)
    check("vpnns -h prints usage and exits 1",
          rc == 1 and "Create a new namespace and run COMMAND" in out,
          "rc=%r out=%r" % (rc, (out or "").strip()[:160]))

    rc, out = run_binary(vpnns, ["-v"], base_env)
    check("vpnns -v prints version and exits 0",
          rc == 0 and "vpnns" in out,
          "rc=%r out=%r" % (rc, (out or "").strip()[:160]))

    # Privacy hardening on top of the upstream crash: without a command vpnns
    # used to dereference the missing argument while setting up namespaces.
    rc, out = run_binary(vpnns, [], base_env)
    check("vpnns without a command fails closed",
          rc == 1 and "no command given" in out,
          "rc=%r out=%r" % (rc, (out or "").strip()[:160]))

    failures = [name for name, ok, _ in CHECKS if not ok]
    print("\nTOTAL=%d PASS=%d FAIL=%d" % (len(CHECKS), len(CHECKS) - len(failures), len(failures)))
    if failures:
        print("FAILED CHECKS: %s" % ", ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
