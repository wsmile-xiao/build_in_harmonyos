#!/usr/bin/env python3
"""Consumer integration tests for the installed Links text browser."""

from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Callable


REQUEST_PATHS: list[str] = []


class TestPageHandler(BaseHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        pass

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        REQUEST_PATHS.append(path)

        if path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/redirect-target")
            self.end_headers()
            return

        if path == "/page":
            status = 200
            body = (
                "<html><body><p>XLINKS_SUCCESS_MARKER &amp; "
                "XLINKS_ENTITY_MARKER</p></body></html>"
            )
        elif path == "/redirect-target":
            status = 200
            body = "<html><body><p>XLINKS_REDIRECT_TARGET_MARKER</p></body></html>"
        elif path == "/hidden":
            status = 200
            body = (
                "<html><body><p>XLINKS_VISIBLE_BEFORE</p>"
                "<script>XLINKS_HIDDEN_SCRIPT_MARKER</script>"
                "<style>.x { content: 'XLINKS_HIDDEN_STYLE_MARKER'; }</style>"
                "<p>XLINKS_VISIBLE_AFTER</p></body></html>"
            )
        elif path == "/not-found":
            status = 404
            body = "<html><body><p>XLINKS_404_BODY_MARKER</p></body></html>"
        else:
            status = 404
            body = "<html><body><p>XLINKS_UNEXPECTED_PATH</p></body></html>"

        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=UTF-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def resolve_links() -> Path:
    override = os.environ.get("XLINKS_BIN")
    candidate = Path(override) if override else None
    if candidate is None:
        found = shutil.which("links")
        candidate = Path(found) if found else None
    if candidate is None or not candidate.is_file():
        raise FileNotFoundError(f"links executable not found: {override or 'PATH'}")
    if os.name != "nt" and not os.access(candidate, os.X_OK):
        raise FileNotFoundError(f"links executable is not executable: {candidate}")
    return candidate.resolve()


def run_links(binary: Path, url: str, timeout: float = 10.0) -> subprocess.CompletedProcess[str]:
    bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
    if not Path(bash).is_file():
        raise RuntimeError(f"HarmonyOS bash is unavailable: {bash}")

    environment = os.environ.copy()
    environment["TERM"] = "dumb"
    environment["LC_ALL"] = "C"
    environment["COLUMNS"] = "120"
    return subprocess.run(
        [bash, "-c", 'exec "$1" -dump "$2"', "xlinks-test", str(binary), url],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        timeout=timeout,
        env=environment,
        check=False,
    )


def output_of(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_renders_loopback_html(binary: Path, base_url: str) -> None:
    result = run_links(binary, f"{base_url}/page")
    output = re.sub(r"\s+", " ", result.stdout)
    require(result.returncode == 0, f"links exited {result.returncode}: {output_of(result)}")
    require("XLINKS_SUCCESS_MARKER" in output, f"page text missing: {output}")
    require(
        "XLINKS_SUCCESS_MARKER & XLINKS_ENTITY_MARKER" in output,
        f"HTML entity was not rendered as '&': {output}",
    )


def test_follows_loopback_redirect(binary: Path, base_url: str) -> None:
    REQUEST_PATHS.clear()
    result = run_links(binary, f"{base_url}/redirect")
    output = output_of(result)
    require(result.returncode == 0, f"links exited {result.returncode}: {output}")
    require("/redirect-target" in REQUEST_PATHS, f"redirect target was not requested: {REQUEST_PATHS}")
    require("XLINKS_REDIRECT_TARGET_MARKER" in output, f"redirect target text missing: {output}")


def test_omits_script_and_style_text(binary: Path, base_url: str) -> None:
    result = run_links(binary, f"{base_url}/hidden")
    output = output_of(result)
    require(result.returncode == 0, f"links exited {result.returncode}: {output}")
    require("XLINKS_VISIBLE_BEFORE" in output, f"visible text before hidden content missing: {output}")
    require("XLINKS_VISIBLE_AFTER" in output, f"visible text after hidden content missing: {output}")
    require("XLINKS_HIDDEN_SCRIPT_MARKER" not in output, "script text leaked into rendered page")
    require("XLINKS_HIDDEN_STYLE_MARKER" not in output, "style text leaked into rendered page")


def test_renders_404_body_without_success_marker(binary: Path, base_url: str) -> None:
    result = run_links(binary, f"{base_url}/not-found")
    output = output_of(result)
    require("XLINKS_404_BODY_MARKER" in output, f"404 response body was not rendered: {output}")
    require("XLINKS_SUCCESS_MARKER" not in output, "404 request rendered the success-page marker")


def test_connection_failure_is_bounded(binary: Path) -> None:
    reservation = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    reservation.bind(("127.0.0.1", 0))
    port = reservation.getsockname()[1]
    reservation.close()

    started = time.monotonic()
    try:
        result = run_links(binary, f"http://127.0.0.1:{port}/unreachable", timeout=10.0)
    except subprocess.TimeoutExpired as exc:
        raise AssertionError("connection failure exceeded the 10-second timeout") from exc
    elapsed = time.monotonic() - started
    require(elapsed < 10.0, f"connection failure took {elapsed:.2f}s")
    print(f"[info] refused loopback connection completed in {elapsed:.2f}s (exit {result.returncode})")


def test_supports_long_version_option(binary: Path) -> None:
    result = subprocess.run(
        [str(binary), "--version"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        timeout=10.0,
        check=False,
    )
    output = output_of(result)
    require(result.returncode == 0, f"links --version exited {result.returncode}: {output}")
    require("Links 2.30" in output, f"unexpected version output: {output}")


def main() -> int:
    try:
        binary = resolve_links()
    except FileNotFoundError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    server = HTTPServer(("127.0.0.1", 0), TestPageHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    cases: list[tuple[str, Callable[..., None], bool]] = [
        ("test_renders_loopback_html", test_renders_loopback_html, True),
        ("test_follows_loopback_redirect", test_follows_loopback_redirect, True),
        ("test_omits_script_and_style_text", test_omits_script_and_style_text, True),
        ("test_renders_404_body_without_success_marker", test_renders_404_body_without_success_marker, True),
        ("test_connection_failure_is_bounded", test_connection_failure_is_bounded, False),
        ("test_supports_long_version_option", test_supports_long_version_option, False),
    ]
    failures = 0
    try:
        for name, case, needs_server in cases:
            try:
                if needs_server:
                    case(binary, base_url)
                else:
                    case(binary)
                print(f"PASS {name}")
            except Exception as exc:  # Report every behavior while still cleaning up the local server.
                failures += 1
                print(f"FAIL {name}: {exc}", file=sys.stderr)
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2.0)

    if failures:
        print(f"FAILED {failures}/{len(cases)} loopback behavior tests", file=sys.stderr)
        return 1
    print(f"PASS {len(cases)}/{len(cases)} loopback behavior tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
