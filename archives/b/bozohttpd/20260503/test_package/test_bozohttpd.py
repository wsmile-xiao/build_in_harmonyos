#!/usr/bin/env python3
"""Run bozohttpd and check a static HTTP response over loopback."""

import os
import socket
import subprocess
import sys
import tempfile
import time


def main(binary):
    version = subprocess.run(
        [binary, "-G"], check=True, capture_output=True, text=True, timeout=10
    ).stdout.strip()
    assert version == "bozohttpd version bozohttpd/20260503", version

    with tempfile.TemporaryDirectory(prefix="bozohttpd-test-") as docroot:
        payload = b"bozohttpd HarmonyOS PC smoke test\n"
        with open(os.path.join(docroot, "health.txt"), "wb") as page:
            page.write(payload)

        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]

        server = subprocess.Popen(
            [binary, "-f", "-i", "127.0.0.1", "-I", str(port), "-n", "-q", docroot],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            response = None
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                if server.poll() is not None:
                    raise AssertionError(f"bozohttpd exited early with {server.returncode}")
                try:
                    client = socket.create_connection(("127.0.0.1", port), timeout=1)
                except OSError:
                    time.sleep(0.1)
                    continue

                with client:
                    client.settimeout(5)
                    client.sendall(
                        b"GET /health.txt HTTP/1.0\r\nHost: localhost\r\n\r\n"
                    )
                    chunks = bytearray()
                    marker = -1
                    while marker == -1:
                        chunk = client.recv(4096)
                        if not chunk:
                            raise AssertionError(
                                f"bozohttpd closed before sending HTTP headers: {bytes(chunks)!r}"
                            )
                        chunks.extend(chunk)
                        marker = chunks.find(b"\r\n\r\n")

                    headers = bytes(chunks[:marker])
                    body = bytearray(chunks[marker + 4 :])
                    content_lengths = [
                        line.split(b":", 1)[1].strip()
                        for line in headers.split(b"\r\n")
                        if line.lower().startswith(b"content-length:")
                    ]
                    assert len(content_lengths) == 1, headers.decode("latin1")
                    assert content_lengths[0].isdigit(), content_lengths[0]
                    content_length = int(content_lengths[0])
                    assert content_length == len(payload), content_length
                    while len(body) < content_length:
                        chunk = client.recv(min(4096, content_length - len(body)))
                        if not chunk:
                            raise AssertionError(
                                f"bozohttpd closed with {len(body)} of "
                                f"{content_length} response bytes"
                            )
                        body.extend(chunk)
                    assert len(body) == content_length, len(body)
                    response = headers + b"\r\n\r\n" + bytes(body)
                break

            assert response is not None, "bozohttpd did not accept a loopback connection"
            headers, body = response.split(b"\r\n\r\n", 1)
            assert headers.startswith(b"HTTP/1.0 200"), headers.decode("latin1")
            assert body == payload, body
        finally:
            server.terminate()
            try:
                server.wait(timeout=3)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=3)


if __name__ == "__main__":
    main(sys.argv[1])
