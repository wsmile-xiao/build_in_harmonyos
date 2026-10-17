#!/usr/bin/env python3
"""echo_srv.py — minimal TCP echo server used by the httptunnel test_package.

Writes a marker file on the first accepted connection so the test can
prove that hts forwarded the tunnel to its destination.
Usage: echo_srv.py PORT MARKER_FILE
"""
import socket
import sys


def main() -> int:
    port = int(sys.argv[1])
    marker = sys.argv[2]
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))
    srv.listen(4)
    first = True
    while True:
        conn, _ = srv.accept()
        if first:
            with open(marker, "w") as f:
                f.write("connected\n")
            first = False
        try:
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                conn.sendall(data)
        except OSError:
            pass
        finally:
            conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
