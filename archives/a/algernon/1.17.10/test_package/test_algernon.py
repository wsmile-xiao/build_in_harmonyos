#!/usr/bin/env python3
"""Consumer smoke test for the packaged algernon web server."""

import os
import socket
import subprocess
import sys
import time
import urllib.request


def pick_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    exe = os.path.abspath(sys.argv[1])
    if not os.path.isfile(exe):
        raise AssertionError(f"Missing algernon executable: {exe}")

    # 1. Version output
    version = subprocess.run(
        [exe, "--version"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    combined = (version.stdout or "") + (version.stderr or "")
    if version.returncode != 0:
        raise AssertionError(
            f"algernon --version exited {version.returncode}: {combined}"
        )
    if "Algernon 1.17.10" not in combined:
        raise AssertionError(f"Unexpected version output: {combined!r}")
    print(f"version output OK: {combined.strip()}")

    # 2. Serve a sample page on a temporary port and fetch it over HTTP
    port = pick_free_port()
    docroot = os.path.dirname(os.path.abspath(__file__))
    server = subprocess.Popen(
        [exe, "--quiet", "--addr", f"127.0.0.1:{port}", "--debug", docroot],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        body = None
        last_error = None
        for _ in range(40):
            if server.poll() is not None:
                out, err = server.communicate(timeout=5)
                raise AssertionError(
                    f"algernon server exited early rc={server.returncode}\n"
                    f"stdout: {out}\nstderr: {err}"
                )
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/", timeout=2
                ) as response:
                    body = response.read().decode("utf-8", errors="replace")
                break
            except Exception as exc:  # server still starting
                last_error = exc
                time.sleep(0.5)
        if body is None:
            raise AssertionError(
                f"algernon server did not answer HTTP requests: {last_error}"
            )
        print(f"HTTP response OK ({len(body)} bytes)")
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()

    print("algernon consumer smoke test passed")


if __name__ == "__main__":
    main()
