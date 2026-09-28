#!/usr/bin/env python3
"""Exercise the packaged tornado wheel from a consumer's point of view.

Run by test_package/conanfile.py with the Conan run environment applied, so
``tornado`` resolves to the package payload via PYTHONPATH.  Verifies:

1. the module comes from the Conan package (not a stray environment copy);
2. the version matches the recipe;
3. the async primitives really work end to end — an in-process HTTPServer is
   served and fetched over loopback with AsyncHTTPClient;
4. the optional ``speedups`` C accelerator state is reported honestly
   (upstream builds it with optional=True, so absence is a supported
   pure-Python fallback).
"""
import os
from pathlib import Path

import tornado
import tornado.httpclient
import tornado.ioloop
import tornado.web

# 1) The import must resolve into the Conan package payload.
expected_root = Path(os.environ["TORNADO_PACKAGE_ROOT"]).resolve()
module_path = Path(tornado.__file__).resolve()
assert expected_root in module_path.parents, (expected_root, module_path)

# 2) Exact version from the recipe.
assert tornado.version == "6.5.2", tornado.version


class Handler(tornado.web.RequestHandler):
    def get(self):
        self.write("ohos-ok")


# 3) Real event-loop round trip over the loopback interface.
app = tornado.web.Application([("/", Handler)])
server = app.listen(0, address="127.0.0.1")
port = list(server._sockets.values())[0].getsockname()[1]


async def main():
    client = tornado.httpclient.AsyncHTTPClient()
    resp = await client.fetch("http://127.0.0.1:%d/" % port)
    assert resp.body == b"ohos-ok", resp.body
    server.stop()


tornado.ioloop.IOLoop.current().run_sync(main)

# 4) Optional accelerator: report, never fail.
try:
    import tornado.speedups  # noqa: F401
    print("speedups: present")
except ImportError:
    print("speedups: absent (pure-python fallback)")

print("TORNADO-CONSUMER-OK")
