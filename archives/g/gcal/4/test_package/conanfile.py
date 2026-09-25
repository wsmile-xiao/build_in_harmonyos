#!/usr/bin/env python3
"""Conan test_package for GNU gcal 4 (artifact gcal/v4) — executes the
packaged tool through the consumer driver test_gcal.py (R34: run the packaged
program and assert real calendar behaviour, not just `--version`)."""
import os

from conan import ConanFile


class GcalTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["gcal"]
        bindir = os.path.join(dep.package_folder, "bin")
        script = os.path.join(self.recipe_folder, "test_gcal.py")
        self.run(f'python3 "{script}" "{bindir}"', env="conanrun")
