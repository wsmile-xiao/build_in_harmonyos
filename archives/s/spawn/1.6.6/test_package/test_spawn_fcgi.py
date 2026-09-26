#!/usr/bin/env python3
"""Black-box test for the installed spawn-fcgi binary.

The test uses a real loopback TCP listener created by spawn-fcgi and speaks
just enough FastCGI to verify begin-request, params, stdin, stdout, and
end-request handling.  It prints one CHECK-OK line per successful assertion
for the Conan wrapper to count.
"""
import argparse
import os
import socket
import subprocess
import sys
import time


FCGI_BEGIN_REQUEST = 1
FCGI_END_REQUEST = 3
FCGI_PARAMS = 4
FCGI_STDIN = 5
FCGI_STDOUT = 6
FCGI_RESPONDER = 1
EXPECTED_CHECKS = 7


def record(record_type, body=b""):
    if len(body) > 0xFFFF:
        raise ValueError("FastCGI record too large")
    header = bytes(
        [
            1,
            record_type,
            0,
            1,
            (len(body) >> 8) & 0xFF,
            len(body) & 0xFF,
            0,
            0,
        ]
    )
    return header + body


def name_value(name, value):
    name = name.encode("ascii")
    value = value.encode("ascii")
    if len(name) >= 128 or len(value) >= 128:
        raise ValueError("test name/value must use one-byte lengths")
    return bytes([len(name), len(value)]) + name + value


def recv_exact(sock, size):
    chunks = []
    remaining = size
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise RuntimeError("connection closed before FastCGI response completed")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def run_command(binary, option):
    proc = subprocess.run(
        [binary, option],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=10,
    )
    return proc.returncode, proc.stdout.decode("utf-8", "replace")


def unused_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spawn-fcgi", required=True)
    parser.add_argument("--backend", required=True)
    args = parser.parse_args()

    passed = []

    def check(condition, label):
        if not condition:
            raise AssertionError(label)
        passed.append(label)
        print("CHECK-OK: " + label, flush=True)

    process = None
    try:
        rc, version_output = run_command(args.spawn_fcgi, "-v")
        check(rc == 0 and "spawn-fcgi v1.6.6" in version_output, "version")

        rc, help_output = run_command(args.spawn_fcgi, "-h")
        check(rc == 0 and "Usage: spawn-fcgi" in help_output, "help")

        port = unused_port()
        process = subprocess.Popen(
            [
                args.spawn_fcgi,
                "-n",
                "-a",
                "127.0.0.1",
                "-p",
                str(port),
                "--",
                args.backend,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        client = None
        deadline = time.time() + 10
        while time.time() < deadline:
            if process.poll() is not None:
                break
            try:
                client = socket.create_connection(("127.0.0.1", port), timeout=0.25)
                break
            except OSError:
                time.sleep(0.05)
        check(client is not None, "tcp_listen")

        with client:
            client.settimeout(8)
            params = b"".join(
                [
                    name_value("GATEWAY_INTERFACE", "CGI/1.1"),
                    name_value("REQUEST_METHOD", "GET"),
                    name_value("SCRIPT_NAME", "/spawn-fcgi-test"),
                    name_value("SERVER_PROTOCOL", "HTTP/1.0"),
                    name_value("QUERY_STRING", ""),
                    name_value("REMOTE_ADDR", "127.0.0.1"),
                    name_value("SERVER_NAME", "localhost"),
                    name_value("SERVER_PORT", str(port)),
                ]
            )
            begin_body = bytes([0, FCGI_RESPONDER, 0, 0, 0, 0, 0, 0])
            request = b"".join(
                [
                    record(FCGI_BEGIN_REQUEST, begin_body),
                    record(FCGI_PARAMS, params),
                    record(FCGI_PARAMS),
                    record(FCGI_STDIN),
                ]
            )
            client.sendall(request)

            stdout_body = b""
            end_seen = False
            for _ in range(64):
                header = recv_exact(client, 8)
                if header[0] != 1 or header[2] != 0 or header[3] != 1:
                    raise AssertionError("fastcgi_response_header")
                content_length = (header[4] << 8) | header[5]
                padding_length = header[6]
                body = recv_exact(client, content_length) if content_length else b""
                if padding_length:
                    recv_exact(client, padding_length)
                if header[1] == FCGI_STDOUT:
                    stdout_body += body
                elif header[1] == FCGI_END_REQUEST:
                    check(len(body) == 8, "fastcgi_end_request")
                    end_seen = True
                    break
            check(end_seen, "fastcgi_response")
            check(b"spawn-fcgi-ok" in stdout_body, "fastcgi_stdout")

        output = process.communicate(timeout=10)[0].decode("utf-8", "replace")
        check(
            process.returncode == 0 and "FCGI_BACKEND_OK begin=1 params=1 stdin=1" in output,
            "backend_exit_zero",
        )
    except Exception as exc:
        print("CHECK-FAIL: %s: %s" % (type(exc).__name__, exc), flush=True)
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        print(
            "TEST_PACKAGE_RESULT total=%d passed=%d failed=%d"
            % (EXPECTED_CHECKS, len(passed), EXPECTED_CHECKS - len(passed)),
            flush=True,
        )
        return 1

    print(
        "TEST_PACKAGE_RESULT total=%d passed=%d failed=0"
        % (EXPECTED_CHECKS, len(passed)),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
