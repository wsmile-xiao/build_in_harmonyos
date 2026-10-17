#!/usr/bin/env python3
"""Validate the already-applied GCC HarmonyOS source patch."""

import sys
from pathlib import Path


def prepare(source, ohos_header):
    source = Path(source)
    ohos_header = Path(ohos_header)
    patched_header = source / "gcc" / "config" / "ohos.h"
    if not patched_header.is_file():
        raise RuntimeError(
            "GCC HarmonyOS patch did not install {}".format(patched_header)
        )
    if patched_header.read_bytes() != ohos_header.read_bytes():
        raise RuntimeError(
            "GCC HarmonyOS header differs from the exported patch input"
        )


def main():
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: prepare_ohos_sources.py SOURCE_FOLDER OHOS_HEADER"
        )
    prepare(Path(sys.argv[1]), Path(sys.argv[2]))


if __name__ == "__main__":
    main()
