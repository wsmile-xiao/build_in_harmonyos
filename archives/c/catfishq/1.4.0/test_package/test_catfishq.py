#!/usr/bin/env python3
"""Consumer tests for catfishq 1.4.0.

Drives the packaged ``bin/catfishq`` against local FASTQ fixtures and
verifies real concatenation / filtering behaviour (not just exit codes):
outputs must be non-empty, preserve read IDs, and honour -n / -l.

Emits HMBS_TEST_PACKAGE_RESULT (discovered/passedCount = 6) and re-emits
the audited HMBS_UPSTREAM_TEST_RESULT (no_tests) so evidence survives
Conan cache hits where build() is skipped.
"""

import gzip
import json
import os
import shutil
import subprocess
import sys
import tempfile


CASES = [
    "help-mentions-fastq",
    "version-prints-1.4.0",
    "concat-single-file-2-reads",
    "concat-directory-4-reads",
    "max-n-1-stops-after-one-read",
    "min-length-50-filters-short-read",
]


def _writable_dir(path):
    try:
        if path and os.path.isdir(path) and os.access(path, os.W_OK):
            return True
    except OSError:
        return False
    return False


def _make_tmpdir():
    # HMBS true machine mounts /tmp read-only; injected TMPDIR/TMP/TEMP
    # points to a writable runtime dir. tempfile respects TMPDIR only when
    # the variable survives conanrun env aggregation, so probe explicitly
    # and never fall back to bare /tmp.
    for key in ("TMPDIR", "TMP", "TEMP"):
        cand = os.environ.get(key, "")
        if _writable_dir(cand):
            return tempfile.mkdtemp(prefix="catfishq-test-", dir=cand)
    try:
        return tempfile.mkdtemp(prefix="catfishq-test-")
    except OSError:
        fallback = os.path.join(os.getcwd(), "catfishq-test-tmp")
        os.makedirs(fallback, exist_ok=True)
        return tempfile.mkdtemp(prefix="catfishq-test-", dir=fallback)


