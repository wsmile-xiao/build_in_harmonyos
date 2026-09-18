#!/usr/bin/env python3
"""Conan test_package for GNU dico 2.12 — executes the packaged tools
through the consumer driver test_dico.py (R34: run the packaged programs
and assert real behaviour)."""
import os

from conan import ConanFile


class DicoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["dico"]
        bindir = os.path.join(dep.package_folder, "bin")
        script = os.path.join(self.recipe_folder, "test_dico.py")
        self.run(f'python3 "{script}" "{bindir}"', env="conanrun")
