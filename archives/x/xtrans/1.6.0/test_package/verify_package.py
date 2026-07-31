#!/usr/bin/env python3
"""Validate the installed xtrans source and metadata contract."""

import sys
from pathlib import Path


EXPECTED_SOURCES = (
    "Xtrans.h",
    "Xtrans.c",
    "Xtransint.h",
    "Xtranslcl.c",
    "Xtranssock.c",
    "Xtransutil.c",
    "transport.c",
)


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def main():
    require(len(sys.argv) == 2, "usage: verify_package.py PACKAGE_FOLDER")
    package = Path(sys.argv[1])
    include_dir = package / "include" / "X11" / "Xtrans"
    missing_sources = [
        name for name in EXPECTED_SOURCES if not (include_dir / name).is_file()
    ]
    require(not missing_sources, f"missing xtrans sources: {missing_sources}")

    expected_files = (
        package / "share" / "aclocal" / "xtrans.m4",
        package / "share" / "pkgconfig" / "xtrans.pc",
        package / "share" / "xtrans" / "xtrans-defines.txt",
        package / "licenses" / "COPYING",
        package / "share" / "doc" / "xtrans" / "README.md",
        package / "share" / "doc" / "xtrans" / "xtrans.xml",
    )
    missing_files = [str(path) for path in expected_files if not path.is_file()]
    require(not missing_files, f"missing xtrans package files: {missing_files}")

    pc_path = package / "share" / "pkgconfig" / "xtrans.pc"
    pc_content = pc_path.read_text(encoding="utf-8")
    require("prefix=${pcfiledir}/../.." in pc_content, "xtrans.pc prefix is not relocatable")
    require("includedir=${prefix}/include" in pc_content, "xtrans.pc includedir is wrong")
    require("Name: XTrans" in pc_content, "xtrans.pc name is wrong")
    require("Version: 1.6.0" in pc_content, "xtrans.pc version is wrong")
    require("-D_DEFAULT_SOURCE" in pc_content, "xtrans.pc lacks _DEFAULT_SOURCE")
    require("-D_BSD_SOURCE" in pc_content, "xtrans.pc lacks _BSD_SOURCE")
    require("-DHAS_STICKY_DIR_BIT" in pc_content, "xtrans.pc lacks sticky-bit support")

    defines_path = package / "share" / "xtrans" / "xtrans-defines.txt"
    defines = set(defines_path.read_text(encoding="utf-8").splitlines())
    for required in ("_DEFAULT_SOURCE", "_BSD_SOURCE", "HAS_STICKY_DIR_BIT"):
        require(required in defines, f"missing packaged definition: {required}")
    require(
        ("HAS_FCHOWN" in defines) == ("-DHAS_FCHOWN" in pc_content),
        "fchown probe result differs between Conan and pkg-config metadata",
    )
    print("validated xtrans source inventory and relocatable metadata")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
