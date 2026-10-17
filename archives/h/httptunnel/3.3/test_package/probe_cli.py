#!/usr/bin/env python3
"""probe_cli.py — TCP connect/echo probe used by the httptunnel test_package.

Default mode sends a token and checks it is echoed back (full round trip).
With --connect-only, only verifies that the TCP connection is accepted
(and writes one byte) before closing.
Usage: probe_cli.py PORT [--connect-only]
"""
import socket
import sys


def main() -> int:
    port = int(sys.argv[1])
    connect_only = "--connect-only" in sys.argv[2:]
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(20)
    try:
        s.connect(("127.0.0.1", port))
    except OSError as e:
        print(f"FAIL: connect to 127.0.0.1:{port} refused/failed: {e}")
        return 2
    if connect_only:
        try:
            s.sendall(b"x")
        except OSError as e:
            print(f"FAIL: send failed: {e}")
            return 3
        s.close()
        print(f"PASS: connection to 127.0.0.1:{port} accepted")
        return 0
    token = b"httptunnel-ping-glm18"
    try:
        s.sendall(token)
        got = b""
        while len(got) < len(token):
            chunk = s.recv(4096)
            if not chunk:
                break
            got += chunk
    except OSError as e:
        print(f"FAIL: echo exchange failed: {e}")
        return 3
    s.close()
    if got == token:
        print(f"ECHO-OK: {got.decode()}")
        return 0
    print(f"ECHO-MISMATCH: sent={len(token)} got={len(got)}")
    return 4


if __name__ == "__main__":
    sys.exit(main())
