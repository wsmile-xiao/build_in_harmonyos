#!/usr/bin/env python3
"""Functional smoke tests for the packaged farbfeld executables."""
import os
import struct
import subprocess
import sys


def run_command(args, stdin_data=None):
    return subprocess.run(
        args, input=stdin_data,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


def create_farbfeld(width, height):
    """Create a minimal farbfeld image (16-bit RGBA)."""
    header = b"farbfeld"
    header += struct.pack(">I", width)
    header += struct.pack(">I", height)
    pixels = b"\xff\x00" * (width * height * 4)
    return header + pixels


def assert_ff2ppm(bin_dir):
    """Test ff2ppm: farbfeld -> PPM."""
    ff_data = create_farbfeld(2, 2)
    result = run_command([os.path.join(bin_dir, "ff2ppm")], stdin_data=ff_data)
    if result.returncode != 0:
        raise AssertionError(f"ff2ppm failed: {result.stderr.decode()}")
    if not result.stdout.startswith(b"P6\n"):
        raise AssertionError("ff2ppm output is not valid PPM (P6)")


def assert_ff2pam(bin_dir):
    """Test ff2pam: farbfeld -> PAM."""
    ff_data = create_farbfeld(2, 2)
    result = run_command([os.path.join(bin_dir, "ff2pam")], stdin_data=ff_data)
    if result.returncode != 0:
        raise AssertionError(f"ff2pam failed: {result.stderr.decode()}")
    if not result.stdout.startswith(b"P7\n"):
        raise AssertionError("ff2pam output is not valid PAM (P7)")


def assert_ff2png(bin_dir):
    """Test ff2png: farbfeld -> PNG."""
    ff_data = create_farbfeld(2, 2)
    result = run_command([os.path.join(bin_dir, "ff2png")], stdin_data=ff_data)
    if result.returncode != 0:
        raise AssertionError(f"ff2png failed: {result.stderr.decode()}")
    if not result.stdout.startswith(b"\x89PNG\r\n\x1a\n"):
        raise AssertionError("ff2png output is not valid PNG")


def assert_ff2jpg(bin_dir):
    """Test ff2jpg: farbfeld -> JPEG."""
    ff_data = create_farbfeld(2, 2)
    result = run_command([os.path.join(bin_dir, "ff2jpg")], stdin_data=ff_data)
    if result.returncode != 0:
        raise AssertionError(f"ff2jpg failed: {result.stderr.decode()}")
    if not result.stdout.startswith(b"\xff\xd8\xff"):
        raise AssertionError("ff2jpg output is not valid JPEG")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_farbfeld.py <bin_dir>")
    bin_dir = sys.argv[1]

    for name in ["ff2ppm", "ff2pam", "ff2png", "ff2jpg"]:
        binary = os.path.join(bin_dir, name)
        if not os.path.isfile(binary):
            raise AssertionError(f"binary not found: {binary}")

    assert_ff2ppm(bin_dir)
    assert_ff2pam(bin_dir)
    assert_ff2png(bin_dir)
    assert_ff2jpg(bin_dir)
    print("All farbfeld tests passed!")


if __name__ == "__main__":
    main()
