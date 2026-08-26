#!/usr/bin/env python3
"""Conan test_package for ltl2ba 1.3 — executable tool smoke test (R34/R7).

Verifies that the ltl2ba binary installed by the Conan package (NOT the
source-tree binary) translates LTL formulae into Büchi automata never
claims. Runs three canonical LTL formulae ([]p, <>p, p U q) and checks
each produces a valid Spin never claim (R6).
"""
import os

from conan import ConanFile


class Ltl2baTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R7: use the binary from the installed Conan package, never the
        # source directory.
        ltl2ba = os.path.join(
            self.dependencies["ltl2ba"].package_folder, "bin", "ltl2ba"
        )
        # test.sh drives the three LTL formulae and asserts exit code 0 +
        # expected Büchi automata output.
        self.run(
            f'cd "{self.source_folder}" && '
            f'bash test.sh "{ltl2ba}"',
            env="conanrun",
        )
