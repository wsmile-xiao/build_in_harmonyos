#!/usr/bin/env python3
"""Consumer test driver for the packaged PRANK binary (HarmonyOS PC / OHOS).

Run as a plain program, never imported:

    python3 msa_check.py --prank <abs path to packaged prank> --work <dir>
                         [--json <result file>]

This is the "layer 2" test from docs/TEST_QUALITY_SPEC.md: it acts as a real
user of the *packaged* artifact.  Every scenario asserts **both** the process
exit code **and** properties of what PRANK actually produced (alignment
records, column parity, gap columns, lossless round-trip of the input
sequences, converted-format headers).  Nothing here is a "file exists" or
"it printed something" smoke check.

Upstream PRANK 250331 ships no test suite at all.  Its Makefile ``check:`` rule
(src/Makefile:160) carries no recipe of its own but depends on ``first``, which
chains ``check -> first (:119) -> all (:142)`` and merely recompiles the whole
program: ``make -n check`` expands to 36 ``g++ -c`` + 1 ``g++ -o`` command lines
and 0 test commands (see test_package/MANIFEST.yml for the inventory).  This file
is therefore the only behavioural evidence in the package.

Exit status: 0 only when every assertion passed.
"""
import argparse
import json
import os
import subprocess
import sys

# ── fixtures ─────────────────────────────────────────────────────────────
# Four short DNA sequences derived from one ancestor: seq2 carries a
# substitution, seq3 a 6 nt deletion, seq4 a 10 nt insertion.  PRANK has to
# place the resulting gap columns using its indel model, so the aligned matrix
# is a real product of the aligner rather than an echo of the input.
DNA_RECORDS = [
    ("seq1",
     "ATGCGTACGTACGGATCCTTGGACCTGTACGATCGATCGATCGGGATCCCATGGCTTAAGCTTGGG"
     "ATCCACGTACGTATCGATCGATCGGGATCCCATGGCTTAAGCTTGGGATCCACGTACGTATCGATC"),
    ("seq2",
     "ATGCGTACGTACGGATCCTTGGACCTGTACGATCGATCGATCGGGATCCCATGGCTTAAGCTTGGG"
     "ATCCACGTACGTATCGATCGATCGGGATCCCATGGCTTAAGCTCGGGATCCACGTACGTATCGATC"),
    ("seq3",
     "ATGCGTACGTACGGATCCTTGGACCTGTACGATCGATCGATCGGGATCCCATGGCTTAAGCTTGGG"
     "ATCCACGTACGTATCGATCGATCGGGATCCCATGGCTTAAGCTTGGGATCCACGTATCGATC"),
    ("seq4",
     "ATGCGTACGTACGGATCCTTGGACCTGTACGATCGATCGATCGGGATCCCATGGCTTAAGCTTGGG"
     "ATCCACGTACGTATCGATCGATCGGGATCCCATGGCTTAAGCTTGGGATCCACGTACGTACGTACGT"
     "ATCGATC"),
]

PROT_RECORDS = [
    ("p1", "MKTLLILAVLTIAAPTSSAEFKGIVGRAVGLADFSKGKTG"),
    ("p2", "MKTLLILAVLTIAAPTSSAEFKGIVGRAVGLADFSKGKAG"),
    ("p3", "MKTLLILAVLTIAAPTSSAEFKGIVGRAVGLAFSKGKAG"),
    ("p4", "MKTLLILAVLTIAAPTSSAEFKGIVGRAVGLADFSKGKAGTTAA"),
]

MAX_INPUT_DNA = max(len(s) for _, s in DNA_RECORDS)
MAX_INPUT_PROT = max(len(s) for _, s in PROT_RECORDS)


class Checker:
    """Counts and reports assertions; a failed check never aborts the run."""

    def __init__(self):
        self.results = []

    def check(self, name, ok, detail=""):
        self.results.append({"name": name, "ok": bool(ok), "detail": detail})
        print("ASSERT %-46s %s%s" % (name, "PASS" if ok else "FAIL",
                                     ("  [%s]" % detail) if detail and not ok else ""))
        return bool(ok)

    @property
    def passed(self):
        return sum(1 for r in self.results if r["ok"])

    @property
    def total(self):
        return len(self.results)


def write_fasta(path, records):
    with open(path, "w", encoding="ascii") as fh:
        for name, seq in records:
            fh.write(">%s\n%s\n" % (name, seq))


