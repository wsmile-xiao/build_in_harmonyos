#!/usr/bin/env python3
"""Minimal IRC server used by the sic consumer test.

Listens on 127.0.0.1:<port>, accepts one client, reads until the client has
sent its USER registration line, replies with a numeric welcome and a PING,
then reads until the client answers with PONG (or a short timeout).  Everything
received is written to <outfile> so the shell test can assert on it.

Usage: python3 sic_ircsrv.py <port> <outfile>
"""
import socket
import sys
import time


def main():
    port = int(sys.argv[1])
    outfile = sys.argv[2]
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.settimeout(20)
    try:
        srv.bind(("127.0.0.1", port))
        srv.listen(1)
    except OSError:
        with open(outfile, "wb"):
            pass
        return 0

    data = b""
    try:
        conn, _ = srv.accept()
    except OSError:
        with open(outfile, "wb"):
            pass
        return 0

    conn.settimeout(5)
    deadline = time.time() + 8
    while time.time() < deadline:
        try:
            chunk = conn.recv(4096)
        except OSError:
            break
        if not chunk:
            break
        data += chunk
        if b"USER" in data:
            break

    try:
        conn.sendall(b":irc.local 001 sic :welcome to the test server\r\n"
                     b"PING :probe\r\n")
    except OSError:
        pass

    deadline = time.time() + 8
    while time.time() < deadline:
        try:
            chunk = conn.recv(4096)
        except OSError:
            break
        if not chunk:
            break
        data += chunk
        if b"PONG" in data:
            break

    with open(outfile, "wb") as handle:
        handle.write(data)
    try:
        conn.close()
    except OSError:
        pass
    srv.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
