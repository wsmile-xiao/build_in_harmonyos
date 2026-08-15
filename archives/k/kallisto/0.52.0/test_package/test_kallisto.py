#!/usr/bin/env python3
"""kallisto 0.52.0 test_package real test source (L0c: test source file).

Runs the installed kallisto binary end-to-end against bundled upstream
unit_tests input data: version assertion + index (10 targets) + quant
(pseudoalignment + abundance.tsv output).
Usage: test_kallisto.py <path-to-kallisto-bin> <path-to-input-data-dir>
"""
import os
import shutil
import subprocess
import sys
import tempfile


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        sys.stderr.write(r.stdout)
        sys.stderr.write(r.stderr)
        raise AssertionError(f"command failed ({r.returncode}): {' '.join(cmd)}")
    return r


def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: test_kallisto.py <kallisto-bin> <input-data-dir>")
    kbin = sys.argv[1]
    data_dir = sys.argv[2]
    if not os.path.isfile(kbin):
        raise AssertionError(f"kallisto binary missing: {kbin}")
    if not os.path.isdir(data_dir):
        raise AssertionError(f"input data missing: {data_dir}")

    # 1) version assertion
    r = run([kbin, "version"])
    if "0.52.0" not in r.stdout:
        raise AssertionError(f"unexpected version output: {r.stdout!r}")

    # 2) index + quant on upstream unit_tests input data
    fasta = os.path.join(data_dir, "10_trans_gt_500_bp.fasta")
    r1 = os.path.join(data_dir, "r1.fastq")
    r2 = os.path.join(data_dir, "r2.fastq")
    for f in (fasta, r1, r2):
        if not os.path.isfile(f):
            raise AssertionError(f"upstream input missing: {f}")
    workdir = tempfile.mkdtemp(prefix="kallisto-tp-")
    try:
        idx = os.path.join(workdir, "idx.kallisto")
        run([kbin, "index", "-i", idx, "-k", "21", fasta])
        out = os.path.join(workdir, "quant")
        run([kbin, "quant", "-i", idx, "-o", out, "-b", "10", r1, r2])
        ab = os.path.join(out, "abundance.tsv")
        if not os.path.isfile(ab):
            raise AssertionError(f"quant output missing: {ab}")
        print(f"OK: kallisto 0.52.0 index+quant smoke passed ({ab})")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
