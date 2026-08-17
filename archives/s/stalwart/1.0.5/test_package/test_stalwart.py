#!/usr/bin/env python3
"""Exercise the packaged CLI against a localhost-only mock JMAP service."""
import base64
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

EXPECTED_AUTH = "Basic " + base64.b64encode(b"admin:secret").decode("ascii")
SCHEMA = {
    "objects": {
        "x:Account": {
            "type": "object",
            "description": "User account",
            "permissionPrefix": "account",
        },
        "x:Domain": {
            "type": "object",
            "description": "Mail domain",
            "permissionPrefix": "domain",
        },
    },
    "schemas": {},
    "fields": {},
    "forms": {},
    "lists": {},
    "enums": {},
    "dashboards": [],
    "layouts": [],
}


class Handler(BaseHTTPRequestHandler):
    requests = []

    def log_message(self, _format, *_args):
        pass

    def do_GET(self):
        type(self).requests.append((self.path, self.headers.get("Authorization")))
        if self.headers.get("Authorization") != EXPECTED_AUTH:
            self.send_error(401)
            return
        if self.path == "/api/schema":
            self.send_json(SCHEMA)
        elif self.path == "/jmap/session":
            self.send_json(
                {
                    "capabilities": {
                        "urn:ietf:params:jmap:core": {
                            "maxObjectsInGet": 64,
                            "maxObjectsInSet": 64,
                        }
                    },
                    "apiUrl": "/jmap",
                }
            )
        else:
            self.send_error(404)

    def send_json(self, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(command, env, expect=0):
    result = subprocess.run(
        command,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    if result.returncode != expect:
        raise RuntimeError(
            f"command {command!r} returned {result.returncode}, expected {expect}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_stalwart.py <stalwart-cli>")
    executable = pathlib.Path(sys.argv[1])
    if not executable.is_file():
        raise RuntimeError(f"missing executable: {executable}")

    with tempfile.TemporaryDirectory(prefix="stalwart-test-") as home:
        env = os.environ.copy()
        env.update({"HOME": home, "NO_COLOR": "1"})

        version = run([str(executable), "--version"], env).stdout.strip()
        assert version == "stalwart-cli 1.0.5", version
        help_text = run([str(executable), "--help"], env).stdout
        for text in ("Stalwart Command Line Interface", "describe", "snapshot"):
            assert text in help_text, text

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}"
        try:
            args = [
                str(executable), "--url", url, "--user", "admin",
                "--password", "secret", "--no-color", "describe",
            ]
            described = run(args, env)
            assert "Account" in described.stdout
            assert "Domain" in described.stdout
            assert ("/api/schema", EXPECTED_AUTH) in Handler.requests
            assert ("/jmap/session", EXPECTED_AUTH) in Handler.requests

            bad = run(
                [
                    str(executable), "--url", url, "--user", "admin",
                    "--password", "wrong", "--no-color", "describe",
                ],
                env,
                expect=1,
            )
            assert "authentication failed" in bad.stderr.lower(), bad.stderr
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    print("stalwart test_package: 9/9 assertions PASS")


if __name__ == "__main__":
    main()
