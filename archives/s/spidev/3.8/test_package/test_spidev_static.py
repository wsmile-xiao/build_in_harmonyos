#!/usr/bin/env python3
"""Static OHOS artifact checks for the packaged spidev CPython extension."""
import os
import sys


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    require(len(sys.argv) == 2, "usage: test_spidev_static.py <extension.so>")
    path = sys.argv[1]
    require(os.path.isfile(path), "extension file is missing: {}".format(path))

    with open(path, "rb") as handle:
        data = handle.read()

    require(data.startswith(b"\x7fELF"), "extension is not an ELF shared object")
    require(b"PyInit_spidev" in data, "extension is missing PyInit_spidev")
    require(b".codesign" in data, "extension is missing the OHOS .codesign section")
    print("spidev OHOS extension artifact checks passed")


if __name__ == "__main__":
    main()
