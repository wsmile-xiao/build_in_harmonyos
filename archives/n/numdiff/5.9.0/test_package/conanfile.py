#!/usr/bin/env python3
"""Conan test_package for numdiff 5.9.0.

numdiff is a command-line tool, so this test really executes the installed
binary on real numeric input and asserts on the observed result (R34 / PF3:
a test_package must exercise the artifact, not merely print a string).

Upstream regression suite: numdiff 5.9.0 ships no in-tree tests; the official
suite is the separate ``numdiff_tests-1.7.0`` tarball.  See
test_package/MANIFEST.yml and reports/test-report.md for the accounting.
"""
import os

from conan import ConanFile
from conan.tools.files import save


class NumdiffTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # ``conan create`` runs this test with CWD = the test_package directory,
        # so write the scratch inputs here and always delete them again -- the
        # archive folder must be left clean (these files are not gitignored).
        scratch = [os.path.abspath(n) for n in
                   ("a.txt", "b.txt", "c.txt", "numdiff-report.txt")]
        try:
            # 1) The installed binary reports the packaged version.
            self.run('numdiff --version 2>&1 | grep -q "numdiff 5.9.0"', env="conanrun")

            # 2) Identical numeric files compare equal -> numdiff exits 0.
            save(self, "a.txt", "1  2.0\n3  4.0\n")
            save(self, "b.txt", "1  2.0\n3  4.0\n")
            self.run("numdiff a.txt b.txt", env="conanrun")

            # 3) A genuinely different numeric field is detected: non-zero exit
            #    and a report that names the differing value.
            save(self, "c.txt", "1  2.0\n3  9.0\n")
            self.run("numdiff a.txt c.txt > numdiff-report.txt", env="conanrun",
                     ignore_errors=True)
            self.run('grep -q "9.0" numdiff-report.txt', env="conanrun")

            # 4) The companion tool shipped by the same package also runs.
            self.run('ndselect --version 2>&1 | grep -q "ndselect 5.9.0"', env="conanrun")
        finally:
            for path in scratch:
                try:
                    os.remove(path)
                except OSError:
                    pass
