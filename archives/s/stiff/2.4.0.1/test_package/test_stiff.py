#!/usr/bin/env python3
"""Generate a tiny FITS image and verify a real STIFF conversion."""
import os
import subprocess
import sys
import tempfile


def card(text):
    return text.ljust(80).encode("ascii")


binary = sys.argv[1]
version = subprocess.run(
    [binary, "-v"], check=True, text=True, capture_output=True
).stdout
if "version 2.4.0" not in version:
    raise SystemExit("unexpected STIFF version output")

with tempfile.TemporaryDirectory() as tmp:
    config = os.path.join(tmp, "stiff.conf")
    fits = os.path.join(tmp, "input.fits")
    output = os.path.join(tmp, "output.tif")

    defaults = subprocess.run(
        [binary, "-d"], check=True, text=True, capture_output=True
    ).stdout
    with open(config, "w", encoding="ascii") as stream:
        stream.write(defaults)

    header = b"".join(
        [
            card("SIMPLE  =                    T"),
            card("BITPIX  =                    8"),
            card("NAXIS   =                    2"),
            card("NAXIS1  =                    2"),
            card("NAXIS2  =                    2"),
            card("END"),
        ]
    )
    header += b" " * ((2880 - len(header) % 2880) % 2880)
    data = bytes([0, 85, 170, 255])
    data += b"\0" * ((2880 - len(data) % 2880) % 2880)
    with open(fits, "wb") as stream:
        stream.write(header + data)

    subprocess.run(
        [
            binary,
            "-c",
            config,
            fits,
            "-OUTFILE_NAME",
            output,
            "-WRITE_XML",
            "N",
        ],
        check=True,
        cwd=tmp,
    )
    with open(output, "rb") as stream:
        signature = stream.read(4)
    if signature not in (b"II*\0", b"MM\0*"):
        raise SystemExit("STIFF did not produce a valid TIFF signature")
