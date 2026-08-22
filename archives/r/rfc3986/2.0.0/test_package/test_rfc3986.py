#!/usr/bin/env python3
"""rfc3986 consumer test (L0c + R34): standalone test source executed
via self.run from conanfile.py test().

R34: actually call the tested API — parse a URI with
rfc3986.uri_reference() and validate it (pure user-space).

Usage: test_rfc3986.py <site-packages>
"""
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <site-packages>", file=sys.stderr)
        return 2
    site = sys.argv[1]
    if not os.path.isdir(os.path.join(site, "rfc3986")):
        raise AssertionError(f"rfc3986 package missing in {site}")
    sys.path.insert(0, site)
    # R34: 真实调用被测库 API
    import rfc3986
    from rfc3986.validators import Validator

    uri = rfc3986.uri_reference("https://example.com/path?q=1#frag")
    if not (uri.scheme == "https" and uri.host == "example.com"):
        raise AssertionError(f"unexpected parse result: {uri}")
    if not uri.is_valid():
        raise AssertionError("uri_reference marked valid URI invalid")
    print(f"OK: rfc3986 {rfc3986.__version__} "
          f"(parse+validate ok: {uri.scheme}://{uri.host})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
