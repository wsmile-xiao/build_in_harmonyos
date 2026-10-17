#!/usr/bin/env python3
"""Consumer test for raxml 8.2.13.

Runs the packaged raxmlHPC binary against a minimal PHYLIP DNA alignment
to verify the CLI works end-to-end (version banner + real ML search on a
tiny dataset). Fails (non-zero exit) if the binary is missing, the version
banner is absent, or the ML search does not produce a result tree.
"""

import os
import subprocess
import sys
import tempfile

MINIMAL_PHYLIP = """\
4 10
SeqA ACGTACGTAC
SeqB ACGTACGTAT
SeqC ACGTACGTAG
SeqD ACGTACGTAA
"""


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: test_raxml.py <package_folder>", file=sys.stderr)
        return 2
    package = sys.argv[1]
    binary = os.path.join(package, "bin", "raxmlHPC")
    if not os.path.isfile(binary):
        print(f"FAIL: raxmlHPC binary not found at {binary}", file=sys.stderr)
        return 1

    # 1) Version banner check
    try:
        out = subprocess.run(
            [binary, "-v"], capture_output=True, text=True, timeout=120
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"FAIL: cannot run raxmlHPC -v: {exc}", file=sys.stderr)
        return 1
    banner = (out.stdout or "") + (out.stderr or "")
    # Note: upstream v8.2.13 tag ships version banner "RAxML version 8.2.12"
    # (version string not bumped upstream); accept the 8.2.x series banner.
    if "RAxML version 8.2" not in banner:
        print(f"FAIL: version banner missing, got: {banner[:300]}", file=sys.stderr)
        return 1
    version_line = next(
        (ln.strip() for ln in banner.splitlines() if "RAxML version" in ln),
        banner.strip(),
    )
    print(f"OK: version banner present: {version_line}")

    # 2) End-to-end ML search on a tiny alignment (GTRCAT, fixed seed)
    with tempfile.TemporaryDirectory() as work:
        aln = os.path.join(work, "mini.phy")
        with open(aln, "w", encoding="utf-8") as fh:
            fh.write(MINIMAL_PHYLIP)
        cmd = [
            binary, "-s", aln, "-n", "consumer", "-m", "GTRCAT",
            "-p", "12345", "-w", work,
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"FAIL: raxmlHPC ML search error: {exc}", file=sys.stderr)
            return 1
        result_tree = os.path.join(work, "RAxML_bestTree.consumer")
        if not os.path.isfile(result_tree):
            tail = (res.stdout or "")[-500:] + (res.stderr or "")[-500:]
            print(f"FAIL: no RAxML_bestTree.consumer produced; rc={res.returncode}\n{tail}", file=sys.stderr)
            return 1
        with open(result_tree, encoding="utf-8") as fh:
            tree = fh.read()
        if not tree.strip().startswith("("):
            print("FAIL: result tree does not look like a Newick tree", file=sys.stderr)
            return 1
        print(f"OK: ML search produced result tree ({len(tree)} bytes)")

    print("ALL RAXML CONSUMER TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
