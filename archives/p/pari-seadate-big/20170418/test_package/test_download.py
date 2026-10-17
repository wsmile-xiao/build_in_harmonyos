#!/usr/bin/env python3
"""Host regression tests for the recipe's bounded HTTP range downloader."""

import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
from pathlib import Path
import re
import tempfile
import threading
import time
import unittest


spec = importlib.util.spec_from_file_location("pari_recipe", Path(__file__).resolve().parents[1] / "conanfile.py")
recipe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recipe)
DATA = bytes(range(256)) * 32 + b"last short range"
SHA256 = hashlib.sha256(DATA).hexdigest()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        match = re.fullmatch(r"bytes=(\d+)-(\d+)", self.headers.get("Range", ""))
        if not match:
            self.send_error(400)
            return
        start, end = map(int, match.groups())
        server = self.server
        with server.lock:
            count = server.requests.get(start, 0) + 1
            server.requests[start] = count
            server.active += 1
            server.peak = max(server.peak, server.active)
        try:
            time.sleep(0.015)
            if server.mode == "retry" and count == 1:
                self.send_error(503)
                return
            self.send_response(200 if server.mode == "ignored" else 206)
            actual_start = start + 1 if server.mode == "wrong_range" else start
            self.send_header("Content-Range", f"bytes {actual_start}-{end}/{len(DATA)}")
            self.send_header("Content-Length", str(end - start + 1))
            self.end_headers()
            body = DATA[start:end + 1]
            if server.mode == "corrupt":
                body = bytes([body[0] ^ 1]) + body[1:]
            if server.mode == "short":
                body = body[:-1]
            try:
                if server.mode == "slow":
                    for position in range(0, len(body), 16):
                        self.wfile.write(body[position:position + 16])
                        self.wfile.flush()
                        time.sleep(0.03)
                else:
                    self.wfile.write(body)
            except OSError:
                pass
        finally:
            with server.lock:
                server.active -= 1


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.destination = Path(self.temporary.name) / "archive.tar"
        self.destination.write_bytes(b"existing verified file")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.mode = "valid"
        self.server.requests = {}
        self.server.lock = threading.Lock()
        self.server.active = self.server.peak = 0
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temporary.cleanup()

    def download(self, **kwargs):
        options = {"workers": 4, "part_size": 1024, "retries": 2, **kwargs}
        recipe.PariSeadateBigConan._download_parallel(
            f"http://127.0.0.1:{self.server.server_port}/archive.tar", self.destination,
            len(DATA), SHA256, **options)

    def assert_preserved(self):
        self.assertEqual(self.destination.read_bytes(), b"existing verified file")
        self.assertEqual(list(self.destination.parent.iterdir()), [self.destination])

    def test_complete_archive_uses_bounded_parallel_ranges(self):
        self.download()
        self.assertEqual(self.destination.read_bytes(), DATA)
        self.assertGreater(self.server.peak, 1)
        self.assertLessEqual(self.server.peak, 4)
        self.assertEqual(set(self.server.requests), set(range(0, len(DATA), 1024)))

    def test_transient_http_failure_retries_each_segment(self):
        self.server.mode = "retry"
        self.download()
        self.assertEqual(self.destination.read_bytes(), DATA)
        self.assertEqual(set(self.server.requests.values()), {2})

    def test_server_ignoring_range_is_rejected(self):
        self.server.mode = "ignored"
        with self.assertRaises(ValueError):
            self.download()
        self.assert_preserved()

    def test_wrong_content_range_is_rejected(self):
        self.server.mode = "wrong_range"
        with self.assertRaises(ValueError):
            self.download()
        self.assert_preserved()

    def test_truncated_response_retries_then_fails(self):
        self.server.mode = "short"
        with self.assertRaises(OSError):
            self.download()
        self.assertLessEqual(max(self.server.requests.values()), 2)
        self.assert_preserved()

    def test_corruption_fails_sha256_and_preserves_destination(self):
        self.server.mode = "corrupt"
        with self.assertRaisesRegex(ValueError, "SHA256"):
            self.download()
        self.assert_preserved()

    def test_download_budget_exhaustion_is_bounded(self):
        with self.assertRaises(TimeoutError):
            self.download(deadline_seconds=0)
        self.assertFalse(self.server.requests)
        self.assert_preserved()

    def test_slow_trickle_obeys_budget_during_transfer(self):
        self.server.mode = "slow"
        started = time.monotonic()
        with self.assertRaises(TimeoutError):
            self.download(workers=1, deadline_seconds=0.7)
        self.assertTrue(self.server.requests)
        self.assertLess(time.monotonic() - started, 1.5)
        self.assert_preserved()


if __name__ == "__main__":
    unittest.main()
