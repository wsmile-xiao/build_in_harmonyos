#!/usr/bin/env python3
"""Functional consumer tests for megahit 1.2.9 (test source file for CI L0c).

Test logic extracted verbatim from test_package/conanfile.py test() so that a
real test source file lives in test_package/ (build_and_test.sh L0c whitelist:
c/cpp/cc/cxx/sh/py, conanfile.py excluded). conanfile.py test() drives this
script; any non-zero exit or failed assertion fails `conan test`.

Usage: python3 test_megahit.py <bindir> <workdir>
  <bindir>   directory holding megahit_core_no_hw_accel / megahit /
             megahit_toolkit from the tested package
  <workdir>  scratch directory for generated reads and assembly outputs

Assertion groups (5, 1:1 from the former inline version):
  A1  megahit_core_no_hw_accel dumpversion == 1.2.9
  A2  megahit wrapper real assembly (-t 2, 200x250bp synthetic reads) exits 0
  A3  assembly produces a non-empty final.contigs.fa
  A4  megahit_toolkit contig2fastg 49 exits 0 with non-empty FASTG output
  A5  megahit_toolkit readstat exits 0 on the contigs
Every subprocess is check=True, so each exit status is asserted too.
"""
import os
import random
import shutil
import subprocess
import sys


def main():
    if len(sys.argv) != 3:
        sys.stderr.write("usage: test_megahit.py <bindir> <workdir>\n")
        return 2
    bindir, workdir = sys.argv[1], sys.argv[2]
    core = os.path.join(bindir, "megahit_core_no_hw_accel")
    wrapper = os.path.join(bindir, "megahit")
    toolkit = os.path.join(bindir, "megahit_toolkit")
    shutil.rmtree(workdir, ignore_errors=True)
    os.makedirs(workdir, exist_ok=True)

    # A1: version smoke test
    res = subprocess.run([core, "dumpversion"], check=True,
                         capture_output=True, text=True)
    version = res.stdout.strip().lstrip("v")
    assert version == "1.2.9", "dumpversion returned {!r}".format(version)

    # A2/A3: small real assembly through the megahit wrapper (2 threads:
    # a known upstream threading defect corrupts sdbg output on aarch64
    # at >= 3 threads; see notes.md)
    random.seed(20260928)
    reads = os.path.join(workdir, "reads.fa")
    with open(reads, "w") as f:
        for i in range(200):
            seq = "".join(random.choice("ACGT") for _ in range(250))
            f.write(">r{}\n{}\n".format(i, seq))
    outdir = os.path.join(workdir, "asm")
    subprocess.run([wrapper, "-r", reads, "-o", outdir,
                    "-t", "2", "--k-list", "21,49", "--min-count", "1"],
                   check=True)
    contigs = os.path.join(outdir, "final.contigs.fa")
    assert os.path.isfile(contigs) and os.path.getsize(contigs) > 0, \
        "assembly produced no final.contigs.fa"

    # A4: toolkit contig2fastg on the assembly output
    fastg = os.path.join(workdir, "k49.fastg")
    with open(fastg, "wb") as fo:
        subprocess.run([toolkit, "contig2fastg", "49", contigs],
                       check=True, stdout=fo)
    assert os.path.isfile(fastg) and os.path.getsize(fastg) > 0

    # A5: toolkit readstat on the contigs
    with open(contigs, "rb") as fi, open(os.devnull, "wb") as dn:
        subprocess.run([toolkit, "readstat"], check=True, stdin=fi, stdout=dn)

    print("test_megahit: 5/5 assertion groups PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
