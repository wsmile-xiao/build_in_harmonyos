#!/usr/bin/env python3
"""test_airthings.py — consumer test source for airthings-cloud 0.3.0 (L0c).

REAL API check (R34): construct the packaged Airthings client with an
aiohttp ClientSession (no network needed — construction proves the API
surface works and aiohttp (the published dependency) is importable).
Usage: test_airthings.py <site-packages-dir>
"""
import os
import sys


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_airthings.py <site-packages-dir>")
    sp = sys.argv[1]
    if not os.path.isdir(os.path.join(sp, "airthings")):
        raise AssertionError(f"airthings missing under {sp}")
    sys.path.insert(0, sp)
    import aiohttp  # dependency must be importable (PYTHONPATH injection)
    from airthings import Airthings
    async def build():
        async with aiohttp.ClientSession() as session:
            client = Airthings("test-client-id", "test-secret", session)
            assert client is not None
    import asyncio
    asyncio.get_event_loop().run_until_complete(build())
    print("OK: airthings-cloud 0.3.0 real API ok (Airthings client construct)")


if __name__ == "__main__":
    main()
