#!/usr/bin/env python3
"""Deterministic loopback MSVA used by the libmsv integration test."""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def _reply(self, payload):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._reply({"protoversion": 1, "available": True})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length).decode("utf-8"))
        valid = bool(request.get("peer") and request.get("pkc"))
        self._reply({"valid": valid, "message": "deterministic MSVA reply"})

    def log_message(self, format_string, *args):
        del format_string, args


def main():
    server = HTTPServer(("127.0.0.1", 0), Handler)
    with open(sys.argv[1], "w", encoding="utf-8") as stream:
        stream.write(str(server.server_port))
    server.serve_forever()


if __name__ == "__main__":
    main()
