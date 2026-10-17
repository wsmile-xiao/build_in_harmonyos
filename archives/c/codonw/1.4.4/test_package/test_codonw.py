#!/usr/bin/env python3
"""Consumer test driver for codonw/1.4.4 (runs the packaged tool).

Usage: python3 test_codonw.py <package_bin_dir> <testgene.dat>

Copies the codonw binary and input file into a private temp dir before
execution (dodges HMDFS cache-page flakiness on CI workers), then asserts
real analysis behaviour of codonw and the argv[0]-dispatched `tidy` alias
copy (upstream `links` target).
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile


def main():
    bindir, inp = sys.argv[1], sys.argv[2]
    work = tempfile.mkdtemp(prefix="codonw-test-")

    # Execute from a freshly written copy: HMDFS cache pages of long-lived
    # build-tree files have been observed to SIGBUS on some CI workers.
    local_bin = os.path.join(work, "codonw")
    shutil.copy2(os.path.join(bindir, "codonw"), local_bin)
    os.chmod(local_bin, 0o755)
    local_tidy = os.path.join(work, "tidy")
    shutil.copy2(os.path.join(bindir, "tidy"), local_tidy)
    os.chmod(local_tidy, 0o755)
    local_inp = os.path.join(work, "testgene.dat")
    shutil.copy2(inp, local_inp)

    # 1) index analysis through the main binary
    out1 = os.path.join(work, "result.txt")
    subprocess.run(
        [local_bin, local_inp, out1,
         "-nomenu", "-silent", "-nowarn", "-human", "-gc", "-enc"],
        check=True, cwd=work)
    with open(out1) as f:
        text = f.read()
    assert "testgene" in text, "gene title missing from indices output"
    assert re.search(r"\d+\.\d+", text), "no numeric index values in output"

    # 2) argv[0]-dispatched copy (upstream `links` target) still works
    out2 = os.path.join(work, "tidy_res.txt")
    subprocess.run(
        [local_tidy, local_inp, out2, "-nomenu", "-silent", "-nowarn"],
        check=True, cwd=work)
    with open(out2) as f:
        tidy_text = f.read()
    assert "testgene" in tidy_text, "gene title missing from tidy output"
    assert re.search(r"[ACGT]{3,}", tidy_text), "tidy output lacks sequence content"

    print("codonw consumer test: OK (index analysis + argv0 variant)")


if __name__ == "__main__":
    main()
