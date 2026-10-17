#!/usr/bin/env python3
"""Consumer test for caesiumclt: version/help plus real PNG compression."""

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile


# 1x1 pixel PNG (opaque red), no network needed.
_TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGA"
    "hKmMIQAAAABJRU5ErkJggg=="
)


def run(binary, *args, cwd=None):
    result = subprocess.run(
        [binary, *args], cwd=cwd,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, check=False,
    )
    return result


def main():
    if len(sys.argv) != 2:
        print("usage: test_caesiumclt.py <caesiumclt>", file=sys.stderr)
        return 2
    binary = sys.argv[1]
    if not os.path.isfile(binary):
        raise AssertionError(f"caesiumclt binary not found: {binary}")

    # 1. --version
    version = run(binary, "--version")
    if version.returncode != 0:
        raise AssertionError(f"--version failed:\n{version.stdout}\n{version.stderr}")
    if "1.4.0" not in version.stdout:
        raise AssertionError(f"--version mismatch:\n{version.stdout}")

    # 2. --help exposes core flags
    help_out = run(binary, "--help")
    if help_out.returncode != 0:
        raise AssertionError(f"--help failed:\n{help_out.stdout}\n{help_out.stderr}")
    for flag in ("--quality", "--output", "--lossless"):
        if flag not in help_out.stdout:
            raise AssertionError(f"--help missing {flag}:\n{help_out.stdout}")

    # /tmp is read-only on the preflight worker; honor the injected TMPDIR.
    tmp_base = (
        os.environ.get("HMBS_TMPDIR")
        or os.environ.get("TMPDIR")
        or os.environ.get("TMP")
        or os.environ.get("TEMP")
    )
    if tmp_base:
        os.makedirs(tmp_base, exist_ok=True)
    tmpdir = tempfile.mkdtemp(prefix="caesiumclt-test-", dir=tmp_base or None)
    try:
        src = os.path.join(tmpdir, "input.png")
        with open(src, "wb") as handle:
            handle.write(base64.b64decode(_TINY_PNG_B64))
        assert os.path.getsize(src) > 0, "fixture PNG is empty"

        # 3. Real lossy compression to an output directory.
        outdir = os.path.join(tmpdir, "out")
        os.makedirs(outdir, exist_ok=True)
        comp = run(binary, "-q", "80", "-o", outdir, src)
        if comp.returncode != 0:
            raise AssertionError(f"compression failed:\n{comp.stdout}\n{comp.stderr}")
        produced = [f for f in os.listdir(outdir) if os.path.isfile(os.path.join(outdir, f))]
        if not produced:
            raise AssertionError(f"no output produced in {outdir}:\n{comp.stdout}\n{comp.stderr}")
        out_file = os.path.join(outdir, produced[0])
        if os.path.getsize(out_file) == 0:
            raise AssertionError(f"compressed output is empty: {out_file}")

        # 4. Dry run succeeds without writing files.
        drydir = os.path.join(tmpdir, "dry")
        os.makedirs(drydir, exist_ok=True)
        dry = run(binary, "-q", "80", "--dry-run", "-o", drydir, src)
        if dry.returncode != 0:
            raise AssertionError(f"--dry-run failed:\n{dry.stdout}\n{dry.stderr}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print("caesiumclt version/help/compression checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