def read_fasta_records(path):
    """Parse a (possibly interleaved) FASTA into [(name, seq_without_gaps_full)]."""
    recs = []
    name = None
    chunks = []
    with open(path, "r", encoding="ascii", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            if line.startswith(">"):
                if name is not None:
                    recs.append((name, "".join(chunks)))
                name = line[1:].split()[0]
                chunks = []
            else:
                chunks.append(line)
    if name is not None:
        recs.append((name, "".join(chunks)))
    return recs


def run_prank(prank, work, args):
    """Invoke the packaged binary with a writable TMPDIR.

    PRANK creates its scratch directory with mkdtemp() under
    TMPDIR/TMP/TEMPDIR/TEMP and aborts if none of them is writable; on OHOS
    ``/tmp`` is read-only, so the harness always points TMPDIR at the job's own
    working directory.
    """
    tmp = os.path.join(work, "tmp")
    os.makedirs(tmp, exist_ok=True)
    env = os.environ.copy()
    for key in ("TMPDIR", "TMP", "TEMPDIR", "TEMP"):
        env[key] = tmp
    cmd = [prank] + args
    proc = subprocess.run(cmd, cwd=work, env=env, timeout=900,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, errors="replace")
    return proc.returncode, proc.stdout or ""


def strip_gaps(seq):
    return seq.replace("-", "").replace(".", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prank", required=True, help="absolute path to packaged prank")
    ap.add_argument("--work", required=True, help="writable working directory")
    ap.add_argument("--json", default="", help="where to write the JSON summary")
    opts = ap.parse_args()

    prank = os.path.abspath(opts.prank)
    work = os.path.abspath(opts.work)
    os.makedirs(work, exist_ok=True)
    c = Checker()

    # ── S1: help / version surface ─────────────────────────────────────
    rc, out = run_prank(prank, work, ["--version"])
    c.check("s1_version_exit0", rc == 0, "rc=%s" % rc)
    c.check("s1_version_banner", "v.250331" in out,
            "no 'v.250331' in help output")

    rc, out = run_prank(prank, work, ["-help"])
    c.check("s1_help_exit0", rc == 0, "rc=%s" % rc)
    c.check("s1_help_options", "-codon" in out and "-convert" in out,
            "documented options missing from -help")

    # ── S2: real DNA multiple sequence alignment ───────────────────────
    write_fasta(os.path.join(work, "dna.fasta"), DNA_RECORDS)
    rc, out = run_prank(prank, work, ["-d=dna.fasta", "-o=dna_aln", "-once"])
    c.check("s2_align_exit0", rc == 0, "rc=%s out=%r" % (rc, out[-200:]))
    c.check("s2_align_banner", "PRANK v.250331" in out, "banner missing")
    c.check("s2_align_score", "Alignment score:" in out,
            "no likelihood score reported")
    c.check("s2_align_reports_input", "dna.fasta" in out,
            "run did not echo its input")

    aln_path = os.path.join(work, "dna_aln.best.fas")
    c.check("s2_alignment_written", os.path.isfile(aln_path)
            and os.path.getsize(aln_path) > 0 if os.path.isfile(aln_path) else False,
            "missing %s" % aln_path)

    recs = read_fasta_records(aln_path) if os.path.isfile(aln_path) else []
    c.check("s2_record_count", len(recs) == len(DNA_RECORDS),
            "got %d records, expected %d" % (len(recs), len(DNA_RECORDS)))
    c.check("s2_record_names",
            sorted(n.lower() for n, _ in recs) == sorted(n for n, _ in DNA_RECORDS),
            "names: %r" % ([n for n, _ in recs],))

    widths = {len(s) for _, s in recs}
    c.check("s2_uniform_columns", len(widths) == 1 and widths != {0},
            "column counts differ: %r" % (sorted(widths),))
    width = next(iter(widths)) if len(widths) == 1 else 0
    c.check("s2_matrix_not_shorter_than_longest_input",
            width >= MAX_INPUT_DNA,
            "alignment width %d < longest input %d" % (width, MAX_INPUT_DNA))

    gapfree = [("-" in s) for _, s in recs]
    c.check("s2_gap_columns_present", any(gapfree),
            "aligner produced no gap columns — indel model not exercised")
    c.check("s2_gaps_in_short_sequences_only",
            all(("-" in s) == (len(strip_gaps(s)) < width) for _, s in recs),
            "gap placement contradicts sequence lengths")

    # Losslessness: removing the inserted gap columns must give back exactly
    # the input sequence for every record.
    by_name = {n.lower(): s for n, s in recs}
    for name, expect in DNA_RECORDS:
        got = strip_gaps(by_name.get(name, ""))
        c.check("s2_roundtrip_%s" % name, got == expect,
                "aligned row differs from input after gap removal")

    # ── S3: guide tree output ──────────────────────────────────────────
    rc, out = run_prank(prank, work,
                        ["-d=dna.fasta", "-o=tree_aln", "-once", "-showtree"])
    dnd = os.path.join(work, "tree_aln.best.dnd")
    c.check("s3_tree_exit0", rc == 0, "rc=%s" % rc)
    c.check("s3_tree_written", os.path.isfile(dnd) and os.path.getsize(dnd) > 0
            if os.path.isfile(dnd) else False, "missing %s" % dnd)
    if os.path.isfile(dnd):
        with open(dnd, "r", encoding="ascii", errors="replace") as fh:
            newick = fh.read().strip()
    else:
        newick = ""
    c.check("s3_tree_newick_shape",
            newick.startswith("(") and newick.rstrip(";").endswith(")")
            and newick.count("(") == newick.count(")"),
            "not a balanced Newick string: %r" % newick[:60])
    low = newick.lower()
    c.check("s3_tree_leaves",
            all(n.lower() in low for n, _ in DNA_RECORDS),
            "leaf labels missing: %r" % newick[:60])

    # ── S4: protein model ──────────────────────────────────────────────
    write_fasta(os.path.join(work, "prot.fasta"), PROT_RECORDS)
    rc, out = run_prank(prank, work,
                        ["-d=prot.fasta", "-o=prot_aln", "-once", "-protein"])
    c.check("s4_protein_exit0", rc == 0, "rc=%s out=%r" % (rc, out[-200:]))
    paln = os.path.join(work, "prot_aln.best.fas")
    prec = read_fasta_records(paln) if os.path.isfile(paln) else []
    c.check("s4_protein_records", len(prec) == len(PROT_RECORDS),
            "got %d records" % len(prec))
    pwidths = {len(s) for _, s in prec}
    c.check("s4_protein_uniform", len(pwidths) == 1
            and next(iter(pwidths)) >= MAX_INPUT_PROT
            if len(pwidths) == 1 else False,
            "protein matrix not uniformly aligned: %r" % (sorted(pwidths),))

    # ── S5: format conversion of the alignment it just wrote ───────────
    rc, out = run_prank(prank, work,
                        ["-convert", "-d=dna_aln.best.fas", "-o=conv",
                         "-f=phylipi"])
    phy = os.path.join(work, "conv.phy")
    c.check("s5_convert_phylip_exit0", rc == 0, "rc=%s out=%r" % (rc, out[-200:]))
    c.check("s5_convert_phylip_written",
            os.path.isfile(phy) and os.path.getsize(phy) > 0
            if os.path.isfile(phy) else False, "missing %s" % phy)
    if os.path.isfile(phy):
        with open(phy, "r", encoding="ascii", errors="replace") as fh:
            head = fh.readline().split()
    else:
        head = []
    c.check("s5_phylip_header", len(head) >= 2 and head[0] == str(len(DNA_RECORDS)),
            "phylip header: %r" % (head,))

    rc, out = run_prank(prank, work,
                        ["-convert", "-d=dna_aln.best.fas", "-o=convn",
                         "-f=nexus"])
    nex = os.path.join(work, "convn.nex")
    c.check("s5_convert_nexus_exit0", rc == 0, "rc=%s" % rc)
    nex_head = ""
    if os.path.isfile(nex):
        with open(nex, "r", encoding="ascii", errors="replace") as fh:
            nex_head = fh.readline().strip()
    c.check("s5_nexus_header", nex_head.upper().startswith("#NEXUS"),
            "nexus file starts with %r" % nex_head[:30])

    # ── S6: verbosity control changes observable behaviour ─────────────
    rc_norm, out_norm = run_prank(prank, work,
                                  ["-d=dna.fasta", "-o=loud", "-once"])
    rc_q, out_q = run_prank(prank, work,
                            ["-d=dna.fasta", "-o=quiet", "-once", "-quiet"])
    c.check("s6_quiet_exit0", rc_q == 0, "rc=%s" % rc_q)
    c.check("s6_quiet_reduces_report", 0 < len(out_q) < len(out_norm),
            "quiet=%d bytes vs default=%d bytes" % (len(out_q), len(out_norm)))
    c.check("s6_quiet_still_writes_alignment",
            os.path.isfile(os.path.join(work, "quiet.best.fas")),
            "-quiet must not suppress the alignment itself")

    # ── S7: negative control — a broken run must not look like success ─
    rc, out = run_prank(prank, work, ["-d=absent.fasta", "-o=neg", "-once"])
    c.check("s7_missing_input_nonzero_exit", rc != 0, "rc=%s (expected != 0)" % rc)
    c.check("s7_missing_input_message", "Failed to open sequence file" in out,
            "no diagnostic for the missing input")
    c.check("s7_missing_input_wrote_nothing",
            not os.path.exists(os.path.join(work, "neg.best.fas")),
            "alignment written despite the failure")

    summary = {
        "binary": prank,
        "framework": "consumer-msa-harness",
        "discovered": c.total,
        "executed": c.total,
        "passed": c.passed,
        "failed": c.total - c.passed,
        "skipped": 0,
        "checks": c.results,
    }
    print("MSA_CHECK_RESULT=" + json.dumps(
        {k: v for k, v in summary.items() if k != "checks"}, sort_keys=True))
    if opts.json:
        with open(opts.json, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=1, sort_keys=True)
    if summary["failed"]:
        print("FAILED CHECKS: %s"
              % ", ".join(r["name"] for r in c.results if not r["ok"]))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
