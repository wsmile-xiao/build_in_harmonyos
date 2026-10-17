#!/usr/bin/env python3
"""L1 consumer test for probcons/1.12.

Executes the packaged binaries (R34): --version/--help smoke (K0) plus a
real multiple-sequence alignment over a bundled FASTA file.
"""
import os
import subprocess
import sys

BINDIR = sys.argv[1]
PROBCONS = os.path.join(BINDIR, "probcons")
FASTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.fa")


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60)


def main():
    checks = 0
    # 1) K0: main command answers --version with rc=0
    r = run([PROBCONS, "--version"])
    assert r.returncode == 0, "--version rc=%d stderr=%s" % (r.returncode, r.stderr)
    assert "1.12" in (r.stdout + r.stderr), "version string missing"
    checks += 1
    # 2) K0: --help answers with rc=0 as well
    r = run([PROBCONS, "--help"])
    assert r.returncode == 0, "--help rc=%d" % r.returncode
    assert "Usage" in (r.stdout + r.stderr), "usage text missing"
    checks += 1
    # 3) functional: align 3 protein sequences
    r = run([PROBCONS, FASTA])
    assert r.returncode == 0, "alignment rc=%d stderr=%s" % (r.returncode, r.stderr)
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    headers = [ln for ln in lines if ln.startswith(">")]
    assert len(headers) == 3, "expected 3 aligned records, got %d" % len(headers)
    seqs = [ln for ln in lines if not ln.startswith(">")]
    assert len(seqs) == 3, "expected 3 sequence lines, got %d" % len(seqs)
    assert all(set(s) <= set("ACDEFGHIKLMNPQRSTVWYU-") for s in seqs), "invalid residues"
    assert len(set(len(s) for s in seqs)) == 1, "aligned rows have unequal length"
    checks += 4
    print("test_probcons: %d checks passed" % checks)


if __name__ == "__main__":
    main()
