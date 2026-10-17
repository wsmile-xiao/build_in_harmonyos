#!/usr/bin/env python3
"""Run the runnable WAILI examples and record upstream limitations."""

import os
import shutil
import subprocess
import sys
from pathlib import Path


PROGRAMS = ("Demo", "Example", "Histogram", "Proof", "Rangecheck", "Test")


def run_program(binary, args=(), cwd=None, input_bytes=None, expect_rc=0):
    result = subprocess.run(
        [str(binary), *args],
        cwd=cwd,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=180,
        check=False,
    )
    output = result.stdout.decode("utf-8", errors="replace")
    if expect_rc is not None and result.returncode != expect_rc:
        raise SystemExit(
            f"{binary.name} returned {result.returncode}, expected {expect_rc}:\n{output}"
        )
    return result.returncode, output


def write_pgm(path):
    width = 64
    height = 64
    pixels = bytes(
        (row * 3 + column) % 256
        for row in range(height)
        for column in range(width)
    )
    path.write_bytes(f"P5\n{width} {height}\n255\n".encode("ascii") + pixels)


def require_output_file(path):
    if not path.is_file() or path.stat().st_size == 0:
        raise SystemExit(f"expected non-empty output file: {path}")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_waili.py <package-bin-directory>")

    bindir = Path(sys.argv[1]).resolve()
    missing = [name for name in PROGRAMS if not (bindir / name).is_file()]
    if missing:
        raise SystemExit("packaged programs are missing: " + ", ".join(missing))

    root = Path.cwd() / "waili-consumer"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    image = root / "image.pgm"
    write_pgm(image)

    rc, _ = run_program(bindir / "Example", cwd=root)
    assert rc == 0
    result = root / "result.pgm"
    require_output_file(result)
    if not result.read_bytes().startswith(b"P5"):
        raise SystemExit("Example result.pgm is not a binary PGM")

    rc, demo_output = run_program(
        bindir / "Demo",
        cwd=root,
        input_bytes=b"quit\n",
    )
    assert rc == 0
    if "demo>" not in demo_output:
        raise SystemExit(f"Demo did not reach its command prompt:\n{demo_output}")

    rc, _ = run_program(bindir / "Proof", ("image.pgm",), cwd=root)
    assert rc == 0
    for name in ("out1.pgm", "out2.pgm", "reco1.pgm", "reco2.pgm"):
        require_output_file(root / name)

    rc, test_output = run_program(bindir / "Test", ("image.pgm",), cwd=root)
    assert rc == 0
    if "Maxerr = 0.000000" not in test_output:
        raise SystemExit(f"Test did not report zero reconstruction error:\n{test_output}")

    histogram_rc, histogram_output = run_program(
        bindir / "Histogram",
        ("--help",),
        cwd=root,
        expect_rc=None,
    )
    if histogram_rc == 0 or "Usage:" not in histogram_output:
        raise SystemExit(
            "Histogram help smoke failed: expected non-zero Usage output:\n"
            + histogram_output
        )

    limitations = []
    gnuplot = shutil.which("gnuplot")
    if gnuplot:
        rc, histogram_output = run_program(
            bindir / "Histogram",
            ("image.pgm", "histogram"),
            cwd=root,
        )
        if rc != 0:
            raise SystemExit(f"Histogram failed with gnuplot available:\n{histogram_output}")
        eps_files = list(root.glob("histogram_*.eps"))
        if not eps_files or not all(path.stat().st_size > 0 for path in eps_files):
            raise SystemExit("Histogram did not produce non-empty EPS output")
        histogram_status = f"executed with {gnuplot} ({len(eps_files)} EPS files)"
    else:
        histogram_status = "not executed: gnuplot is unavailable"
    limitations.append("Histogram plotting " + histogram_status)

    rangecheck_rc, rangecheck_output = run_program(
        bindir / "Rangecheck",
        cwd=root,
        expect_rc=None,
    )
    if rangecheck_rc == 0:
        raise SystemExit("Rangecheck unexpectedly passed the 16-bit PixType preflight")
    if "PixType must contain 64 bits" not in rangecheck_output:
        raise SystemExit(
            "Rangecheck did not report the documented upstream PixType bug:\n"
            + rangecheck_output
        )
    limitations.append(
        "Rangecheck expected failure: upstream requires 64-bit PixType, "
        "but the project defines PixType as 16-bit s16"
    )

    print(
        "waili consumer test: 4/4 runnable workflows passed "
        "(Example, Demo, Proof, Test)"
    )
    for limitation in limitations:
        print("waili limitation: " + limitation)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
