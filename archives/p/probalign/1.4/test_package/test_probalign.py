#!/usr/bin/env python3
"""Consumer test for the probalign Conan package.

This exercises the delivered command line tool the way a user does: write
sequence files, run the installed binary, and judge the alignment it
reports.  Checks are behavioural, not existence checks -- a real alignment
must be rectangular, stripping its gaps must recover the input residues,
changing the temperature and gap costs must move an indel, and every
documented failure path must exit non-zero.

Expected outputs are goldens captured from the upstream 1.4 sources built
for the HarmonyOS target and re-verified byte for byte over repeated runs:
probalign computes posterior probabilities, it does not sample, so its
alignment is deterministic.

Usage: test_probalign.py <bin_dir> <work_dir>
"""
import os
import subprocess
import sys

TIMEOUT = 300

PROTEIN = {
    "s1": "MKVAAATLGGSIVAQGIRPTDYIACDGIKLNDLEFNIKPTTLKFFKEINTAGK",
    "s2": "MKVAAATLGGSIVAQGIRPTDYIACDGIKLNDLEFNIKPTTLKFFKEIN",
    "s3": "MQLGGSIVAQGIRPTDYIACDGIKLNDLEFNIKPTTLKFFKEIN",
}
# Golden alignment for PROTEIN under upstream defaults: -prot, temperature 5,
# gap open 22, gap extend 1, Gonnet 160.
PROTEIN_ALIGNED = [
    ("s1", "MKVAAATLGGSIVAQGIRPTDYIACDGIKLNDLEFNIKPTTLKFFKEINTAGK"),
    ("s2", "MKVAAATLGGSIVAQGIRPTDYIACDGIKLNDLEFNIKPTTLKFFKEIN----"),
    ("s3", "-----MQLGGSIVAQGIRPTDYIACDGIKLNDLEFNIKPTTLKFFKEIN----"),
]
# Same input with temperature 1 and cheaper gaps: the posterior optimum moves
# the s3 insertion, which is what makes this a genuine inference test.
PROTEIN_ALIGNED_TUNED = [
    ("s1", "MKVAAATLGGSIVAQGIRPTDYIACDGIKLNDLEFNIKPTTLKFFKEINTAGK"),
    ("s2", "MKVAAATLGGSIVAQGIRPTDYIACDGIKLNDLEFNIKPTTLKFFKEIN----"),
    ("s3", "MQ-----LGGSIVAQGIRPTDYIACDGIKLNDLEFNIKPTTLKFFKEIN----"),
]
CLUSTALW_GOLDEN = [
    "Probalign version 1.4 multiple sequence alignment",
    "",
    "s1    MKVAAATLGGSIVAQGIRPTDYIACDGIKLNDLEFNIKPTTLKFFKEINTAGK",
    "s2    MKVAAATLGGSIVAQGIRPTDYIACDGIKLNDLEFNIKPTTLKFFKEIN----",
    "s3    -----MQLGGSIVAQGIRPTDYIACDGIKLNDLEFNIKPTTLKFFKEIN----",
    "      *****  ******************************************",
]
NUCLEOTIDE = {
    "n1": "ACGTACGTAAAAACCCCCGGGGGTTTTT",
    "n2": "ACGTACGAAAAACCCCCGGGGTTTTTT",
    "n3": "ACGTACGTAAAAACCCCGGGGGTTTTTAA",
}
NUCLEOTIDE_ALIGNED = [
    ("n1", "ACGTACGTAAAAACCCCCGGGGGTTTT-T--"),
    ("n2", "ACGTACG-AAAAACCCCCGG-GGTTTTTT--"),
    ("n3", "ACGTACGTAAAAACC-CCGGGGGTTTT-TAA"),
]


class Consumer:
    """Runs the packaged binary and counts the assertions it settles."""

    def __init__(self, binary, work_dir):
        self.binary = binary
        self.work_dir = work_dir
        self.attempted = 0
        self.failures = []

    def check(self, label, condition, detail=""):
        self.attempted += 1
        if condition:
            print(f"ok: {label}")
            return
        self.failures.append(label)
        print(f"FAIL: {label} :: {detail}")

    def write_fasta(self, name, sequences):
        path = os.path.join(self.work_dir, name)
        with open(path, "w", encoding="ascii", newline="\n") as handle:
            for key in sequences:
                handle.write(f">{key}\n{sequences[key]}\n")
        return path

    def run(self, args):
        completed = subprocess.run(
            [self.binary, *args],
            cwd=self.work_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=TIMEOUT,
            check=False,
        )
        return (completed.returncode,
                completed.stdout.decode("utf-8", "replace"),
                completed.stderr.decode("utf-8", "replace"))


