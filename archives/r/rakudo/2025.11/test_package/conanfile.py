#!/usr/bin/env python3
"""Consumer test for Rakudo 2025.11."""

import os

from conan import ConanFile


class RakudoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_rakudo.py", "test.raku"

    def requirements(self):
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        runner = os.path.join(self.source_folder, "test_rakudo.py")
        script = os.path.join(self.source_folder, "test.raku")
        package = self.dependencies[self.tested_reference_str].package_folder
        raku = os.path.join(package, "bin", "raku")
        self.run(f'python3 "{runner}" "{raku}" "{script}"', env="conanrun")
