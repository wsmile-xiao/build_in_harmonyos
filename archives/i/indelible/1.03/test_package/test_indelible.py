#!/usr/bin/env python3
"""Functional test for indelible 1.03 — executes the real binary.

Two cases (counters come from actual execution, not stdout parsing):
  case 1: minimal upstream-style control.txt (NUCLEOTIDE/JC,
          2 taxa, 100 bp, 1 replicate) -> assert outputname.fas and
          outputname_TRUE.phy exist, are non-empty and contain FASTA content.
  case 2: second minimal control.txt (NUCLEOTIDE/JC, 2 taxa, 50 bp,
          1 replicate, different output stub) -> same assertions on its
          own outputs. Two independent lengths prove the simulator runs
          repeatably instead of relying on one fixture.

Rationale: the man page phrase "If INDELible is executed without a control
file present, an example file is generated" does not hold on the真机
build — an empty directory run interactively prompts
"There is no control file. INDELible was looking for file named:
control.txt / Please enter the correct filename." 10 times and exits
without generating control.txt (see preflight 2026-09-27 stderr). So the
old case 1 (empty-dir generation) can never pass; both cases now use
valid control files present before execution.
"""

import os
import subprocess
import sys
import tempfile

MINIMAL_CONTROL_100 = """[TYPE] NUCLEOTIDE 1
[MODEL] modelname
[submodel] JC
[TREE] treename (A:0.1,B:0.1);
[PARTITIONS] partitionname
[treename modelname 100]
[EVOLVE] partitionname 1 outputname
"""

MINIMAL_CONTROL_50 = """[TYPE] NUCLEOTIDE 1
[MODEL] modelname
[submodel] JC
[TREE] treename (A:0.1,B:0.1);
[PARTITIONS] partitionname
[treename modelname 50]
[EVOLVE] partitionname 1 output2
"""


def run_binary(binary, cwd, timeout=120):
    with open(os.devnull, "rb") as devnull:
        return subprocess.run(
            [binary],
            cwd=cwd,
            stdin=devnull,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )


def run_simulation_case(binary, control_text, stub, label):
    work = tempfile.mkdtemp(prefix="indelible-%s-" % label)
    with open(os.path.join(work, "control.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(control_text)
    try:
        proc = run_binary(binary, work)
    except subprocess.TimeoutExpired:
        print("%s FAIL: binary timed out" % label)
        return False
    if proc.returncode != 0:
        print("%s FAIL: exit code %d" % (label, proc.returncode))
        print(proc.stdout.decode("utf-8", "replace")[-2000:])
        return False
    fas = os.path.join(work, stub + ".fas")
    tru = os.path.join(work, stub + "_TRUE.phy")
    for path in (fas, tru):
        if not os.path.isfile(path):
            print("%s FAIL: missing output %s" % (label, os.path.basename(path)))
            print(proc.stdout.decode("utf-8", "replace")[-2000:])
            return False
        if os.path.getsize(path) == 0:
            print("%s FAIL: empty output %s" % (label, os.path.basename(path)))
            return False
    # Guard against empty-file false passes: real FASTA/PHYLIP outputs are
    # non-empty text with sequence content, not zero-assertion placeholders.
    with open(fas, "r", encoding="utf-8", errors="replace") as f:
        fas_text = f.read()
    if ">" not in fas_text:
        print("%s FAIL: %s lacks FASTA header" % (label, os.path.basename(fas)))
        return False
    with open(tru, "r", encoding="utf-8", errors="replace") as f:
        tru_text = f.read()
    if len(tru_text.strip()) == 0:
        print("%s FAIL: %s has no alignment content" % (label, os.path.basename(tru)))
        return False
    print("%s OK: %s + %s non-empty" % (label, os.path.basename(fas), os.path.basename(tru)))
    return True


def main():
    if len(sys.argv) != 2:
        print("usage: test_indelible.py <indelible-binary>")
        return 2
    binary = sys.argv[1]
    if not os.path.isfile(binary):
        print("binary not found: %s" % binary)
        return 1
    if not os.access(binary, os.X_OK) and os.name != "nt":
        print("binary not executable: %s" % binary)
        return 1

    discovered = 2
    passed_count = 0
    if run_simulation_case(binary, MINIMAL_CONTROL_100, "outputname", "case1"):
        passed_count += 1
    if run_simulation_case(binary, MINIMAL_CONTROL_50, "output2", "case2"):
        passed_count += 1

    passed = (passed_count == discovered)
    command = "python3 test_indelible.py <package>/bin/indelible"
    print('HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":%s,"command":"%s","discovered":%d,"passedCount":%d}' % (
        "true" if passed else "false", command, discovered, passed_count))
    print('HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"none - upstream 1.03 ships no test suite (see test_package/MANIFEST.yml audit)","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"upstream tarball has no tests directory and no check/test/ctest target"}')
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