def parse_mfa(text):
    """Read probalign's own MFA output back as [(name, aligned_row)]."""
    entries = []
    name = None
    for line in text.splitlines():
        if not line.strip():
            continue
        if line.startswith(">"):
            name = line[1:].strip()
            continue
        entries.append((name, line.strip()))
    return entries


MARKERS = set("*:. ")
RESIDUES = set("ACDEFGHIKLMNPQRSTVWY-")


def parse_clustalw(text, width):
    """Read the sequence block of a CLUSTAL W report as [(name, row)]."""
    rows = []
    for line in text.splitlines():
        fields = line.split()
        if (len(fields) == 2
                and len(fields[1]) == width
                and set(fields[1]) <= RESIDUES):
            rows.append((fields[0], fields[1]))
    return rows


def has_conservation_row(text):
    """True when the report carries a marker-only conservation line."""
    return any(line.strip() and set(line.strip()) <= MARKERS
               for line in text.splitlines())


def assert_alignment(consumer, label, entries, aligned, source):
    """A reported alignment must be exact, rectangular and reversible."""
    consumer.check(f"{label}: reported rows match the golden alignment",
                   entries == aligned, f"got {entries}")
    consumer.check(f"{label}: alignment is rectangular",
                   bool(entries) and
                   len({len(row) for _, row in entries}) == 1,
                   f"lengths {[len(row) for _, row in entries]}")
    consumer.check(f"{label}: stripping gaps recovers every input sequence",
                   [(name, row.replace("-", "")) for name, row in entries]
                   == list(source.items()),
                   f"got {[(name, row.replace('-', '')) for name, row in entries]}")


