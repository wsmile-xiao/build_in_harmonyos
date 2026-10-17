#!/usr/bin/env python3
"""Conan test_package for spaced 1.2.0-201605.

spaced ships no test suite at all (MANIFEST.yml documents the inventory), and it
is a CLI tool, so the consumer test drives the packaged binary end to end: it
feeds it FASTA input, a spaced-seed pattern file and a thread count, and
asserts on the distance matrix that comes out - sequence count, per-row labels,
zero diagonal, symmetry and non-zero off-diagonal distances, plus the branch
selection between the DNA and the protein code path.

One assertion group exists purely because of the platform: on AAPCS64 plain
`char` is unsigned, and unpatched upstream then rejects every pattern file.
test_spaced.sh A6 pins that down by requiring the absence of upstream's
"FORMAT-ERROR: Pattern containes illegal characters!" on stderr.

See test_spaced.sh for the assertion list.
"""
import os
import tempfile

from conan import ConanFile
from conan.tools.build import can_run


class SpacedTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies["spaced"].package_folder
        spaced_bin = os.path.join(pkg, "bin", "spaced")
        script = os.path.join(self.source_folder, "test_spaced.sh")
        # Work outside the archive tree: the archive folder is read-only on the
        # CI worker and must stay free of build residue (JC1).
        workdir = os.path.join(tempfile.gettempdir(), "spaced-1.2.0-201605-test_package")
        self.run('sh "%s" "%s" "%s"' % (script, spaced_bin, workdir))