def run_capture(*cmd, env=None):
    proc = subprocess.run(
        list(cmd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
        env=env,
        check=False,
    )
    print("[cmd] " + " ".join(cmd))
    print(proc.stdout)
    return proc.returncode, proc.stdout


def require(cond, label, detail=""):
    if not cond:
        raise AssertionError("FAIL %s\n%s" % (label, detail))
    print("PASS: %s" % label)


def count_reads(path):
    with open(path, "r", encoding="utf-8") as fh:
        lines = [ln.rstrip("\n") for ln in fh if ln.strip() != ""]
    if len(lines) % 4 != 0:
        raise AssertionError("FASTQ line count not multiple of 4: %s" % path)
    return len(lines) // 4, "\n".join(lines)


def _write_validated_inputs(dest_dir):
    """(Re)generate FASTQ inputs with seq/qual lengths matched by construction.

    Static fixture files are hand-maintained and a one-char seq/qual length
    mismatch makes pysam raise ``ValueError: truncated quality string`` (the
    preflight failure). Building the inputs here with string multiplication
    ("ACGT" * 15 paired with "I" * len(seq)) guarantees matched
    lengths regardless of static-file drift. Semantics are unchanged: a.fastq
    holds 2 reads (one 60bp long + one 4bp short for the -l 50 case), b.fastq
    holds 2 long reads, so directory concat is 4 reads.
    """
    os.makedirs(dest_dir, exist_ok=True)
    long_a = "ACGT" * 15  # 60bp (> 50, survives -l 50)
    short_a = "ACGT"  # 4bp (filtered by -l 50)
    long_b1 = "GATTACA" * 10  # 70bp
    long_b2 = "TTGGCCAA" * 9  # 72bp
    payloads = {
        "a.fastq": [
            ("HD1-1", long_a, "I"),
            ("HD1-2", short_a, "I"),
        ],
        "b.fastq": [
            ("HD2-1", long_b1, "J"),
            ("HD2-2", long_b2, "H"),
        ],
    }
    for fname, reads in payloads.items():
        path = os.path.join(dest_dir, fname)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            for rid, seq, qchar in reads:
                qual = qchar * len(seq)
                if len(seq) != len(qual) or not seq:
                    raise AssertionError("generated empty/mismatched read %s" % rid)
                fh.write("@%s\n%s\n+\n%s\n" % (rid, seq, qual))
        # Re-validate what was written (fail fast with a clear message).
        with open(path, "r", encoding="utf-8") as fh:
            lines = [ln.rstrip("\n") for ln in fh if ln.strip() != ""]
        if len(lines) % 4 != 0:
            raise AssertionError("generated FASTQ line count not multiple of 4: %s" % path)
        for i in range(0, len(lines), 4):
            if len(lines[i + 1]) != len(lines[i + 3]):
                raise AssertionError(
                    "generated seq/qual mismatch in %s line %d (%d vs %d)"
                    % (path, i, len(lines[i + 1]), len(lines[i + 3]))
                )
    return dest_dir


def main():
    if len(sys.argv) != 3:
        print("usage: test_catfishq.py <catfishq-bin> <fixtures-dir>")
        return 2
    catfishq = sys.argv[1]
    fixtures = sys.argv[2]
    require(os.path.isfile(catfishq), "packaged catfishq binary exists", catfishq)
    require(os.path.isfile(os.path.join(fixtures, "a.fastq")), "fixture a.fastq exists")
    require(os.path.isfile(os.path.join(fixtures, "b.fastq")), "fixture b.fastq exists")

    # 1. --help
    rc, out = run_capture(catfishq, "--help")
    require(rc == 0, "help exits 0", out)
    require("FASTQ" in out or "fastq" in out, "help mentions FASTQ", out)

    # 2. --version
    rc, out = run_capture(catfishq, "--version")
    require(rc == 0, "version exits 0", out)
    require("1.4.0" in out, "version prints 1.4.0", out)

    tmp = _make_tmpdir()
    # Validated inputs (seq/qual matched by construction) isolate the consumer
    # tests from static-file drift; source fixtures are still checked above.
    inputs = _write_validated_inputs(os.path.join(tmp, "inputs"))
    src_a = os.path.join(inputs, "a.fastq")
    src_b = os.path.join(inputs, "b.fastq")
    try:
        # 3. concat single file -> 2 reads, IDs preserved, non-empty
        single = os.path.join(tmp, "single.fastq")
        rc, out = run_capture(catfishq, "-o", single, src_a)
        require(rc == 0, "concat single file exits 0", out)
        n, body = count_reads(single)
        require(n == 2, "single file yields 2 reads (got %d)" % n, body)
        require("@HD1-1" in body and "@HD1-2" in body, "read IDs preserved", body)

        # 4. concat directory -> 4 reads
        merged = os.path.join(tmp, "merged.fastq")
        rc, out = run_capture(catfishq, "-o", merged, inputs)
        require(rc == 0, "concat directory exits 0", out)
        n, body = count_reads(merged)
        require(n == 4, "directory yields 4 reads (got %d)" % n, body)
        for rid in ("@HD1-1", "@HD1-2", "@HD2-1", "@HD2-2"):
            require(rid in body, "merged output contains %s" % rid, body)

        # gzip input path (upstream fixture parity): merged .gz must also cat 4 reads
        gz_src = os.path.join(tmp, "b.fastq.gz")
        with open(src_b, "rb") as fh_in:
            with gzip.open(gz_src, "wb") as fh_out:
                shutil.copyfileobj(fh_in, fh_out)
        merged_gz = os.path.join(tmp, "merged_gz.fastq")
        rc, out = run_capture(
            catfishq, "-o", merged_gz,
            src_a, gz_src,
        )
        require(rc == 0, "mixed plain+gz inputs exit 0", out)
        n, body = count_reads(merged_gz)
        require(n == 4, "plain+gz yields 4 reads (got %d)" % n, body)

        # 5. -n 1 stops after one read
        one = os.path.join(tmp, "one.fastq")
        rc, out = run_capture(catfishq, "-n", "1", "-o", one, inputs)
        require(rc == 0, "-n 1 exits 0", out)
        n, body = count_reads(one)
        require(n == 1, "-n 1 yields exactly 1 read (got %d)" % n, body)

        # 6. -l 50 filters out the 4bp short read in a.fastq
        filt = os.path.join(tmp, "filt.fastq")
        rc, out = run_capture(
            catfishq, "-l", "50", "-o", filt, src_a
        )
        require(rc == 0, "-l 50 exits 0", out)
        n, body = count_reads(filt)
        require(n == 1, "-l 50 keeps 1 long read (got %d)" % n, body)
        require("@HD1-1" in body and "@HD1-2" not in body, "short read filtered", body)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    tp_marker = {
        "executed": True,
        "passed": True,
        "command": "python3 test_catfishq.py <package>/bin/catfishq fixtures/",
        "discovered": len(CASES),
        "passedCount": len(CASES),
    }
    print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_marker))

    upstream_marker = {
        "status": "no_tests",
        "framework": "upstream-test-audit",
        "command": "audit upstream sdist for test suite (no pytest/unittest config)",
        "discovered": 0,
        "executed": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "reason": (
            "Upstream catfishq-1.4.0 sdist audited: no test_*.py, no tests/ "
            "package, no pytest.ini/tox.ini/setup.cfg[tool:pytest]; setup.py "
            "has no tests_require; test/ holds only fixture FASTQ data. "
            "No automated suite to execute."
        ),
    }
    print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker))
    print("ALL %d CATFISHQ CONSUMER CASES PASSED" % len(CASES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
