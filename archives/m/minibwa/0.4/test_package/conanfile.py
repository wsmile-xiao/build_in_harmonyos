#!/usr/bin/env python3
"""Consumer test for the minibwa/0.4 application package.

Runs the packaged `minibwa` executable end-to-end via self.run() (L0d):
the test_package/test_minibwa.sh script checks the installed ELF binary,
`--help`/`version` subcommands and an index -> map round trip on a tiny
generated reference with a deterministic exact-match read, asserting the
resulting SAM record (100M, NM:i:0). The same dataset is re-verified
below with in-process assertions.
"""
import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.tools.build import can_run


class MinibwaTestConan(ConanFile):
    settings = "os", "compiler", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies["minibwa"].package_folder
        bin_dir = os.path.join(pkg, "bin")
        bin_path = os.path.join(bin_dir, "minibwa")

        # L0d: execute the real test source (test_package/test_minibwa.sh,
        # the L0c test file) via self.run(); it drives the installed
        # bin/minibwa end-to-end (ELF magic + --help/version + index/map
        # with SAM assertions).
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_minibwa.sh")
        self.run(f'sh "{test_script}" "{bin_dir}"', env="conanrun")

        # Documented version subcommand (minibwa has no --version flag).
        out = subprocess.run([bin_path, "version"],
                             capture_output=True, text=True)
        assert out.returncode == 0, \
            f"minibwa version exited {out.returncode}"
        assert "0.4" in out.stdout, f"unexpected version: {out.stdout!r}"

        tdir = tempfile.mkdtemp(prefix="minibwa-test-")
        ref = os.path.join(tdir, "tiny-ref.fa")
        # 168 bp reference, AT/GC balanced blocks, no homopolymer runs.
        with open(ref, "w") as f:
            f.write(">tiny\n")
            f.write("ACGTGCAATGTCAGTCAAGTCAGTTGACGATCGATCGTACGTAGCTAGCTAACGATCGATCGTACGATCGTACGATCGATCGTACGTAGCTAACGATCGATCGATCGTACGATCGATCGTACGATCGTACGATCGTACGATCGTACGATCGTAGCTAACGATCGATCGTACGATCGTACGATCGATCGTACGTAGCTAACGATCG\n")
        with open(ref) as f:
            read = f.read().splitlines()[1][20:120]
        read_fq = os.path.join(tdir, "tiny-read.fq")
        with open(read_fq, "w") as f:
            f.write("@r1\n" + read + "\n+\n" + "F" * len(read) + "\n")

        subprocess.run([bin_path, "index", ref],
                       capture_output=True, text=True, cwd=tdir)
        try:
            r = subprocess.run([bin_path, "map", ref, read_fq],
                               capture_output=True, text=True, cwd=tdir)
        finally:
            shutil.rmtree(tdir, ignore_errors=True)
        assert r.returncode == 0, \
            f"minibwa map exited {r.returncode}: {r.stderr[-400:]}"
        records = [line for line in r.stdout.splitlines()
                   if line and not line.startswith("@")]
        assert records, "minibwa map produced no SAM records"
        first = records[0].split("\t")
        assert len(first) >= 11, f"short SAM record: {records[0][:120]}"
        assert first[2] == "tiny", f"RNAME not 'tiny': {first[2]}"
        assert first[3] == "21", f"POS not 21: {first[3]}"
        assert first[5] == "100M", f"CIGAR not 100M: {first[5]}"
        assert int(first[1]) & 0x100 == 0, "first record should be primary"
        nm = [f for f in first[11:] if f.startswith("NM:i:")]
        assert nm and nm[0] == "NM:i:0", f"expected exact match, got {nm}"
