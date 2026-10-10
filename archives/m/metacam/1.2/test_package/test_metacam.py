"""Black-box tests for the installed metacam, with no upstream test assets."""

import pathlib
import struct
import subprocess
import sys
import tempfile


def tiff_with_make():
    # Little-endian TIFF: one Make ASCII tag and no next IFD.
    return (
        b"II*\x00"
        + struct.pack("<I", 8)
        + struct.pack("<H", 1)
        + struct.pack("<HHII", 0x010F, 2, 6, 26)
        + struct.pack("<I", 0)
        + b"Canon\x00"
    )


def run(binary, *args):
    return subprocess.run([binary, *map(str, args)], capture_output=True, text=True)


def main(binary):
    help_result = run(binary, "--help")
    assert help_result.returncode == 0, help_result
    assert "Usage:" in help_result.stderr, help_result

    empty_result = run(binary)
    assert empty_result.returncode == 2, empty_result

    # CI's shared TMPDIR can be non-writable for this target application.
    with tempfile.TemporaryDirectory(
        prefix="metacam-test-", dir="/data/storage/el2/base/cache"
    ) as directory:
        root = pathlib.Path(directory)
        raw = root / "sample.tiff"
        raw.write_bytes(tiff_with_make())
        raw_result = run(binary, raw)
        assert raw_result.returncode == 0, raw_result
        assert "Canon" in raw_result.stdout, raw_result

        # EXIF deliberately begins after the first 1024-byte scan buffer.
        jpeg = root / "late-exif.jpg"
        jpeg.write_bytes(
            b"\xff\xd8" + b"\x00" * 1100 + b"Exif\x00\x00"
            + tiff_with_make() + b"\x00" * 1100
        )
        jpeg_result = run(binary, jpeg)
        assert jpeg_result.returncode == 0, jpeg_result
        assert "Canon" in jpeg_result.stdout, jpeg_result

        # A final partial scan sets both eofbit and failbit before TIFF seeks.
        short_jpeg = root / "short-exif.jpg"
        short_jpeg.write_bytes(b"\xff\xd8Exif\x00\x00" + tiff_with_make())
        short_result = run(binary, short_jpeg)
        assert short_result.returncode == 0, short_result
        assert "Canon" in short_result.stdout, short_result

        # The marker can straddle two 1024-byte scan buffers.
        split_jpeg = root / "split-exif.jpg"
        split_jpeg.write_bytes(
            b"\xff\xd8" + b"\x00" * 1022 + b"Ex" + b"if\x00\x00"
            + tiff_with_make()
        )
        split_result = run(binary, split_jpeg)
        assert split_result.returncode == 0, split_result
        assert "Canon" in split_result.stdout, split_result

    print("PASS: installed metacam reads TIFF, late, short and split JPEG EXIF")


if __name__ == "__main__":
    main(sys.argv[1])
