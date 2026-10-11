#!/usr/bin/env python3
"""Consumer test for the installed tstools command set."""

import os

from conan import ConanFile


class TstoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["tstools"]
        bindir = os.path.join(dep.package_folder, "bin")
        self.run(f'TSTOOLS_BIN="{bindir}" sh test.sh', env="conanrun")
