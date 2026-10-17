#!/usr/bin/env python3
"""Consumer-side functional tests for prover9 2017-11A (LADR tool suite).

Runs the packaged CLI binaries (R34: tests exercise the real package
artifacts, not just printed strings):

  1. prover9 --version       version banner smoke test (the LADR tools
                             print the banner + usage and exit 1 for
                             --version, so we assert on the banner text)
  2. prover9 -t 60 -f x2.in  timed proof of a group-theory theorem:
                             commutativity from left identity, left
                             inverse, associativity and x*x = e; asserts
                             "THEOREM PROVED"
  3. mace4 -v0 -t 60 -f group2.in
                             finite model search for the smallest
                             noncommutative group; asserts the model
                             section and "Exiting with 1 model.", then
                             pipes the output through interpformat
                             tabular and asserts "% Interpretation of
                             size 6"
  4. prooftrans parents_only translation of the saved prover9 proof
                             output; asserts the PROOF section marker

Every subprocess call is bounded by an explicit timeout. The scratch
directory lives under $TMPDIR (E002: /tmp is read-only on OHOS) and is
removed in a try/finally block.

Usage: test_prover9.py <package-bindir> [summary-json-path]
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

# Upstream input: prover9.examples/x2.in (LADR-2017-11A) — group theory.
# Goal: x * y = y * x follows from left identity, left inverse,
# associativity and x * x = e.
PROVER9_INPUT = """
formulas(sos).

  e * x = x.
  x' * x = e.
  (x * y) * z = x * (y * z).

  x * x = e.

end_of_list.

formulas(goals).

  x * y = y * x.

end_of_list.
"""

# Upstream input: mace4.examples/group2.in (LADR-2017-11A) — a
# noncommutative group in first-order form; the smallest model has
# 6 elements (S3). Kept verbatim, including assign(iterate_up_to, 12);
# verbosity is cleared from the command line (-v0), same as upstream
# `make test2`.
MACE4_INPUT = """assign(iterate_up_to, 12).

set(verbose).

% This list of formulas specifies a noncommutative group.
%
% Normally we would write the group axioms with clauses
% (as in the example ncg-48.in).  Here we use quantified
% formulas.

formulas(theory).

% Associativity

all x all y all z ((x * y) * z = x * (y * z)).

% There is a left identity element, and every element has a left inverse.

exists e ((all x (e * x = x)) &
          (all x exists y (y * x = e))).

% So far, we have group theory.  Now, state that
% there are two noncommuting elements.

exists a exists b (a * b != b * a).

