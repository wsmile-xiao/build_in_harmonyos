#!/usr/bin/env python3
"""Deterministic consumer checks for the packaged pyfavicon API."""

import asyncio
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import tempfile
import threading

import pyfavicon
from pyfavicon import Favicon, FaviconType, Icons, parse_base64_icon


PNG_1X1 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0l"
    "EQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)
DATA_URI = "data:image/png;base64," + PNG_1X1
checks = 0


def check(condition, message):
    global checks
    if not condition:
        raise AssertionError(message)
    checks += 1


class FixtureHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        raw_png = base64.b64decode(PNG_1X1)
        if self.path in {"/favicon.ico", "/apple.png", "/tile.png"}:
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(raw_png)))
            self.end_headers()
            self.wfile.write(raw_png)
            return
        self.send_error(404)

    def log_message(self, format, *args):
        return


async def main():
    raw_png = base64.b64decode(PNG_1X1)
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    tmpdir = Path(tempfile.mkdtemp(prefix="pyfavicon-test-"))
    try:
        base_url = f"http://127.0.0.1:{server.server_port}/docs/index.html"
        manager = Favicon(download_dir=tmpdir, headers={"DNT": "1"})
        html = (
            "<html><head>"
            f"<link rel='icon' href='{DATA_URI}'>"
            "<link rel='shortcut icon' href='../favicon.ico'>"
            "<link rel='apple-touch-icon' href='/apple.png'>"
            "<meta name='msapplication-TileImage' content='/tile.png'>"
            f"<link rel='icon' href='{DATA_URI}'>"
            "</head></html>"
        )

        icons = await manager.from_html(html, base_url)
        icon_list = list(icons)
        check(pyfavicon.__version__ == "0.1.1", "module exposes packaged version")
        check(parse_base64_icon(DATA_URI) == raw_png, "decodes base64 data icon")
        check(len(icon_list) == 4, "discovers four unique favicon sources")

        data_icon = icon_list[0]
        check(data_icon.type is FaviconType.DATA, "classifies data URI icon")
        check(data_icon.size == (1, 1), "parses PNG dimensions without Pillow")
        check(data_icon.extension == "png", "parses PNG extension without Pillow")

        relative_icon = icon_list[1]
        check(relative_icon.type is FaviconType.URL, "classifies URL icon")
        expected_url = f"http://127.0.0.1:{server.server_port}/favicon.ico"
        check(str(relative_icon.link) == expected_url, "resolves relative favicon URL")
        check(relative_icon.size == (1, 1), "parses URL icon dimensions through stdlib HTTP")

        largest = icons.get_largest("png")
        check(largest is data_icon, "selects largest PNG icon")
        await data_icon.save()
        check(Path(data_icon.path).is_file(), "saves data icon to download directory")
        check(Path(data_icon.path).read_bytes() == raw_png, "saved data icon bytes match source")

        html_file = tmpdir / "index.html"
        html_file.write_text(f'<link rel="icon" href="{DATA_URI}">', encoding="utf-8")
        from_file_icons = await manager.from_file(html_file, base_url)
        check(len(list(from_file_icons)) == 1, "loads favicon links from an HTML file")

        empty_icons = Icons()
        check(empty_icons.get_largest() is None, "empty icon collection returns no largest icon")
    finally:
        server.shutdown()
        server.server_close()
        shutil.rmtree(tmpdir, ignore_errors=True)


asyncio.run(main())

expected_checks = 14
if checks != expected_checks:
    raise AssertionError(
        f"consumer assertion count mismatch: expected {expected_checks}, got {checks}"
    )
print(f"PASS: pyfavicon packaged API consumer test ({checks}/{expected_checks} assertions)")
