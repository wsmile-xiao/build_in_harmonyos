#!/usr/bin/env python3
"""Minimal package smoke test for a nemu package folder or archive."""
import os
import struct
import sys
import tarfile


REQUIRED = {
    "bin/nemu",
    "bin/ntty",
    "share/nemu/templates/config/nemu.cfg.sample",
    "share/locale/ru/LC_MESSAGES/nemu.mo",
}


def check_elf(data: bytes, name: str) -> None:
    if data[:4] != b"\x7fELF":
        raise ValueError(f"not an ELF executable: {name}")
    if len(data) < 20 or data[4] != 2 or data[5] != 1:
        raise ValueError(f"unexpected ELF class or endianness: {name}")
    if struct.unpack_from("<H", data, 18)[0] != 183:
        raise ValueError(f"unexpected ELF machine: {name}")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: smoke.py <package-folder-or-tar.gz>", file=sys.stderr)
        return 2

    package = os.path.abspath(sys.argv[1])
    try:
        if tarfile.is_tarfile(package):
            with tarfile.open(package, "r:*") as archive:
                members = {
                    member.name.lstrip("./"): member
                    for member in archive.getmembers()
                }
                missing = sorted(REQUIRED - members.keys())
                if missing:
                    raise ValueError(f"missing package files: {', '.join(missing)}")
                for name in ("bin/nemu",):
                    member = members[name]
                    if not member.isfile():
                        raise ValueError(f"package entry is not a regular file: {name}")
                    check_elf(archive.extractfile(member).read(20), name)
                script_member = members["bin/ntty"]
                if not script_member.isfile():
                    raise ValueError(
                        f"package entry is not a regular file: bin/ntty")
                script = archive.extractfile(script_member).read(128)
                if not script.startswith(b"#!/bin/sh\n"):
                    raise ValueError("bin/ntty is not a POSIX shell script")
        else:
            missing = sorted(
                path for path in REQUIRED
                if not os.path.isfile(os.path.join(package, path))
            )
            if missing:
                raise ValueError(f"missing package files: {', '.join(missing)}")
            for name in ("bin/nemu",):
                path = os.path.join(package, name)
                if not os.access(path, os.X_OK):
                    raise ValueError(f"package binary is not executable: {path}")
                with open(path, "rb") as stream:
                    check_elf(stream.read(20), name)
            with open(os.path.join(package, "bin", "ntty"), "rb") as stream:
                if not stream.read(128).startswith(b"#!/bin/sh\n"):
                    raise ValueError("bin/ntty is not a POSIX shell script")
    except (OSError, ValueError, tarfile.TarError) as error:
        print(f"nemu package smoke test: FAIL: {error}", file=sys.stderr)
        return 1

    print("nemu package smoke test: PASS (files, ELF headers, package layout)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
