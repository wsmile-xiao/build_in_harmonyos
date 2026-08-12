#!/usr/bin/env python3
"""Documented consumer scenarios executed by test_package/conanfile.py."""

SCENARIOS = (
    "packaged i2pd --version",
    "packaged i2pd --help",
    "reject an unknown configuration option",
)


if __name__ == "__main__":
    print("\n".join(SCENARIOS))
