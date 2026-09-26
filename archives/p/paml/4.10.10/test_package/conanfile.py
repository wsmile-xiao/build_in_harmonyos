#!/usr/bin/env python3
"""test_package for paml — CLI tool suite (no library API).

Upstream ships no test suite, so the test drives the packaged binaries
on real data and asserts values from upstream reference files. All 27
assertions live in run_tests.sh (the L0c test source file):

1. `chi2` (interactive): feed 'q' to quit after the first table, assert
   the chi-square critical value for DF=1, p=0.05 (3.8415) is printed.
2. `yn00` (end-to-end ML run on the upstream abglobin.nuc sample,
   5 sequences x 285 codons, milliseconds to run): compare the Nei-
   Gojobori / Yang-Nielsen / LWL85 estimates against the upstream
   reference output YN00abglobin.result.txt shipped in examples/.
3. all 10 CLI binaries present and executable.
4. OHOS platform-specific (10 assertions): each of the 10 binaries is a
   native OHOS aarch64 ELF executable (ELF magic + ELFCLASS64 +
   e_machine EM_AARCH64, byte-level via od — no readelf dependency).

The script executes real computation paths of the tested package
(not a print-only shell).
"""
import os

from conan import ConanFile


class PamlTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = os.path.join(self.dependencies["paml"].package_folder, "bin")
        script = os.path.join(self.source_folder, "run_tests.sh")
        self.run(f"bash {script} {bin_dir}", env="conanrun")
