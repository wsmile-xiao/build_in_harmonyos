#!/usr/bin/env python3
"""End-to-end checks for the packaged webfsd application."""

import argparse
import http.client
import json
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import time


PAYLOAD = b"webfs HarmonyOS integration fixture\x00range-bytes\n"


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def start_server(binary, root, port, certificate=None):
    args = [binary, "-F", "-4", "-i", "127.0.0.1", "-p", str(port), "-r", root]
    if certificate:
        args.extend(["-S", "-C", certificate])
    process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"webfsd exited during startup ({process.returncode})")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                return process
        except OSError:
            time.sleep(0.05)
    stop_server(process)
    raise TimeoutError("webfsd did not begin listening within 8 seconds")


def stop_server(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=4)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=4)


def request(port, path, headers=None, tls_context=None):
    if tls_context is None:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=4)
    else:
        connection = http.client.HTTPSConnection(
            "127.0.0.1", port, timeout=4, context=tls_context
        )
    try:
        connection.request("GET", path, headers=headers or {"Connection": "close"})
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def record(results, name, passed, detail):
    results[name] = bool(passed)
    sys.stdout.write(f"{'[PASS]' if passed else '[FAIL]'} {name}: {detail}\n")
    sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--webfsd", required=True)
    parser.add_argument("--openssl", required=True)
    parser.add_argument("--target-os", required=True)
    options = parser.parse_args()

    binary = str(Path(options.webfsd).resolve())
    openssl = options.openssl
    if not Path(openssl).is_file():
        openssl = shutil.which(openssl) or openssl
    if not Path(openssl).is_file():
        harmonybrew_openssl = Path.home() / ".harmonybrew" / "bin" / "openssl"
        if harmonybrew_openssl.is_file():
            openssl = str(harmonybrew_openssl)
    if not Path(openssl).is_file():
        raise FileNotFoundError(f"OpenSSL executable not found: {options.openssl}")
    results = {}
    help_result = subprocess.run([binary, "-h"], capture_output=True, text=True, timeout=5)
    help_text = help_result.stdout + help_result.stderr
    usage_present = "usage: webfsd" in help_text and "-h       print this text" in help_text
    record(results, "A1_help_usage", usage_present,
           f"exit={help_result.returncode}, usage_present={usage_present}")
    record(results, "A2_tls_option_advertised", "-S" in help_text,
           "SSL option present in webfsd -h" if "-S" in help_text else "SSL option absent")

    is_ohos = options.target_os.lower() == "ohos"
    range_name = "A6_ohos_sendfile_emulation_range_206" if is_ohos else "A6_range_status_206"

    with tempfile.TemporaryDirectory(prefix="webfs-test-") as tmp:
        root = Path(tmp) / "www"
        root.mkdir()
        (root / "index.bin").write_bytes(PAYLOAD)
        http_port = free_port()
        http_process = None
        try:
            http_process = start_server(binary, str(root), http_port)
            status, _headers, body = request(http_port, "/index.bin")
            record(results, "A3_http_status_200", status == 200, f"status={status}")
            record(results, "A4_http_exact_body", body == PAYLOAD,
                   f"received={len(body)} bytes, expected={len(PAYLOAD)}")

            missing_status, _headers, _body = request(http_port, "/missing.bin")
            record(results, "A5_missing_path_404", missing_status == 404,
                   f"status={missing_status}")

            first, last = 3, 11
            range_status, range_headers, range_body = request(
                http_port, "/index.bin", {"Range": f"bytes={first}-{last}", "Connection": "close"}
            )
            expected_range = f"bytes {first}-{last}/{len(PAYLOAD)}"
            record(results, range_name, range_status == 206, f"status={range_status}")
            record(results, "A7_content_range_exact",
                   range_headers.get("Content-Range") == expected_range,
                   f"Content-Range={range_headers.get('Content-Range')!r}")
            record(results, "A8_range_body_exact", range_body == PAYLOAD[first:last + 1],
                   f"received={range_body!r}")
        except Exception as error:
            for name in (
                "A3_http_status_200", "A4_http_exact_body", "A5_missing_path_404",
                range_name,
                "A7_content_range_exact", "A8_range_body_exact",
            ):
                if name not in results:
                    record(results, name, False, f"HTTP server/request error: {error}")
        finally:
            stop_server(http_process)

        https_port = free_port()
        https_process = None
        try:
            cert = Path(tmp) / "server-cert.pem"
            key = Path(tmp) / "server-key.pem"
            combined = Path(tmp) / "server.pem"
            subprocess.run(
                [openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-sha256",
                 "-days", "1", "-keyout", str(key), "-out", str(cert),
                 "-subj", "/CN=localhost"],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=30,
            )
            combined.write_bytes(cert.read_bytes() + key.read_bytes())
            https_process = start_server(binary, str(root), https_port, str(combined))
            tls_context = ssl._create_unverified_context()
            https_status, _headers, https_body = request(
                https_port, "/index.bin", tls_context=tls_context
            )
            record(results, "A9_https_status_200", https_status == 200,
                   f"status={https_status}")
            record(results, "A10_https_exact_body", https_body == PAYLOAD,
                   f"received={len(https_body)} bytes, expected={len(PAYLOAD)}")
        except Exception as error:
            if "A9_https_status_200" not in results:
                record(results, "A9_https_status_200", False, str(error))
            if "A10_https_exact_body" not in results:
                record(results, "A10_https_exact_body", False, str(error))
        finally:
            stop_server(https_process)

    passed = sum(results.values())
    failed = len(results) - passed
    ok = failed == 0 and len(results) == 10
    sys.stdout.write(f"webfsd consumer checks: {passed}/{len(results)} passed; {failed} failed\n")
    marker = {"executed": True, "passed": ok, "command": "python3 test_webfs.py", "discovered": 10, "passedCount": passed}
    sys.stdout.write("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker) + "\n")
    sys.stdout.flush()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
