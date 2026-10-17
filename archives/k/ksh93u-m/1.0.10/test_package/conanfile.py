#!/usr/bin/env python3
"""test_package for ksh93u-m — really executes the packaged ksh binary (R34).

Runs `ksh --version` and then executes a functional ksh script (test_ksh.sh)
with the packaged ksh, asserting real shell behaviour (arithmetic, parameter
substitution, loops, conditionals, KSH_VERSION).
"""
import os

from conan import ConanFile


class Ksh93UmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        ksh = os.path.join(self.dependencies["ksh93u-m"].package_folder, "bin", "ksh")
        # Functional test script executed BY the packaged ksh (asserts arithmetic,
        # parameter substitution, loops, conditionals, KSH_VERSION, ...; exit 0 on
        # success). NOTE: `ksh --version` exits 2 by design, so version checking
        # is done inside the script via $KSH_VERSION.
        script = os.path.join(self.source_folder, "test_ksh.sh")
        self.run(f'"{ksh}" "{script}"', env="conanrun")
