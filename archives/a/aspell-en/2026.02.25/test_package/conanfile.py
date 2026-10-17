#!/usr/bin/env python3
"""test_package for aspell-en — validates English dictionary data files."""
import os
from conan import ConanFile


class AspellEnTestConan(ConanFile):
    test_type = "explicit"
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["aspell-en"]
        test_script = os.path.join(self.source_folder, "test_aspell_en.py")
        self.run(f'python3 "{test_script}" "{dep.package_folder}"', env="conanrun")
