#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Loopback stand-in for the containers restclient-cpp's own suite expects.

Upstream runs its 51 gtest cases against two containers that CI cannot provide
(``make docker-services`` in Makefile.am): ``kennethreitz/httpbin`` on
127.0.0.1:8998 and ``sameersbn/squid`` on 127.0.0.1:3128, plus the public
``https://httpbin.org`` used by the ``ConnectionTestRemote`` fixture.

This module serves exactly the endpoint subset those cases read, from
single-file Python standard library code, on the same ports:

  http   127.0.0.1:8998  httpbin subset (GET/POST/PUT/PATCH/DELETE/OPTIONS/HEAD)
  https  127.0.0.1:8999  same subset over TLS with the localhost-only test
                         certificate next to this module (peer verification
                         stays *on*)
  proxy  127.0.0.1:3128  forward proxy, CONNECT only -- enough to tunnel the
                         TLS requests the proxy cases make

Endpoints implemented (matching httpbin's response contract, which the cases
assert on literally):

  ANY  /get|/post|/put|/patch|/delete|/options   echo: args/headers/origin/url
  ANY  /anything[/<tail>]                        same echo
  GET  /headers                                  {"headers": {...}}
  GET  /basic-auth/<user>/<pass>                 401 + WWW-Authenticate, then
                                                 200 {"authenticated","user"}
  GET  /redirect/<n>                             n chained 302 hops then 200
  GET  /delay/<s>                                sleeps s then echo
  GET  /status/<code>                            bare status

Contract details the suite depends on, and that are therefore reproduced
rather than approximated:

* body is pretty-printed JSON **ending in a newline** -- TestSetWriteFunction
  compares ``bytes_of_last_chunk`` against the line-reassembled body, which
  only balances when every line, including the last, is newline-terminated;
* ``Connection: keep-alive`` is always present -- six cases assert on it;
* request header names are canonicalized the way Go's net/http does it
  (``foo`` -> ``Foo``) -- TestSetHeaders sends ``foo`` and asserts on
  ``root["headers"]["Foo"]``;
* ``HEAD`` answers with headers and **no body** -- TestRestClientHeadCode and
  TestHeadHeaders both assert an empty body on a keep-alive connection;
* ``url`` is rebuilt from the raw request target and the ``Host`` header, so
  ``TestRestClientGETBodyCode``'s equality against ``TestUrl + "/get"`` holds
  (including through the proxy, where Host names the tunnel target).

Deliberately out of scope: anything the cases never request.
"""

import argparse
import json
import os
import re
import socket
import socketserver
import ssl
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler

HTTP_PORT = 8998
TLS_PORT = 8999
PROXY_PORT = 3128

ECHO_PATHS = r"^/(get|post|put|patch|delete|options)$"


def canonical_header_key(name):
    parts = name.split("-")
    return "-".join(part[:1].upper() + part[1:].lower() for part in parts)


class HttpbinHandler(BaseHTTPRequestHandler):
    """One handler class serves both the plain and the TLS listener.

    ``tls`` is set on the TLS server subclass below; the plain listener keeps
    it False so ``url`` and the scheme stay correct on each endpoint.
    """

    protocol_version = "HTTP/1.1"
    tls = False

    def log_message(self, fmt, *args):
        pass

    # ---- plumbing -------------------------------------------------------

    def _scheme(self):
        return "https" if self.tls else "http"

    def _absolute_url(self, raw_path):
        host = self.headers.get("Host") or "%s:%d" % self.server.server_address[:2]
        return "%s://%s%s" % (self._scheme(), host, raw_path)

    def _read_body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0 or self.command == "HEAD":
            return ""
        return self.rfile.read(length).decode("utf-8", "replace")

    def _respond(self, code, payload=None, extra_headers=None):
        raw = b""
        if payload is not None:
            raw = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Connection", "keep-alive")
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        # A HEAD response declares Content-Length but must not carry a body;
        # appending one would desync the keep-alive connection curl reuses.
        if raw and self.command != "HEAD":
            self.wfile.write(raw)

    def _echo_headers(self):
        # httpbin answers through Go's net/http, which canonicalizes header
        # names on ingest: "foo" comes back as "Foo".  Upstream assertions key
        # on that spelling, so echoing the raw case fails them.
        return {canonical_header_key(name): value for name, value in self.headers.items()}

    def _echo(self, code=200):
        query = urllib.parse.urlparse(self.path).query
        args = {k: v[-1] for k, v in urllib.parse.parse_qs(query).items()}
        payload = {
            "args": args,
            "headers": self._echo_headers(),
            "origin": "%s:%d" % self.client_address[:2],
            "url": self._absolute_url(self.path),
        }
        body = self._read_body()
        if body:
            try:
                payload["json"] = json.loads(body)
            except ValueError:
                payload["data"] = body
        self._respond(code, payload)

    # ---- routes ---------------------------------------------------------

    def _basic_auth(self, user, expected):
        supplied = self._credentials()
        if supplied == (user, expected):
            self._respond(200, {"authenticated": True, "user": user})
        else:
            self._respond(401, {}, {"WWW-Authenticate": 'Basic realm="Restricted"'})

    def _credentials(self):
        header = self.headers.get("Authorization", "")
        if not header.startswith("Basic "):
            return None
        import base64
        try:
            user, _, password = base64.b64decode(header[6:]).decode("utf-8").partition(":")
        except Exception:
            return None
        return (user, password)

    def _redirect(self, remaining):
        if remaining <= 0:
            self._echo()
            return
        self._respond(302, {}, {"Location": "/redirect/%d" % (remaining - 1)})

    def _route(self):
        path = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)

        match = re.match(r"^/basic-auth/([^/]+)/([^/]+)$", path)
        if match:
            self._basic_auth(match.group(1), match.group(2))
            return
        match = re.match(r"^/redirect/(\d+)$", path)
        if match:
            self._redirect(int(match.group(1)))
            return
        match = re.match(r"^/delay/(\d+)$", path)
        if match:
            time.sleep(min(int(match.group(1)), self.server.max_delay))
            self._echo()
            return
        match = re.match(r"^/status/(\d{3})$", path)
        if match:
            self._respond(int(match.group(1)), None)
            return
        if path.startswith("/headers"):
            self._respond(200, {"headers": self._echo_headers()})
            return
        if path.startswith("/anything") or re.match(ECHO_PATHS, path):
            self._echo()
            return
        self._respond(404, {"error": "not implemented by the loopback stand-in: %s" % path})

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = _route
    do_HEAD = _route


class ProxyHandler(BaseHTTPRequestHandler):
    """Minimal CONNECT tunnel: enough for curl's https-over-proxy cases."""

    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    def _refuse(self, code, reason):
        self.send_response(code, reason)
        self.send_header("Content-Length", "0")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True

    def do_CONNECT(self):
        host, _, port = self.path.rpartition(":")
        if not host or not port.isdigit():
            self._refuse(400, "Bad Request")
            return
        try:
            upstream = socket.create_connection((host, int(port)), timeout=10)
        except OSError:
            self._refuse(502, "Bad Gateway")
            return
        self.send_response(200, "Connection Established")
        self.send_header("Content-Length", "0")
        self.end_headers()
        self.wfile.flush()
        self._tunnel(upstream)
        self.close_connection = True

    def _pump(self, source, target, done):
        try:
            while not done.is_set():
                chunk = source.recv(65536)
                if not chunk:
                    break
                target.sendall(chunk)
        except OSError:
            pass
        finally:
            done.set()
            for sock in (source, target):
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

    def _tunnel(self, upstream):
        done = threading.Event()
        raw_client = self.connection
        back = threading.Thread(target=self._pump, args=(upstream, raw_client, done), daemon=True)
        back.start()
        self._pump(raw_client, upstream, done)
        back.join(timeout=5)
        upstream.close()

    def do_GET(self):
        self._refuse(501, "Only CONNECT is implemented by this test proxy")

    do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_HEAD = do_GET


class LoopbackServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def build_http_server(port, host, max_delay):
    server = LoopbackServer((host, port), HttpbinHandler)
    server.max_delay = max_delay
    return server


def build_tls_server(port, host, max_delay, certfile, keyfile):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=certfile, keyfile=keyfile)

    class TLSHttpbinHandler(HttpbinHandler):
        tls = True

    class TLSLoopbackServer(LoopbackServer):
        def get_request(self):
            conn, addr = self.socket.accept()
            return context.wrap_socket(conn, server_side=True), addr

    server = TLSLoopbackServer((host, port), TLSHttpbinHandler)
    server.max_delay = max_delay
    return server


def build_proxy_server(port, host):
    return LoopbackServer((host, port), ProxyHandler)


def serve_all(http_port=HTTP_PORT, tls_port=TLS_PORT, proxy_port=PROXY_PORT,
              host="127.0.0.1", max_delay=10, certfile=None, keyfile=None,
              ready_file=None, tls=True):
    here = os.path.dirname(os.path.abspath(__file__))
    certfile = certfile or os.path.join(here, "localhost-test-only.crt")
    keyfile = keyfile or os.path.join(here, "localhost-test-only.key")
    if tls and not (os.path.isfile(certfile) and os.path.isfile(keyfile)):
        raise RuntimeError("TLS listener requested but %s / %s are missing" % (certfile, keyfile))

    servers = [build_http_server(http_port, host, max_delay)]
    endpoints = ["http=%s:%d" % (host, http_port)]
    if tls:
        servers.append(build_tls_server(tls_port, host, max_delay, certfile, keyfile))
        endpoints.append("https=%s:%d" % (host, tls_port))
    servers.append(build_proxy_server(proxy_port, host))
    endpoints.append("proxy=%s:%d" % (host, proxy_port))

    for server in servers:
        threading.Thread(target=server.serve_forever, daemon=True).start()

    line = "READY " + " ".join(endpoints)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()
    if ready_file:
        with open(ready_file, "w", encoding="utf-8") as handle:
            handle.write(line + "\n")
    return servers


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--http-port", type=int, default=HTTP_PORT)
    parser.add_argument("--tls-port", type=int, default=TLS_PORT)
    parser.add_argument("--proxy-port", type=int, default=PROXY_PORT)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--max-delay", type=int, default=10)
    parser.add_argument("--ready-file", default="")
    parser.add_argument("--no-tls", dest="tls", action="store_false",
                        help="skip the TLS listener (probing only; the Remote "
                             "fixture cases need it and will fail without it)")
    args = parser.parse_args(argv)

    serve_all(args.http_port, args.tls_port, args.proxy_port, args.host,
              args.max_delay, ready_file=args.ready_file or None, tls=args.tls)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
