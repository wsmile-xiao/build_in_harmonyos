#!/usr/bin/env python3
"""Conan test_package for CodonW 1.4.4 — executes the packaged tool through
the consumer driver test_codonw.py (R34: run the packaged program and assert
real analysis behaviour)."""
import os

from conan import ConanFile


class CodonwTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["codonw"]
        bindir = os.path.join(dep.package_folder, "bin")
        inp = os.path.join(self.recipe_folder, "testgene.dat")
        script = os.path.join(self.recipe_folder, "test_codonw.py")
        self.run(f'python3 "{script}" "{bindir}" "{inp}"', env="conanrun")
