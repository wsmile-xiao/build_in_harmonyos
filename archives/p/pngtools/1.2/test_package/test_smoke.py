#!/usr/bin/env python3
"""Consumer smoke test for the installed pngtools programs."""

import os
import struct
import subprocess
import sys
import tempfile
import zlib


def chunk(kind, payload):
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    )


def write_png(path):
    width = height = 1
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    scanline = b"\x00\xff\x00\x00"
    payload = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(scanline))
        + chunk(b"IEND", b"")
    )
    with open(path, "wb") as handle:
        handle.write(payload)


def run(args, stdin=None):
    return subprocess.run(
        args,
        input=stdin,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_smoke.py <bin-dir>")

    bindir = sys.argv[1]
    tools = {
        name: os.path.join(bindir, name)
        for name in ("pnginfo", "pngchunks", "pngchunkdesc", "pngcp")
    }
    for name, path in tools.items():
        if not os.path.isfile(path):
            raise AssertionError("missing installed tool: %s" % name)

    checks = 0
    with tempfile.TemporaryDirectory(prefix="pngtools-smoke-") as tmp:
        source_png = os.path.join(tmp, "source.png")
        copied_png = os.path.join(tmp, "copied.png")
        invalid_file = os.path.join(tmp, "invalid.txt")
        write_png(source_png)
        with open(invalid_file, "w", encoding="ascii") as handle:
            handle.write("not a png\n")

        result = run([tools["pnginfo"], source_png])
        assert result.returncode == 0, result.stderr
        assert "Image Width: 1" in result.stdout
        checks += 2

        result = run([tools["pngchunks"], source_png])
        assert result.returncode == 0, result.stderr
        assert "[IHDR]" in result.stdout
        assert "[IEND]" in result.stdout
        checks += 3

        result = run([tools["pngchunkdesc"]], stdin="IHDR")
        assert result.returncode == 0, result.stderr
        assert "Critical" in result.stdout
        checks += 2

        result = run([tools["pngcp"], source_png, copied_png])
        assert result.returncode == 0, result.stderr
        assert os.path.isfile(copied_png)
        copied = run([tools["pnginfo"], copied_png])
        assert copied.returncode == 0, copied.stderr
        assert "Image Width: 1" in copied.stdout
        checks += 3

        result = run([tools["pnginfo"], invalid_file])
        assert result.returncode != 0
        checks += 1

    print("TEST_PACKAGE_RESULT total=%d passed=%d failed=0" % (checks, checks))


if __name__ == "__main__":
    main()
