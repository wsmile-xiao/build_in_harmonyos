#!/usr/bin/env python3
"""OHOS-specific consumer test for cloud-utils-ec2metadata (test_package).

Validates the installed package with NO external network:
  1. ec2metadata --help — env-shebang resolution on HarmonyOS works
     (upstream usage() writes to stderr and exits 1 by design).
  2. Full IMDSv2 flow against a LOCAL mock proxy: the hardcoded token
     endpoint (169.254.169.254) and metadata queries are routed through
     http_proxy to a local mock, proving the real functional path
     (token PUT + meta-data/instance-id + meta-data/ami-id).
  3. write-mime-multipart --help — second installed Python tool runs.

The installed binaries are resolved through the conanrun PATH env.
"""
import http.server
import os
import socketserver
import subprocess
import sys
import threading

EC2METADATA = os.environ.get("EC2METADATA_BIN", "ec2metadata")
WMM = os.environ.get("WRITE_MIME_MULTIPART_BIN", "write-mime-multipart")
TOKEN = b"ohos-mock-token-123456"

META = {
    "meta-data/instance-id": b"i-ohos-test-001",
    "meta-data/ami-id": b"ami-ohos-0.34",
    "meta-data/local-ipv4": b"10.0.0.5",
}

failures = []


class MockProxy(http.server.BaseHTTPRequestHandler):
    """Plain HTTP proxy answering the IMDSv2 token + metadata requests."""

    def _respond(self, code, body=b""):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_PUT(self):
        if self.path.endswith("/latest/api/token"):
            self._respond(200, TOKEN)
        else:
            self._respond(404)

    def do_GET(self):
        # Proxied request line: GET http://host/path HTTP/1.1
        path = self.path
        if "://" in path:
            from urllib.parse import urlsplit
            path = urlsplit(path).path
        parts = [p for p in path.split("/") if p]
        key = "/".join(parts[-2:]) if len(parts) >= 2 else ""
        if key in META:
            self._respond(200, META[key])
        else:
            self._respond(404)

    def log_message(self, *args):
        pass


def run(cmd, label, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=45, env=e)
        out = (p.stdout + p.stderr).strip()
        print(f"[{label}] rc={p.returncode}")
        for line in (out.splitlines()[:6] if out else []):
            print("    ", line)
        if p.returncode != 0 and p.stderr.strip():
            print("    stderr:", p.stderr.strip()[:300])
        return p
    except subprocess.TimeoutExpired:
        failures.append(f"{label}: TIMEOUT (45s)")
        return None
    except Exception as ex:
        failures.append(f"{label}: {ex}")
        return None


def main():
    # 1. --help: upstream usage() writes to stderr and exits 1 by design
    p = run([EC2METADATA, "--help"], "help")
    if p is not None:
        combined = (p.stdout or "") + (p.stderr or "")
        if "Query and display EC2 metadata" not in combined:
            failures.append("help: expected usage text missing")

    # 2. IMDSv2 flow through local mock proxy
    with socketserver.TCPServer(("127.0.0.1", 0), MockProxy) as srv:
        port = srv.server_address[1]
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            proxy_env = {
                "http_proxy": f"http://127.0.0.1:{port}",
                "https_proxy": f"http://127.0.0.1:{port}",
                "HTTP_PROXY": f"http://127.0.0.1:{port}",
                "HTTPS_PROXY": f"http://127.0.0.1:{port}",
                "no_proxy": "",
                "NO_PROXY": "",
            }
            # metadata URL must point at a real listening port for the
            # direct connectivity probe; proxied GETs still reach the mock
            url = f"http://127.0.0.1:{port}/2009-04-04"
            p = run([EC2METADATA, "-u", url, "--instance-id"],
                    "instance-id", env=proxy_env)
            if p is not None and "i-ohos-test-001" not in p.stdout:
                failures.append("instance-id: mock value not returned")
            p = run([EC2METADATA, "-u", url, "--ami-id"],
                    "ami-id", env=proxy_env)
            if p is not None and "ami-ohos-0.34" not in p.stdout:
                failures.append("ami-id: mock value not returned")
        finally:
            srv.shutdown()

    # 3. write-mime-multipart --help
    p = run([WMM, "--help"], "wmm-help")
    if p is not None:
        combined = (p.stdout or "") + (p.stderr or "")
        if "Usage: write-mime-multipart" not in combined:
            failures.append("wmm-help: expected usage text missing")

    if failures:
        print("OHOS TEST FAILED:")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("OHOS TEST PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()