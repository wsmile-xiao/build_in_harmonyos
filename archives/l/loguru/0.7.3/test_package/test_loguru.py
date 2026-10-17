#!/usr/bin/env python3
"""Conan test_package for loguru — R34 real API usage (no empty shell).

loguru is pure Python. The verifiable artifact is the loguru package under
<pkg>/lib/python3.12/site-packages/. This test imports the packaged loguru
and actually records a log message + reads it back via a sink — proving the
package is functional, not just present on disk.
"""
import os
import sys


def main():
    pkg = sys.argv[1]
    pyver = "python3.12"
    site = os.path.join(pkg, "lib", pyver, "site-packages")
    if not os.path.isdir(os.path.join(site, "loguru")):
        print(f"FAIL: loguru package dir not found under {site}",
              file=sys.stderr)
        return 1
    sys.path.insert(0, site)

    from loguru import logger

    # R34: record a real log message and capture it via a list sink.
    captured = []
    logger.remove()
    logger.add(captured.append, format="{message}")
    logger.info("hello from loguru")
    if not captured or "hello from loguru" not in captured[0]:
        print(f"FAIL: sink capture unexpected: {captured!r}",
              file=sys.stderr)
        return 1

    print(f"OK: loguru imported from package; captured={captured[0]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
