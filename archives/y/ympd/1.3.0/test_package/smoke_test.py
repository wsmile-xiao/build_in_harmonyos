"""Exercise the packaged CLI and its HTTP server as a consumer would."""

import http.client
import logging
import socket
import subprocess
import sys
import time


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    logging.info("PASS: %s", message)


def main(binary):
    version = subprocess.run(
        [binary, "-v"], capture_output=True, text=True, timeout=10
    )
    check(version.returncode == 0, "-v exits successfully")
    check(
        version.stdout.splitlines()[0].strip() == "ympd  1.3.0",
        "-v reports the packaged 1.3.0 version",
    )

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    server = subprocess.Popen(
        [binary, "-w", f"127.0.0.1:{port}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        response = None
        deadline = time.monotonic() + 10
        last_error = None
        while time.monotonic() < deadline:
            if server.poll() is not None:
                details = server.stderr.read()
                raise AssertionError(f"ympd exited before serving HTTP: {details}")
            try:
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
                connection.request("GET", "/")
                response = connection.getresponse()
                body = response.read()
                connection.close()
                break
            except OSError as error:
                last_error = error
                time.sleep(0.1)

        if response is None:
            raise AssertionError(f"HTTP server did not accept a loopback request: {last_error}")
        check(response is not None, "HTTP server accepts a loopback request")
        check(response.status == 200, "GET / returns HTTP 200")
        check(b"ympd" in body.lower(), "GET / serves the embedded ympd page")
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if len(sys.argv) != 2:
        raise SystemExit("usage: smoke_test.py <ympd-binary>")
    main(sys.argv[1])