end_of_list.
"""

TIME_LIMIT = 60  # hard cap for every subprocess, in seconds


def _tmp_base():
    """E002: /tmp is read-only on OHOS — prefer $TMPDIR, then ~/tmp."""
    value = os.environ.get("TMPDIR")
    if value and os.path.isdir(value):
        return value
    home_tmp = os.path.expanduser(os.path.join("~", "tmp"))
    if os.path.isdir(home_tmp):
        return home_tmp
    return None


class Results:
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.assertions = 0
        self.entries = []

    def check(self, condition, description):
        self.assertions += 1
        if condition:
            print(f"  ok: {description}")
            return True
        print(f"  FAIL: {description}")
        return False

    def record(self, name, ok, detail):
        self.total += 1
        if ok:
            self.passed += 1
        self.entries.append({"name": name, "passed": ok, "detail": detail})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def run_tool(argv, stdin_data=None, timeout=TIME_LIMIT):
    """Run a packaged binary with a mandatory timeout."""
    return subprocess.run(
        argv,
        input=stdin_data,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def test_version_smoke(bindir, results, _scratch):
    """1. prover9 --version prints the 2017-11A banner."""
    try:
        proc = run_tool([os.path.join(bindir, "prover9"), "--version"], timeout=15)
    except subprocess.TimeoutExpired:
        results.record("prover9 --version", False, "timed out")
        return
    out = proc.stdout or ""
    ok = results.check("2017-11A" in out, "version banner contains 2017-11A")
    ok = results.check("Prover9" in out, "version banner contains Prover9") and ok
    results.record(
        "prover9 --version",
        ok,
        f"banner: {out.strip().splitlines()[1].strip() if len(out.strip().splitlines()) > 1 else '(empty)'}",
    )


def test_prover9_theorem(bindir, results, scratch):
    """2. prover9 proves the group-theory theorem (timed)."""
    infile = os.path.join(scratch, "x2.in")
    with open(infile, "w", encoding="utf-8") as fh:
        fh.write(PROVER9_INPUT)
    proof_file = os.path.join(scratch, "x2.proof")
    try:
        proc = run_tool(
            [os.path.join(bindir, "prover9"), "-t", str(TIME_LIMIT), "-f", infile]
        )
    except subprocess.TimeoutExpired:
        results.record("prover9 timed theorem proof", False, "timed out")
        return False
    out = proc.stdout or ""
    with open(proof_file, "w", encoding="utf-8") as fh:
        fh.write(out)
    ok = results.check(proc.returncode == 0, f"prover9 exit code 0 (got {proc.returncode})")
    ok = results.check("THEOREM PROVED" in out, "output contains THEOREM PROVED") and ok
    count = out.count("THEOREM PROVED")
    results.record(
        "prover9 timed theorem proof",
        ok,
        f"exit={proc.returncode}, THEOREM PROVED x{count} (commutativity from left identity/inverse/assoc/x*x=e)",
    )
    return ok


def test_mace4_model(bindir, results, scratch):
    """3. mace4 finds the 6-element noncommutative group model."""
    infile = os.path.join(scratch, "group2.in")
    with open(infile, "w", encoding="utf-8") as fh:
        fh.write(MACE4_INPUT)
    try:
        proc = run_tool(
            [
                os.path.join(bindir, "mace4"),
                "-v0",
                "-t",
                str(TIME_LIMIT),
                "-f",
                infile,
            ]
        )
    except subprocess.TimeoutExpired:
        results.record("mace4 finite model search", False, "timed out")
        return
    out = proc.stdout or ""
    ok = results.check(proc.returncode == 0, f"mace4 exit code 0 (got {proc.returncode})")
    ok = results.check(
        "============================== MODEL" in out,
        "output contains the MODEL section",
    ) and ok
    ok = results.check("Exiting with 1 model." in out, "exiting with 1 model") and ok
    # Feed the mace4 output through interpformat (upstream test2 pipeline).
    try:
        fmt = run_tool(
            [os.path.join(bindir, "interpformat"), "tabular"], stdin_data=out
        )
    except subprocess.TimeoutExpired:
        results.record("mace4 finite model search", False, "interpformat timed out")
        return
    fout = fmt.stdout or ""
    ok = results.check(fmt.returncode == 0, f"interpformat exit code 0 (got {fmt.returncode})") and ok
    ok = results.check(
        "% Interpretation of size 6" in fout,
        "interpformat reports an interpretation of size 6",
    ) and ok
    results.record(
        "mace4 finite model search",
        ok,
        f"exit={proc.returncode}, 6-element noncommutative group model found, interpformat tabular OK",
    )


def test_prooftrans(bindir, results, scratch):
    """4. prooftrans converts the saved prover9 proof output."""
    proof_file = os.path.join(scratch, "x2.proof")
    if not os.path.isfile(proof_file):
        results.record("prooftrans proof translation", False, "no saved proof output")
        return
    with open(proof_file, encoding="utf-8") as fh:
        proof = fh.read()
    try:
        proc = run_tool(
            [os.path.join(bindir, "prooftrans"), "parents_only"], stdin_data=proof
        )
    except subprocess.TimeoutExpired:
        results.record("prooftrans proof translation", False, "timed out")
        return
    out = proc.stdout or ""
    ok = results.check(proc.returncode == 0, f"prooftrans exit code 0 (got {proc.returncode})")
    ok = results.check(
        "============================== PROOF" in out,
        "output contains the PROOF section",
    ) and ok
    steps = out.count("# label(goal)")
    results.record(
        "prooftrans proof translation",
        ok,
        f"exit={proc.returncode}, PROOF section present, {steps} goal-labelled steps",
    )


def main(argv):
    if len(argv) < 2:
        print("usage: test_prover9.py <package-bindir> [summary-json-path]", file=sys.stderr)
        return 2
    bindir = argv[1]
    summary_path = argv[2] if len(argv) > 2 else None
    results = Results()
    scratch = tempfile.mkdtemp(prefix="p9test-", dir=_tmp_base())
    try:
        test_version_smoke(bindir, results, scratch)
        test_prover9_theorem(bindir, results, scratch)
        test_mace4_model(bindir, results, scratch)
        test_prooftrans(bindir, results, scratch)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    print()
    print(f"test summary: {results.passed}/{results.total} tests passed, "
          f"{results.assertions} assertions evaluated")
    print(f"HMBS_TEST_PACKAGE_RESULT: total={results.total} passed={results.passed}")

    if summary_path:
        try:
            with open(summary_path, "w", encoding="utf-8") as fh:
                json.dump(
                    {
                        "total": results.total,
                        "passed": results.passed,
                        "assertions": results.assertions,
                        "tests": results.entries,
                    },
                    fh,
                    ensure_ascii=False,
                    indent=2,
                )
        except OSError as exc:
            print(f"warning: cannot write summary file: {exc}", file=sys.stderr)

    return 0 if results.passed == results.total else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
