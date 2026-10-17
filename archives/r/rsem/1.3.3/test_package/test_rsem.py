#!/usr/bin/env python3
"""Conan test_package — rsem 1.3.3 functional smoke test.

rsem upstream ships no test suite (no tests/ directory, no test/check
make target — see notes.md). This test_package fills that gap with a
functional pipeline check that exercises the packaged binaries:

  1. rsem-samtools --version           (bundled samtools runs)
  2. rsem-samtools view -bS            (SAM -> BAM conversion via htslib)
  3. rsem-samtools view -H             (BAM header readable back)
  4. rsem-sam-validator                (SAM/BAM validation tool runs)
  5. rsem-build-read-index             (creates a read index from FASTQ)
  6. rsem-bam2readdepth                (BAM -> per-base read depth)
  7. rsem-simulate-reads               (usage banner proves the binary loads)

All run-time artifacts are created in a temp working dir; nothing is
written back into the fixture data/ directory.
"""
import os
import platform
import shutil
import subprocess
import sys
import tempfile

bin_dir = sys.argv[1]
bindir = os.path.abspath(bin_dir)


def run(cmd, **kw):
    print(f"  $ {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr)
        raise SystemExit(f"FAILED: {' '.join(cmd)} (rc={r.returncode})")
    return r


def check(cond, msg):
    if not cond:
        raise SystemExit(f"FAILED: {msg}")
    print(f"  ok: {msg}")


print(f"[rsem test_package] os={platform.system()} arch={platform.machine()}")

here = os.path.dirname(os.path.abspath(__file__))
work = tempfile.mkdtemp(prefix="rsem-test-")
try:
    # 1. bundled samtools runs
    r = run([os.path.join(bindir, "rsem-samtools"), "--version"])
    check("samtools 1.3" in r.stdout, "rsem-samtools --version reports samtools 1.3")

    # 2. SAM -> BAM conversion
    sam = os.path.join(here, "data", "test.sam")
    bam = os.path.join(work, "test.bam")
    run([os.path.join(bindir, "rsem-samtools"), "view", "-bS", sam, "-o", bam])
    check(os.path.isfile(bam) and os.path.getsize(bam) > 0,
          "rsem-samtools view -bS produced a non-empty BAM")

    # 3. BAM header readable back
    r = run([os.path.join(bindir, "rsem-samtools"), "view", "-H", bam])
    check("@SQ" in r.stdout and "SN:chr1" in r.stdout,
          "BAM header is readable back (contains @SQ SN:chr1)")

    # 4. SAM validator accepts the fixture (rc==0 enforced by run())
    r = run([os.path.join(bindir, "rsem-sam-validator"), sam])
    check(r.returncode == 0, "rsem-sam-validator accepted the SAM fixture")

    # 5. read index built from FASTQ — copy the fixture into the temp dir so
    #    the generated .ridx never lands beside (or shadows) the input file
    fq = os.path.join(work, "test_reads.fq")
    shutil.copyfile(os.path.join(here, "data", "test_reads.fq"), fq)
    run([os.path.join(bindir, "rsem-build-read-index"), "0", "1", "1", fq])
    ridx = fq + ".ridx"
    check(os.path.isfile(ridx) and os.path.getsize(ridx) > 0,
          "rsem-build-read-index produced a non-empty .ridx")

    # 6. BAM -> read depth; fixture records carry ZW:f:1.0, so positions
    #    100 and 200 (1-based) must each have depth >= 1
    depth = os.path.join(work, "test.depth")
    run([os.path.join(bindir, "rsem-bam2readdepth"), bam, depth])
    check(os.path.isfile(depth) and os.path.getsize(depth) > 0,
          "rsem-bam2readdepth produced a depth file")
    depth_by_pos = {}
    for line in open(depth):
        parts = line.split()
        if len(parts) < 3:
            continue
        # depth values are space-separated in the third column
        depth_by_pos[parts[0]] = parts[2:]
    check("chr1" in depth_by_pos and len(depth_by_pos["chr1"]) == 1000,
          "depth file covers chr1 with 1000 per-base entries")
    d100 = int(float(depth_by_pos["chr1"][99]))
    d200 = int(float(depth_by_pos["chr1"][199]))
    check(d100 >= 1, "read depth at chr1:100 is nonzero (got %d)" % d100)
    check(d200 >= 1, "read depth at chr1:200 is nonzero (got %d)" % d200)
    d50 = int(float(depth_by_pos["chr1"][49]))
    check(d50 == 0, "read depth at uncovered chr1:50 is zero (got %d)" % d50)

    # 7. simulate-reads loads and prints usage (rc!=0 with no args is expected)
    r = subprocess.run([os.path.join(bindir, "rsem-simulate-reads")],
                       capture_output=True, text=True)
    print("  $ rsem-simulate-reads (no args)")
    check("Usage: rsem-simulate-reads" in r.stdout + r.stderr,
          "rsem-simulate-reads usage banner")
    print("[rsem test_package] ALL TESTS PASSED")
finally:
    shutil.rmtree(work, ignore_errors=True)
