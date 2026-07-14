#!/usr/bin/env python3
"""Test source for bannergrab 3.5 — starts a TCP server and verifies banner grabbing.

This script is invoked by test_package/conanfile.py test() method.
It starts a simple TCP server that sends a known banner, then runs
bannergrab against it and verifies the output.
"""
import socket
import subprocess
import sys
import threading
import time


def start_tcp_server(port, banner):
    """Start a TCP server that sends a banner on connection."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))
    srv.listen(1)
    srv.settimeout(5)

    ready = threading.Event()

    def serve():
        ready.set()
        try:
            conn, _ = srv.accept()
            conn.sendall(banner)
            time.sleep(0.5)
            conn.close()
        except Exception as e:
            print(f"Server error: {e}", file=sys.stderr)
        finally:
            srv.close()

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    return t, ready


def run_test():
    bannergrab = sys.argv[1] if len(sys.argv) > 1 else "bannergrab"
    port = 12399
    expected = "SSH-2.0-OpenSSH_test"

    # Start TCP server with known banner
    _, ready = start_tcp_server(port, (expected + "\r\n").encode())

    # Wait for server thread to be ready (replaces fixed sleep)
    if not ready.wait(timeout=5):
        print("FAIL: TCP server did not start within 5 seconds", file=sys.stderr)
        return 1

    # Run bannergrab in --no-triggers mode
    result = subprocess.run(
        [bannergrab, "--no-triggers", "127.0.0.1", str(port)],
        capture_output=True, text=True, timeout=10
    )

    output = result.stdout.strip()
    if expected in output:
        print(f"PASS: bannergrab correctly grabbed banner: {output}")
        return 0
    else:
        print(f"FAIL: expected '{expected}' in output, got: {output}")
        print(f"stderr: {result.stderr}")
        return 1


if __name__ == "__main__":
    sys.exit(run_test())
