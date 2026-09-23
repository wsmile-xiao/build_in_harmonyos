#!/usr/bin/env python3
"""Functional test harness for the installed miniasm binary.

Usage: test_miniasm.py <path-to-miniasm> <result-json> [workdir]

miniasm 0.3 ships no upstream test suite, so this harness builds a small
deterministic all-vs-all overlap set (7 reads of 2500 bp sampled every 150 bp
from a 3600 bp synthetic sequence), feeds the PAF to miniasm, and checks the
resulting GFA/PAF output. Also checks the version and usage behaviour.
"""
import json
import os
import subprocess
import sys


def gen_seq(n, seed=1):
    out = []
    x = seed
    for _ in range(n):
        x = (1103515245 * x + 12345) & 0x7fffffff
        out.append("ACGT"[(x >> 16) & 3])
    return "".join(out)


def build_inputs(workdir):
    genome = gen_seq(3600)
    read_len, step, n_reads = 2500, 150, 7
    reads = []
    for i in range(n_reads):
        start = i * step
        reads.append(genome[start:start + read_len])

    fa = os.path.join(workdir, "reads.fa")
    with open(fa, "w") as handle:
        for i, seq in enumerate(reads):
            handle.write(f">R{i}\n{seq}\n")

    paf = os.path.join(workdir, "reads.paf")
    lines = []
    for i in range(n_reads):
        si, ei = i * step, i * step + read_len
        for j in range(n_reads):
            if i == j:
                continue
            sj, ej = j * step, j * step + read_len
            ov_s, ov_e = max(si, sj), min(ei, ej)
            length = ov_e - ov_s
            if length < 2000:
                continue
            qs, qe = ov_s - si, ov_e - si
            ts, te = ov_s - sj, ov_e - sj
            lines.append(f"R{i}\t{read_len}\t{qs}\t{qe}\t+\tR{j}\t{read_len}\t{ts}\t{te}\t{length}\t{length}\t60")
    with open(paf, "w") as handle:
        handle.write("\n".join(lines) + "\n")
    return fa, paf, lines


def main():
    exe = sys.argv[1]
    result_path = sys.argv[2]
    workdir = sys.argv[3] if len(sys.argv) > 3 else os.path.expanduser("~")
    os.makedirs(workdir, exist_ok=True)

    checks = []

    def record(name, ok, detail=""):
        checks.append((name, bool(ok)))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if detail and not ok else ""))

    def run(args, stdin=None):
        proc = subprocess.run([exe] + args, input=stdin, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, cwd=workdir)
        return proc.returncode, proc.stdout, proc.stderr

    rc, out, err = run(["-V"])
    record("version: -V == 0.3-r179", rc == 0 and out.decode().strip() == "0.3-r179",
           out.decode('utf-8', 'replace'))

    rc, out, err = run([])
    record("usage: no args prints Usage to stderr", rc != 0 and b"Usage" in err)

    fa, paf, lines = build_inputs(workdir)
    record("input harness produced overlap lines", len(lines) > 0, f"{len(lines)} lines")

    # -c 1 -e 0 keeps the tiny synthetic graph from being pruned.
    rc, out, err = run(["-c", "1", "-e", "0", "-f", fa, paf])
    gfa = out.decode("utf-8", "replace")
    seg_lines = [ln for ln in gfa.splitlines() if ln.startswith("S\t")]
    record("functional: miniasm produces a GFA segment", rc == 0 and len(seg_lines) >= 1,
           f"rc={rc} segments={len(seg_lines)}")

    rc, out, err = run(["-p", "paf", paf])
    hit_lines = [ln for ln in out.decode("utf-8", "replace").splitlines() if ln.strip()]
    record("functional: -p paf emits overlap records", rc == 0 and len(hit_lines) >= 1,
           f"rc={rc} hits={len(hit_lines)}")

    rc, out, err = run(["-p", "bed", paf])
    record("functional: -p bed runs", rc == 0, f"rc={rc}")

    passed = sum(1 for _, ok in checks if ok)
    failed = len(checks) - passed
    summary = {"passed": passed, "total": len(checks), "failed": failed}
    with open(result_path, "w") as handle:
        json.dump(summary, handle)
    print("MINIASM_RESULT passed={passed} total={total} failed={failed}".format(**summary))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