def main(argv):
    if len(argv) != 3:
        print("usage: test_probalign.py <bin_dir> <work_dir>")
        return 2
    bin_dir, work_dir = argv[1], argv[2]
    binary = os.path.join(bin_dir, "probalign")
    if not os.path.isfile(binary):
        print(f"FAIL: probalign is missing from {bin_dir}")
        return 1
    os.makedirs(work_dir, exist_ok=True)

    consumer = Consumer(binary, work_dir)
    protein_file = consumer.write_fasta("protein.mfa", PROTEIN)
    nucleotide_file = consumer.write_fasta("nucleotide.mfa", NUCLEOTIDE)

    # 1. the installed artifact is the built executable ---------------------
    with open(binary, "rb") as handle:
        magic = handle.read(4)
    consumer.check("installed probalign is an ELF executable",
                   magic == b"\x7fELF", magic.hex())
    consumer.check("installed probalign carries the exec bit",
                   os.access(binary, os.X_OK), binary)

    # 2. protein mode really aligns ----------------------------------------
    code, out, err = consumer.run([protein_file])
    consumer.check("protein alignment exits 0", code == 0,
                   f"rc={code} err={err[-200:]}")
    default_entries = parse_mfa(out)
    assert_alignment(consumer, "protein MFA", default_entries,
                     PROTEIN_ALIGNED, PROTEIN)
    consumer.check("protein run reports its version, model and guide tree",
                   "PROBALIGN Version 1.4" in err
                   and "aligns multiple protein sequences" in err
                   and "Alignment tree: ((s1 s2) s3)" in err,
                   err[-300:])

    code, again, _ = consumer.run([protein_file])
    consumer.check("a second run reproduces the first byte for byte",
                   code == 0 and again == out, "posterior decoding may not sample")

    code, prot_out, _ = consumer.run(["-prot", protein_file])
    consumer.check("-prot reproduces the default protein alignment",
                   code == 0 and prot_out == out, f"rc={code}")

    # 3. gap placement is computed, not padded -----------------------------
    code, tuned_out, _ = consumer.run(
        ["-T", "1", "-go", "8", "-ge", "0.5", protein_file])
    tuned = parse_mfa(tuned_out)
    consumer.check("temperature and gap costs move the reported indel",
                   code == 0 and tuned == PROTEIN_ALIGNED_TUNED
                   and dict(tuned)["s3"] != dict(default_entries)["s3"],
                   f"rc={code} got {tuned}")
    consumer.check("tuned rows still reverse to the input sequences",
                   [(name, row.replace("-", "")) for name, row in tuned]
                   == list(PROTEIN.items()), f"got {tuned}")

    # 4. CLUSTAL W rendering -----------------------------------------------
    width = len(PROTEIN_ALIGNED[0][1])
    consumer.check("every reported protein row spans the full alignment",
                   all(len(row) == width for _, row in default_entries),
                   f"width={width} rows={[len(row) for _, row in default_entries]}")
    code, clustalw, _ = consumer.run(["-clustalw", protein_file])
    consumer.check("-clustalw exits 0", code == 0, f"rc={code}")
    consumer.check("-clustalw output matches the CLUSTAL W golden",
                   [line.rstrip() for line in clustalw.splitlines()]
                   == CLUSTALW_GOLDEN,
                   repr(clustalw.splitlines()))
    consumer.check("-clustalw rows equal the MFA rows",
                   parse_clustalw(clustalw, width) == PROTEIN_ALIGNED,
                   repr(parse_clustalw(clustalw, width)))
    consumer.check("-clustalw prints a conservation marker row",
                   has_conservation_row(clustalw),
                   repr(clustalw.splitlines()[-1:]))

    # 5. nucleotide mode ----------------------------------------------------
    code, nuc_out, _ = consumer.run(["-nuc", nucleotide_file])
    consumer.check("-nuc alignment exits 0", code == 0, f"rc={code}")
    assert_alignment(consumer, "nucleotide MFA", parse_mfa(nuc_out),
                     NUCLEOTIDE_ALIGNED, NUCLEOTIDE)
    code, _, err = consumer.run(["-nuc", "-score_matrix", "nuc_simple",
                                 nucleotide_file])
    consumer.check("-score_matrix nuc_simple is accepted", code == 0,
                   f"rc={code} err={err[-160:]}")
    code, _, err = consumer.run(["-prot", "-score_matrix", "gonnet_160",
                                 protein_file])
    consumer.check("-score_matrix gonnet_160 is accepted", code == 0,
                   f"rc={code} err={err[-160:]}")

    # 6. remaining documented switches -------------------------------------
    code, order_out, _ = consumer.run(["-a", protein_file])
    consumer.check("-a keeps the reported alignment valid",
                   code == 0 and parse_mfa(order_out) == PROTEIN_ALIGNED,
                   f"rc={code} got {parse_mfa(order_out)}")
    code, verbose_out, verbose_err = consumer.run(["-v", protein_file])
    consumer.check("-v adds posterior-matrix progress without changing output",
                   code == 0 and verbose_out == out
                   and "Computing posterior matrix" in verbose_err
                   and len(verbose_err) > len(err),
                   f"rc={code} verbose={len(verbose_err)} quiet={len(err)}")

    # 7. failure paths must fail, loudly -----------------------------------
    code, out, err = consumer.run(["missing-reference.mfa"])
    consumer.check("unreadable input exits non-zero", code != 0, f"rc={code}")
    consumer.check("unreadable input names the file in its error",
                   "ERROR: Could not open file" in out + err
                   and "missing-reference.mfa" in out + err,
                   (out + err)[-200:])
    code, out, err = consumer.run(["--prot", protein_file])
    consumer.check("long options are rejected with a non-zero exit",
                   code != 0 and "ERROR: Unrecognized option: --prot" in out + err,
                   f"rc={code} {(out + err)[-200:]}")
    code, _, _ = consumer.run([])
    consumer.check("no arguments exits non-zero", code != 0, f"rc={code}")
    code, out, err = consumer.run(["-T", "not-a-number", protein_file])
    consumer.check("a malformed -T value exits non-zero",
                   code != 0
                   and "Invalid floating-point value following option -T"
                   in out + err,
                   f"rc={code} err={err[-200:]}")

    passed = consumer.attempted - len(consumer.failures)
    if consumer.failures:
        print(f"FAIL: probalign packaged consumer test "
              f"({passed}/{consumer.attempted} assertions passed)")
        return 1
    print(f"PASS: probalign packaged consumer test "
          f"({consumer.attempted}/{consumer.attempted} assertions)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
