#!/usr/bin/env python3

import filecmp
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run_ad2vcf(package_dir):
    exe_name = "ad2vcf.exe" if os.name == "nt" else "ad2vcf"
    exe = package_dir / "bin" / exe_name
    fixture_dir = package_dir / "share" / "ad2vcf" / "Test"
    if not exe.is_file():
        raise FileNotFoundError(exe)
    if not fixture_dir.is_dir():
        raise FileNotFoundError(fixture_dir)

    version = subprocess.run([str(exe), "--version"], text=True, capture_output=True, check=True)
    if "ad2vcf 0.1.6" not in version.stdout:
        raise RuntimeError(f"unexpected version output: {version.stdout!r}")

    with tempfile.TemporaryDirectory(prefix="ad2vcf-test-", dir=os.getcwd()) as tmp:
        work = Path(tmp)
        for name in ("test.vcf", "test.sam", "test-ad-correct.vcf"):
            shutil.copy2(fixture_dir / name, work / name)

        with open(work / "test.sam", "rb") as sam_stream:
            result = subprocess.run(
                [str(exe), "test.vcf", "10"],
                cwd=work,
                stdin=sam_stream,
                text=True,
                capture_output=True,
            )
        if result.returncode != 0:
            sys.stderr.write(result.stdout)
            sys.stderr.write(result.stderr)
            raise RuntimeError(f"ad2vcf returned {result.returncode}")

        if not filecmp.cmp(work / "test-ad-correct.vcf", work / "test-ad.vcf", shallow=False):
            raise RuntimeError("ad2vcf fixture output differs from test-ad-correct.vcf")


def main(argv):
    if len(argv) != 2:
        raise SystemExit("usage: test_ad2vcf.py <package-folder>")
    run_ad2vcf(Path(argv[1]))


if __name__ == "__main__":
    main(sys.argv)
