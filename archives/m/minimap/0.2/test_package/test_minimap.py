#!/usr/bin/env python3
"""Functional test harness for the installed minimap binary.

Usage: test_minimap.py <path-to-minimap> <result-json> [workdir]

Creates a small synthetic target/query FASTA pair and checks version, usage,
direct mapping and index dump/load mapping. Also writes target.fa/query.fa so
the C consumer test in conanfile.py can reuse them.
"""
import json
import os
import subprocess
import sys


def gen_seq(n, seed=7):
    out = []
    x = seed
    for _ in range(n):
        x = (1103515245 * x + 12345) & 0x7fffffff
        out.append("ACGT"[(x >> 16) & 3])
    return "".join(out)


def main():
    exe = sys.argv[1]
    result_path = sys.argv[2]
    workdir = sys.argv[3] if len(sys.argv) > 3 else os.path.expanduser("~")
    os.makedirs(workdir, exist_ok=True)

    target = os.path.join(workdir, "target.fa")
    query = os.path.join(workdir, "query.fa")
    genome = gen_seq(2000)
    with open(target, "w") as handle:
        handle.write(">chr1\n" + genome + "\n")
    with open(query, "w") as handle:
        handle.write(">read1\n" + genome[400:1000] + "\n")

    checks = []

    def record(name, ok, detail=""):
        checks.append((name, bool(ok)))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if detail and not ok else ""))

    def run(args):
        proc = subprocess.run([exe] + args, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, cwd=workdir)
        return proc.returncode, proc.stdout, proc.stderr

    rc, out, err = run(["-V"])
    record("version: -V == 0.2-r123", rc == 0 and out.decode().strip() == "0.2-r123",
           out.decode("utf-8", "replace"))

    rc, out, err = run([])
    record("usage: no args prints Usage", rc != 0 and b"Usage" in err)

    rc, out, err = run(["-k", "7", "-w", "4", "-L", "10", "-c", "1", "-t", "1", target, query])
    hits = [ln for ln in out.decode("utf-8", "replace").splitlines() if ln.strip()]
    record("functional: direct mapping emits a hit", rc == 0 and len(hits) >= 1,
           f"rc={rc} hits={len(hits)}")

    mmi = os.path.join(workdir, "target.mmi")
    rc1, _, _ = run(["-k", "7", "-w", "4", "-d", mmi, target])
    rc2, out2, err2 = run(["-l", mmi, query])
    hits2 = [ln for ln in out2.decode("utf-8", "replace").splitlines() if ln.strip()]
    record("functional: index dump + load mapping emits a hit",
           rc1 == 0 and rc2 == 0 and len(hits2) >= 1,
           f"rc1={rc1} rc2={rc2} hits={len(hits2)}")

    passed = sum(1 for _, ok in checks if ok)
    failed = len(checks) - passed
    summary = {"passed": passed, "total": len(checks), "failed": failed}
    with open(result_path, "w") as handle:
        json.dump(summary, handle)
    print("MINIMAP_RESULT passed={passed} total={total} failed={failed}".format(**summary))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
