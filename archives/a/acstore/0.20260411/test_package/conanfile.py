#!/usr/bin/env python3
import os
import sys

from conan import ConanFile


class AcstoreTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        test_script = os.path.join(self.recipe_folder, "test_acstore.py")
        self.run(f'"{sys.executable}" "{test_script}"', env="conanrun")
