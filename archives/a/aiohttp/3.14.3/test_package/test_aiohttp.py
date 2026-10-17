#!/usr/bin/env python3
"""test_aiohttp.py — consumer test source for aiohttp 3.14.3 (L0c).

REAL API check (R34) on the packaged aiohttp (pure-Python fallback):
  aiohttp import + aiohttp.web.Application construction + route add +
  aiohttp.ClientSession creation (no web-server startup — avoids socket
  binding environment limits on OHOS).
Usage: test_aiohttp.py <site-packages-dir>
"""
import os
import sys


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_aiohttp.py <site-packages-dir>")
    site = sys.argv[1]
    if not os.path.isdir(os.path.join(site, "aiohttp")):
        raise AssertionError(f"aiohttp package dir missing under {site}")
    sys.path.insert(0, site)

    import asyncio
    import aiohttp

    async def check():
        from aiohttp import web

        # web.Application + route (real API, no server startup)
        app = web.Application()
        async def handler(request):
            return web.Response(text="ok")
        app.router.add_get("/", handler)
        if len(app.router.routes()) < 1:
            raise AssertionError("router route add failed")

        # ClientSession creation (real API)
        async with aiohttp.ClientSession() as session:
            if session is None:
                raise AssertionError("ClientSession creation failed")

    asyncio.run(check())
    print("OK: aiohttp 3.14.3 real API ok "
          "(web.Application/router/ClientSession)")


if __name__ == "__main__":
    main()
