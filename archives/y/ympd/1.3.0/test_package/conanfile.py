"""Consumer smoke tests for the installed ympd executable."""

import os
import sys

from conan import ConanFile


class YmpdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["ympd"]
        binary = os.path.join(package.package_folder, "bin", "ympd")
        script = os.path.join(self.source_folder, "smoke_test.py")
        self.run(f'"{sys.executable}" "{script}" "{binary}"', env="conanrun")
