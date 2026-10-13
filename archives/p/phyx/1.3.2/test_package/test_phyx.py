#!/usr/bin/env python3
"""End-to-end deterministic tests for installed phyx executables."""

import os
import shutil
import subprocess
import sys


def run(program, *args):
    executable = shutil.which(program)
    if not executable:
        raise AssertionError(f"packaged executable not found: {program}")
    result = subprocess.run([executable, *args], text=True, capture_output=True)
    if result.returncode != 0:
        raise AssertionError(
            f"{program} failed ({result.returncode})\n{result.stdout}\n{result.stderr}")
    return result.stdout


data = os.path.abspath(sys.argv[1])

stats = run("pxlssq", "-s", os.path.join(data, "test.fa"))
for expected in (
        "Number of sequences: 5", "Sequence length: 20",
        "A           20          0.2", "C           37         0.37",
        "G+C           55         0.55"):
    if expected not in stats:
        raise AssertionError(f"pxlssq deterministic result missing: {expected}\n{stats}")
print("PASS: pxlssq deterministic nucleotide statistics")

colored = run("pxtcol", "-t", os.path.join(data, "test.tre"))
expected_tree = "tree tree = (((TaxonA:0.1,TaxonB:0.03):0.125,TaxonC:0.25):0.4,(TaxonD:0.23,TaxonE:0.16):0.3);"
if "#NEXUS" not in colored or expected_tree not in colored:
    raise AssertionError(f"pxtcol output mismatch\n{colored}")
print("PASS: pxtcol converts the tree to deterministic NEXUS output")

combined = run("pxtcomb", "-t", os.path.join(data, "test.tre"),
               "-a", os.path.join(data, "test2.tre"))
if "TaxonA" not in combined or not combined.rstrip().endswith(";"):
    raise AssertionError(f"pxtcomb output mismatch\n{combined}")
print("PASS: pxtcomb combines the packaged reference trees")

if os.uname().sysname == "HarmonyOS":
    version = run("pxseqgen", "-V")
    if "pxseqgen" not in version:
        raise AssertionError(f"pxseqgen runtime closure check failed\n{version}")
    print("PASS: HarmonyOS scientific runtime closure loads successfully")

print("ALL PHYX CONSUMER TESTS PASSED")
