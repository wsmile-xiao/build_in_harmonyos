#!/usr/bin/env python3
"""async-timeout consumer test (L0c + R34): standalone test source
executed via self.run from conanfile.py test().

R34: actually call the tested API — async_timeout.timeout async
timeout context (pure user-space asyncio).

Usage: test_async_timeout.py <site-packages>
"""
import asyncio
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <site-packages>", file=sys.stderr)
        return 2
    site = sys.argv[1]
    if not os.path.isdir(os.path.join(site, "async_timeout")):
        raise AssertionError(f"async_timeout package missing in {site}")
    sys.path.insert(0, site)

    async def _run():
        from async_timeout import timeout
        async with timeout(5):
            await asyncio.sleep(0.01)
        return True

    if not asyncio.run(_run()):
        raise AssertionError("async_timeout.timeout failed")
    print("OK: async-timeout 5.0.1 (timeout context ok)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
