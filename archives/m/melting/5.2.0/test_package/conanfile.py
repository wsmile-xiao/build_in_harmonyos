#!/usr/bin/env python3
"""Conan test_package for melting 5.2.0 — Conan L1 official test.

Calls melting.Main.getMeltingResults Java API (via test.sh + TestMelting.java).
CI runs this automatically via `conan create` (which invokes test_package).
"""

from conan import ConanFile


class MeltingTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["melting"].package_folder
        self.run('sh test.sh "{}"'.format(pkg), env="conanrun")
